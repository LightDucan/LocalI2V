from __future__ import annotations

import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np
import pytest

from app.postprocess.frame_extractor import extract_frames
from app.postprocess.postprocess_pipeline import postprocess_video
from app.postprocess.upscaler import calculate_psnr, upscale_frames
from app.postprocess.video_probe import probe_video

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_VIDEO = ROOT / "outputs" / "benchmark" / "benchmark_A.mp4"


@pytest.fixture
def synthetic_video_fixture(tmp_path: Path) -> Path:
    """Creates a deterministic 3-frame 512x288 test video in tmp_path."""
    frames_dir = tmp_path / "synth_frames"
    frames_dir.mkdir()

    for i in range(3):
        img = Image.new("RGB", (512, 288), color=(40 + i * 40, 80 + i * 20, 120 + i * 30))
        draw = ImageDraw.Draw(img)
        draw.rectangle([50 + i * 20, 50, 200 + i * 20, 200], fill=(200, 100, 50))
        draw.text((60 + i * 20, 60), f"Frame {i}", fill=(255, 255, 255))
        img.save(frames_dir / f"{i:06d}.png")

    video_path = tmp_path / "synthetic_test.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-framerate", "8",
        "-i", str(frames_dir / "%06d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        "-r", "8",
        str(video_path),
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return video_path


def test_video_probe_synthetic(synthetic_video_fixture: Path):
    info = probe_video(synthetic_video_fixture)
    assert info["width"] == 512
    assert info["height"] == 288
    assert info["frame_count"] == 3
    assert info["codec"] in {"h264", "libx264"}


def test_frame_extractor_synthetic(synthetic_video_fixture: Path, tmp_path: Path):
    out_dir = tmp_path / "extracted_synth"
    frames = extract_frames(synthetic_video_fixture, out_dir)
    assert len(frames) == 3
    assert all(f.suffix.lower() == ".png" for f in frames)


def test_psnr_calculation_and_corruption_detection(tmp_path: Path):
    # Base clean image
    base_img = Image.new("RGB", (512, 288), color=(100, 150, 200))
    draw = ImageDraw.Draw(base_img)
    draw.rectangle([100, 100, 400, 250], fill=(220, 50, 50))
    src_path = tmp_path / "src.png"
    base_img.save(src_path)

    # 1. Clean 2x scaled image
    clean_up = base_img.resize((1024, 576), Image.Resampling.LANCZOS)
    clean_up_path = tmp_path / "clean_up.png"
    clean_up.save(clean_up_path)

    psnr_clean = calculate_psnr(src_path, clean_up_path)
    assert psnr_clean > 35.0, f"Clean upscale should have high PSNR, got {psnr_clean}"

    # 2. Corrupted image with scrambled tiles
    corrupted_arr = np.array(clean_up)
    # Swap top and bottom halves (spatial displacement)
    h = corrupted_arr.shape[0] // 2
    corrupted_arr = np.vstack([corrupted_arr[h:], corrupted_arr[:h]])
    corrupted_img = Image.fromarray(corrupted_arr)
    corrupted_path = tmp_path / "corrupted_up.png"
    corrupted_img.save(corrupted_path)

    psnr_corrupted = calculate_psnr(src_path, corrupted_path)
    assert psnr_corrupted < 18.0, f"Corrupted upscale must fail PSNR guard, got {psnr_corrupted}"


def test_upscale_sanity_fallback_guard(tmp_path: Path):
    in_dir = tmp_path / "guard_in"
    in_dir.mkdir()
    img = Image.new("RGB", (512, 288), color=(70, 120, 180))
    img.save(in_dir / "000000.png")

    out_dir = tmp_path / "guard_out"

    # Forcing min_psnr_threshold impossibly high (90 dB) must trigger automatic fallback to Lanczos
    _, _, engine, fallback, psnr = upscale_frames(
        input_dir=in_dir,
        output_dir=out_dir,
        scale=2,
        min_psnr_threshold=90.0,
    )
    assert fallback is True
    assert engine == "ffmpeg_lanczos"
    assert (out_dir / "000000.png").exists()


def test_postprocess_pipeline_synthetic(synthetic_video_fixture: Path, tmp_path: Path):
    out_dir = tmp_path / "post_out"
    res = postprocess_video(
        raw_video_path=synthetic_video_fixture,
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
    assert meta["upscale_sanity_psnr"] >= 18.0
    assert meta["timings"]["total_postprocess_time_sec"] > 0
    assert synthetic_video_fixture.exists(), "Raw source video must be preserved"
