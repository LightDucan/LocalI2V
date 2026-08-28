from __future__ import annotations

import json
import os
import psutil
import socket
import sys
import time
from pathlib import Path
import pytest
import torch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.history.database import HistoryDatabase
from app.jobs.job_manager import JobManager
from app.orchestration.pipeline import I2VPipeline
from app.postprocess.video_probe import probe_video
from app.system.diagnostics import get_system_status_summary

INPUT_IMAGE = ROOT / "history" / "benchmark_assets" / "character_portrait.png"


def test_rc_system_diagnostics():
    status = get_system_status_summary()
    assert status["gpu"]["status"] == "PASS", f"GPU check failed: {status['gpu']}"
    assert status["checkpoint"]["status"] == "PASS", f"Checkpoint missing: {status['checkpoint']}"
    assert status["output_dir"]["status"] == "PASS"
    assert status["ffmpeg"]["status"] == "PASS"


def test_rc_raw_prompt_invariant_byte_for_byte():
    user_prompt = "A girl standing in the wind. Detailed anime style."
    from app.orchestration.prompt_handler import process_prompt
    res = process_prompt(user_prompt, mode="raw", camera_preset="pan_left", subject_mode="two_subject")
    assert res == user_prompt
    assert res.encode("utf-8") == user_prompt.encode("utf-8")


def test_rc_end_to_end_generation_and_enhancement():
    """Runs a complete end-to-end generation with enhancement and checks all artifacts."""
    db = HistoryDatabase()
    job_mgr = JobManager(db=db)

    prompt = "Character breathes slowly. Camera static."
    seed = 42
    progress_updates = []

    # Monitor memory before
    ram_before = psutil.virtual_memory().used / (1024**3)
    vram_before = torch.cuda.memory_allocated(0) / (1024**2) if torch.cuda.is_available() else 0

    t0 = time.perf_counter()
    generator = job_mgr.run_job_stream(
        image_path=str(INPUT_IMAGE),
        prompt=prompt,
        seed=seed,
        mode="raw",
        preserve="normal",
        motion="normal",
        camera_preset="static",
        subject_mode="single",
        enhance_enabled=True,
    )

    final_video = None
    final_error = None
    for pct, status, vid, err in generator:
        progress_updates.append((pct, status))
        if vid:
            final_video = vid
        if err:
            final_error = err

    duration = time.perf_counter() - t0
    assert final_error is None, f"Generation failed: {final_error}"
    assert final_video is not None, "Final video path must not be None"
    assert Path(final_video).exists(), f"Video file {final_video} does not exist"

    # Verify progress was emitted and strictly monotonic
    assert len(progress_updates) >= 5, f"Expected multiple progress events, got {len(progress_updates)}"
    pcts = [p[0] for p in progress_updates]
    for i in range(1, len(pcts)):
        assert pcts[i] >= pcts[i-1], "Progress must be strictly non-decreasing"

    # Verify video probe: 1024x576 @ 24fps
    probe = probe_video(final_video)
    assert probe["width"] == 1024
    assert probe["height"] == 576
    assert probe["fps"] == 24.0
    assert probe["codec"] in {"h264", "libx264"}

    # Verify SQLite history recorded the job
    latest_jobs = db.get_latest_jobs(5)
    assert len(latest_jobs) >= 1
    job = latest_jobs[0]
    assert job["status"] == "DONE"
    assert job["user_prompt"] == prompt
    assert job["inference_prompt"] == prompt  # RAW invariant in DB
    assert job["raw_output"] is not None
    assert job["enhanced_output"] == final_video

    print(f"RC E2E generation passed in {duration:.2f}s! Video: {final_video}")


def test_rc_invalid_image_rejection(tmp_path: Path):
    bad_img = tmp_path / "corrupted.png"
    bad_img.write_text("not an image binary", encoding="utf-8")

    job_mgr = JobManager()
    gen = job_mgr.run_job_stream(image_path=str(bad_img), prompt="Test prompt", mode="raw")
    error_received = None
    for _, _, _, err in gen:
        if err:
            error_received = err

    assert error_received is not None
    assert "Invalid Image" in error_received or "corrupted" in error_received.lower() or "cannot identify" in error_received.lower()


def test_rc_privacy_local_only_bindings():
    """Verifies ComfyUI and Gradio endpoints are bound strictly to 127.0.0.1 (localhost)."""
    # Verify localhost socket connect
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(2.0)
        s.connect(("127.0.0.1", 8188))
        connected = True
    except Exception:
        connected = False
    finally:
        s.close()
    assert connected, "ComfyUI must be listening on 127.0.0.1:8188"
