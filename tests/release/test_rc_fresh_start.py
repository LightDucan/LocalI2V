from __future__ import annotations

import json
import logging
import os
import psutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from PIL import Image, ImageDraw
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.history.database import HistoryDatabase
from app.jobs.job_manager import JobManager
from app.postprocess.video_probe import probe_video
from app.system.diagnostics import get_system_status_summary


@pytest.fixture
def synthetic_portrait_fixture(tmp_path: Path) -> Path:
    """Generates a deterministic 512x288 RGB test portrait without external file dependencies."""
    img = Image.new("RGB", (512, 288), color=(30, 45, 60))
    draw = ImageDraw.Draw(img)
    # Head & torso silhouette
    draw.ellipse([216, 40, 296, 120], fill=(220, 180, 150))
    draw.rectangle([196, 120, 316, 260], fill=(80, 100, 140))
    draw.text((220, 70), "RELEASE", fill=(0, 0, 0))
    test_path = tmp_path / "synthetic_test_portrait.png"
    img.save(test_path)
    return test_path


def find_comfyui_pid() -> int | None:
    """Finds the PID of the process listening on port 8188."""
    for conn in psutil.net_connections(kind="inet"):
        if conn.laddr and conn.laddr.port == 8188 and conn.status == "LISTEN":
            return conn.pid
    return None


def get_gpu_vram_mb() -> float:
    """Polls real GPU VRAM usage via nvidia-smi."""
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True,
        )
        return float(res.stdout.strip().split("\n")[0])
    except Exception:
        return 0.0


def test_rc_system_diagnostics():
    status = get_system_status_summary()
    assert status["gpu"]["status"] == "PASS", f"GPU check failed: {status['gpu']}"
    assert status["checkpoint"]["status"] == "PASS", f"Checkpoint missing: {status['checkpoint']}"
    assert status["output_dir"]["status"] == "PASS"
    assert status["ffmpeg"]["status"] == "PASS"


def test_rc_raw_prompt_invariant_byte_for_byte():
    user_prompt = "A character breathing softly. Camera static."
    from app.orchestration.prompt_handler import process_prompt
    res = process_prompt(user_prompt, mode="raw", camera_preset="pan_left", subject_mode="two_subject")
    assert res == user_prompt
    assert res.encode("utf-8") == user_prompt.encode("utf-8")


def test_rc_end_to_end_generation_enhancement_and_privacy(synthetic_portrait_fixture: Path, tmp_path: Path):
    """
    Executes full E2E generation + enhancement on a synthetic portrait while actively
    monitoring network traffic for any non-loopback outbound connections and tracking peak memory.
    """
    db_path = tmp_path / "rc_history.db"
    db = HistoryDatabase(db_path)
    job_mgr = JobManager(db=db)

    prompt = "Character breathes slowly. Camera static."
    progress_updates = []

    # Monitor processes: current process and ComfyUI process
    test_pid = os.getpid()
    comfy_pid = find_comfyui_pid()
    monitored_pids = {test_pid}
    if comfy_pid:
        monitored_pids.add(comfy_pid)

    observed_non_loopback_connections = []
    peak_vram_mb = [0.0]
    peak_ram_gb = [0.0]
    stop_monitor = threading.Event()

    def network_and_memory_monitor():
        allowed_hosts = {"127.0.0.1", "::1", "localhost", "0.0.0.0"}
        while not stop_monitor.is_set():
            # 1. Network monitoring
            try:
                for c in psutil.net_connections(kind="inet"):
                    if c.pid in monitored_pids and c.raddr:
                        rip = c.raddr.ip
                        if rip not in allowed_hosts:
                            observed_non_loopback_connections.append({
                                "pid": c.pid,
                                "laddr": f"{c.laddr.ip}:{c.laddr.port}",
                                "raddr": f"{c.raddr.ip}:{c.raddr.port}",
                                "status": c.status,
                            })
            except Exception:
                pass

            # 2. Memory monitoring
            vram = get_gpu_vram_mb()
            if vram > peak_vram_mb[0]:
                peak_vram_mb[0] = vram

            ram = psutil.virtual_memory().used / (1024**3)
            if ram > peak_ram_gb[0]:
                peak_ram_gb[0] = ram

            time.sleep(0.2)

    monitor_thread = threading.Thread(target=network_and_memory_monitor, daemon=True)
    monitor_thread.start()

    t0 = time.perf_counter()
    final_video = None
    final_error = None

    try:
        # Request seed = -1 (random effective seed)
        generator = job_mgr.run_job_stream(
            image_path=str(synthetic_portrait_fixture),
            prompt=prompt,
            seed=-1,
            mode="raw",
            preserve="normal",
            motion="normal",
            camera_preset="static",
            subject_mode="single",
            enhance_enabled=True,
        )

        for pct, status, vid, err in generator:
            progress_updates.append((pct, status))
            if vid:
                final_video = vid
            if err:
                final_error = err

    finally:
        stop_monitor.set()
        monitor_thread.join(timeout=1.0)

    duration = round(time.perf_counter() - t0, 2)

    # 1. Assertion: No errors and output exists
    assert final_error is None, f"Generation failed: {final_error}"
    assert final_video is not None, "Final video path must not be None"
    assert Path(final_video).exists(), f"Video file {final_video} does not exist"

    # 2. Assertion: Progress was monotonic
    assert len(progress_updates) >= 5, f"Expected multiple progress events, got {len(progress_updates)}"
    pcts = [p[0] for p in progress_updates]
    for i in range(1, len(pcts)):
        assert pcts[i] >= pcts[i-1], "Progress must be strictly non-decreasing"

    # 3. Assertion: Video probe verification (1024x576 @ 24fps)
    probe = probe_video(final_video)
    assert probe["width"] == 1024
    assert probe["height"] == 576
    assert probe["fps"] == 24.0
    assert probe["codec"] in {"h264", "libx264"}

    # 4. Assertion: SQLite history and effective seed persistence
    latest_jobs = db.get_latest_jobs(5)
    assert len(latest_jobs) >= 1
    job = latest_jobs[0]
    assert job["status"] == "DONE"
    assert job["user_prompt"] == prompt
    assert job["inference_prompt"] == prompt  # RAW invariant in DB
    assert job["seed"] > 0, f"Effective seed must be positive integer, got {job['seed']}"
    assert job["raw_output"] is not None
    assert job["enhanced_output"] == final_video

    # 5. Assertion: Framing and preview artifacts
    sj = json.loads(job["settings_json"]) if job.get("settings_json") else {}
    assert sj.get("preprocess_mode") == "contain_pad"

    # 6. Assertion: Privacy check - zero non-loopback outbound connections
    assert observed_non_loopback_connections == [], f"Outbound connections detected during generation: {observed_non_loopback_connections}"

    print(f"\n[RC METRICS]")
    print(f"  Duration: {duration}s")
    print(f"  Effective Seed: {job['seed']}")
    print(f"  Peak VRAM (nvidia-smi): {peak_vram_mb[0]:.1f} MB")
    print(f"  Peak RAM (psutil): {peak_ram_gb[0]:.2f} GB")
    print(f"  Monitored PIDs: {monitored_pids}")
    print(f"  Non-loopback connections: {observed_non_loopback_connections}")
    print(f"  Enhanced Video: {final_video}")


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
