from __future__ import annotations

import json
import os
import subprocess
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


def test_e2e_job_manager_stream_and_cancel(running_comfyui, tmp_path: Path):
    pipeline = I2VPipeline(output_dir=tmp_path / "outputs")
    jm = JobManager(pipeline=pipeline)

    test_img = tmp_path / "cancel_test.png"
    img = Image.new("RGB", (512, 288), color=(50, 50, 50))
    img.save(test_img)

    # Test stream execution
    updates = []
    for pct, status_text, vid_path, err in jm.run_job_stream(
        image_path=str(test_img),
        prompt="A short test clip.",
        seed=999,
        steps=8,
        length=25,
    ):
        updates.append((pct, status_text))

    assert len(updates) > 1
    assert updates[-1][0] == 1.0


def test_e2e_invalid_image_error_handling(running_comfyui, tmp_path: Path):
    pipeline = I2VPipeline(output_dir=tmp_path / "outputs")
    res = pipeline.generate(
        image_path=tmp_path / "does_not_exist.png",
        prompt="Test prompt",
    )
    assert res.success is False
    assert "Invalid Image" in res.error_message
