from __future__ import annotations

import json
from pathlib import Path
import pytest

from app.postprocess.video_probe import probe_video
from app.postprocess.frame_extractor import extract_frames
from app.postprocess.postprocess_pipeline import postprocess_video

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_VIDEO = ROOT / "outputs" / "benchmark" / "benchmark_A.mp4"


def test_video_probe():
    assert SAMPLE_VIDEO.exists(), "Sample video benchmark_A.mp4 should exist"
    info = probe_video(SAMPLE_VIDEO)
    assert info["width"] == 512
    assert info["height"] == 288
    assert info["frame_count"] >= 25
    assert info["codec"] in {"h264", "libx264"}


def test_frame_extractor(tmp_path: Path):
    frames_dir = tmp_path / "extracted_frames"
    frames = extract_frames(SAMPLE_VIDEO, frames_dir)
    assert len(frames) >= 25
    assert all(f.suffix.lower() == ".png" for f in frames)


def test_postprocess_pipeline_execution(tmp_path: Path):
    out_dir = tmp_path / "post_out"
    res = postprocess_video(
        raw_video_path=SAMPLE_VIDEO,
        output_dir=out_dir,
        source_fps=8.0,
        enable_upscale=True,
        upscale_scale=2,
        enable_interpolate=True,
        target_fps=24.0,
    )

    assert res.success is True, f"Postprocess failed: {res.error_message}"
    assert res.enhanced_video_path is not None
    assert Path(res.enhanced_video_path).exists()
    assert Path(res.metadata_path).exists()

    with open(res.metadata_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["input_resolution"] == "512x288"
    assert meta["final_resolution"] == "1024x576"
    assert meta["final_fps"] == 24.0
    assert meta["timings"]["total_postprocess_time_sec"] > 0
    assert SAMPLE_VIDEO.exists(), "Raw source video must be preserved"
