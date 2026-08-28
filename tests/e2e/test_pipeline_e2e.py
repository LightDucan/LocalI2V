from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path
import pytest
from PIL import Image

from app.orchestration.pipeline import I2VPipeline
from app.jobs.job_manager import JobManager


@pytest.fixture(scope="module")
def running_comfyui():
    # Start ComfyUI
    cmd = [
        ".venv/Scripts/python.exe",
        "comfyui/main.py",
        "--listen", "127.0.0.1",
        "--port", "8188",
        "--disable-xformers",
        "--use-split-cross-attention",
        "--lowvram",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Wait for server ready
    client = I2VPipeline().client
    ready = False
    for _ in range(30):
        try:
            client.check_health(timeout=2.0)
            ready = True
            break
        except Exception:
            time.sleep(1.0)

    assert ready, "ComfyUI server failed to start for E2E tests"
    yield proc

    # Teardown
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def test_e2e_pipeline_generation(running_comfyui, tmp_path: Path):
    pipeline = I2VPipeline(output_dir=tmp_path / "outputs")

    # Create test image
    test_img = tmp_path / "e2e_test_input.png"
    img = Image.new("RGB", (512, 288), color=(100, 150, 200))
    img.save(test_img)

    user_prompt = "Character breathes gently. Camera static."
    res = pipeline.generate(
        image_path=test_img,
        prompt=user_prompt,
        seed=12345,
        steps=8,
        length=25,
        fps=8.0,
        mode="raw",
    )

    assert res.success is True, f"Pipeline generation failed: {res.error_message}"
    assert res.video_path is not None
    assert Path(res.video_path).exists()
    assert Path(res.video_path).stat().st_size > 1000

    assert res.metadata_path is not None
    assert Path(res.metadata_path).exists()

    with open(res.metadata_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["selected_model"] == "ltxv-2b-0.9.6-distilled-04-25.safetensors"
    assert meta["seed"] == 12345
    assert meta["user_prompt"] == user_prompt
    assert meta["inference_prompt"] == user_prompt
    assert meta["frame_count"] == 25
    assert meta["resolution"] == "512x288"
    assert meta["steps"] == 8
    assert meta["generation_time_seconds"] > 0
    assert meta["status"] == "SUCCESS"


def test_e2e_realtime_progress_streaming(running_comfyui, tmp_path: Path):
    pipeline = I2VPipeline(output_dir=tmp_path / "outputs")
    jm = JobManager(pipeline=pipeline)

    test_img = tmp_path / "stream_test.png"
    img = Image.new("RGB", (512, 288), color=(120, 80, 160))
    img.save(test_img)

    progress_updates: list[tuple[float, str]] = []
    final_video: str | None = None
    final_error: str | None = None

    for pct, status_text, vid_path, err_msg in jm.run_job_stream(
        image_path=str(test_img),
        prompt="Character blinks slowly. Camera static.",
        seed=4242,
        steps=8,
        length=25,
    ):
        progress_updates.append((pct, status_text))
        if vid_path:
            final_video = vid_path
        if err_msg:
            final_error = err_msg

    # 1. Assert multiple intermediate progress events occurred
    assert len(progress_updates) >= 5, f"Expected >= 5 progress updates, got {len(progress_updates)}"

    # 2. Assert progress is strictly monotonic
    prev = -1.0
    for pct, text in progress_updates:
        assert pct >= prev, f"Non-monotonic progress update: {pct} < {prev} (text: {text})"
        prev = pct

    # 3. Assert final success == 1.0 and video produced
    assert final_error is None
    assert final_video is not None
    assert Path(final_video).exists()
    assert progress_updates[-1][0] == 1.0
    print(f"Captured {len(progress_updates)} monotonic progress updates during generation.")


def test_e2e_real_cancellation(running_comfyui, tmp_path: Path):
    pipeline = I2VPipeline(output_dir=tmp_path / "outputs")
    jm = JobManager(pipeline=pipeline)

    test_img = tmp_path / "cancel_real_test.png"
    img = Image.new("RGB", (512, 288), color=(60, 60, 60))
    img.save(test_img)

    stream_results = []
    cancel_called = threading.Event()
    cancel_time = [0.0]

    def consume_stream():
        for item in jm.run_job_stream(
            image_path=str(test_img),
            prompt="Character walks forward. Camera tracking.",
            seed=7777,
            steps=8,
            length=25,
        ):
            stream_results.append(item)
            pct = item[0]
            # Once progress is active in setup/sampling, trigger cancel
            if pct >= 0.05 and not cancel_called.is_set():
                cancel_called.set()
                t0 = time.perf_counter()
                success = jm.cancel()
                cancel_time[0] = time.perf_counter() - t0
                assert success is True

    runner_thread = threading.Thread(target=consume_stream)
    runner_thread.start()
    runner_thread.join(timeout=30.0)

    assert not runner_thread.is_alive(), "Stream runner did not exit within timeout after cancel"
    assert not jm.is_running, "JobManager should be non-running/IDLE after cancel"

    # Verify no successful video is reported
    videos_produced = [res[2] for res in stream_results if res[2] is not None]
    assert len(videos_produced) == 0, f"Expected no video on cancelled job, but got: {videos_produced}"

    # Verify cancelled status or error message
    final_status = stream_results[-1][1] if stream_results else ""
    assert "cancel" in final_status.lower() or "interrupted" in final_status.lower() or "cancelled" in final_status.lower()
    print(f"Cancellation confirmed promptly in {cancel_time[0]:.3f}s. Final status: {final_status}")


def test_e2e_invalid_image_error_handling(running_comfyui, tmp_path: Path):
    pipeline = I2VPipeline(output_dir=tmp_path / "outputs")
    res = pipeline.generate(
        image_path=tmp_path / "does_not_exist.png",
        prompt="Test prompt",
    )
    assert res.success is False
    assert "Invalid Image" in res.error_message
