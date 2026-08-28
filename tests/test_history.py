from __future__ import annotations

import json
from pathlib import Path
import pytest

from app.history.database import HistoryDatabase
from app.system.diagnostics import get_system_status_summary
from app.ui.main_ui import on_mode_change


def test_sqlite_persistence_across_reopen(tmp_path: Path):
    db_path = tmp_path / "test_history.db"

    # Instance 1: Create 3 jobs
    db1 = HistoryDatabase(db_path)
    job1 = db1.create_job(
        job_id="job-001",
        source_image="img1.png",
        user_prompt="Prompt 1",
        seed=101,
        mode="raw",
        preserve="normal",
        motion="normal",
    )
    db1.update_job_status("job-001", status="DONE", raw_output="outputs/001.mp4")

    job2 = db1.create_job(
        job_id="job-002",
        source_image="img2.png",
        user_prompt="Prompt 2",
        seed=202,
        mode="simple",
        preserve="high",
        motion="subtle",
    )
    db1.update_job_status("job-002", status="DONE", raw_output="outputs/002.mp4", enhanced_output="outputs/002_enh.mp4")

    job3 = db1.create_job(
        job_id="job-003",
        source_image="img3.png",
        user_prompt="Prompt 3",
        seed=303,
        mode="cinematic",
        preserve="maximum",
        motion="strong",
    )
    db1.update_job_status("job-003", status="FAILED", error_message="Simulated error")

    # Instance 2: Reopen from disk
    db2 = HistoryDatabase(db_path)
    latest = db2.get_latest_jobs(10)
    assert len(latest) == 3

    # Check persistence of fields
    j1 = db2.get_job("job-001")
    assert j1 is not None
    assert j1["user_prompt"] == "Prompt 1"
    assert j1["seed"] == 101
    assert j1["status"] == "DONE"
    assert j1["raw_output"] == "outputs/001.mp4"

    j2 = db2.get_job("job-002")
    assert j2 is not None
    assert j2["mode"] == "simple"
    assert j2["enhanced_output"] == "outputs/002_enh.mp4"

    j3 = db2.get_job("job-003")
    assert j3 is not None
    assert j3["status"] == "FAILED"
    assert j3["error_message"] == "Simulated error"


def test_retry_creates_distinct_job(tmp_path: Path):
    db = HistoryDatabase(tmp_path / "test_retry.db")
    orig_job = db.create_job(
        job_id="job-orig",
        source_image="portrait.png",
        user_prompt="Character breathing",
        seed=42,
        mode="raw",
    )
    db.update_job_status("job-orig", status="DONE", raw_output="outputs/orig.mp4")

    # Retry creates a new distinct job_id
    new_job_id = "job-retry-999"
    new_job = db.create_job(
        job_id=new_job_id,
        source_image=orig_job["source_image"],
        user_prompt=orig_job["user_prompt"],
        seed=orig_job["seed"],
        mode=orig_job["mode"],
    )

    assert new_job["job_id"] != orig_job["job_id"]
    assert new_job["user_prompt"] == orig_job["user_prompt"]
    assert new_job["seed"] == orig_job["seed"]

    # Verify original job remained unchanged
    check_orig = db.get_job("job-orig")
    assert check_orig["job_id"] == "job-orig"
    assert check_orig["status"] == "DONE"


def test_mode_ui_logic():
    # RAW mode hides camera and subject prompt controls
    cam_up, subj_up = on_mode_change("Raw")
    assert cam_up["visible"] is False
    assert subj_up["visible"] is False

    # Simple mode shows camera and subject controls
    cam_up, subj_up = on_mode_change("Simple")
    assert cam_up["visible"] is True
    assert subj_up["visible"] is True

    # Cinematic mode shows camera and subject controls
    cam_up, subj_up = on_mode_change("Cinematic")
    assert cam_up["visible"] is True
    assert subj_up["visible"] is True


def test_diagnostics_real_checks():
    summary = get_system_status_summary()
    assert "gpu" in summary
    assert "comfyui" in summary
    assert "checkpoint" in summary
    assert "output_dir" in summary
    assert "ffmpeg" in summary
    assert summary["output_dir"]["status"] == "PASS"
    assert summary["ffmpeg"]["status"] == "PASS"
    assert summary["gpu"]["status"] in {"PASS", "FAIL"}


def test_latest_10_ordering(tmp_path: Path):
    db = HistoryDatabase(tmp_path / "test_ordering.db")
    for i in range(15):
        db.create_job(job_id=f"job-{i:03d}", user_prompt=f"Prompt {i}")

    latest = db.get_latest_jobs(10)
    assert len(latest) == 10
    # Newest should be first
    assert latest[0]["job_id"] == "job-014"
    assert latest[9]["job_id"] == "job-005"
