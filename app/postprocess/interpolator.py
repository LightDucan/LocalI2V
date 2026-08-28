from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path

logger = logging.getLogger("locali2v.interpolator")

ROOT = Path(__file__).resolve().parents[2]
RIFE_EXE = ROOT / "tools" / "rife" / "rife-ncnn-vulkan.exe"
RIFE_MODEL_DIR = ROOT / "tools" / "rife" / "rife-v4.6"


def interpolate_frames(
    input_dir: str | Path,
    output_dir: str | Path,
    source_fps: float = 8.0,
    target_fps: float = 24.0,
    model_dir: Path | None = None,
) -> tuple[Path, float]:
    """
    Interpolates frame sequence to reach target_fps (default 24fps) using RIFE NCNN Vulkan.
    Falls back to FFmpeg motion interpolation if standalone binary is not available.
    Returns: (output_dir_path, duration_seconds)
    """
    in_dir = Path(input_dir)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    input_frames = sorted(list(in_dir.glob("*.png")))
    if not input_frames:
        raise ValueError(f"No frames found in {in_dir} for interpolation")

    multiplier = target_fps / max(1.0, source_fps)
    # Target frame count: (N - 1) * multiplier + 1
    target_frame_count = int(round((len(input_frames) - 1) * multiplier + 1))
    target_frame_count = max(len(input_frames), target_frame_count)

    t0 = time.perf_counter()
    model_path = model_dir or RIFE_MODEL_DIR

    if RIFE_EXE.exists() and model_path.exists():
        logger.info("Running RIFE NCNN Vulkan interpolation (%d -> %d frames, target %dfps)...", len(input_frames), target_frame_count, int(target_fps))
        cmd = [
            str(RIFE_EXE),
            "-i", str(in_dir),
            "-o", str(out_dir),
            "-n", str(target_frame_count),
            "-m", str(model_path),
            "-f", "%06d.png",
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            logger.warning("RIFE executable returned error (%s). Falling back to FFmpeg motion interpolation.", res.stderr)
            _fallback_ffmpeg_interpolate(in_dir, out_dir, source_fps, target_fps)
    else:
        logger.info("RIFE binary not found. Using FFmpeg motion interpolation (%dfps -> %dfps)...", int(source_fps), int(target_fps))
        _fallback_ffmpeg_interpolate(in_dir, out_dir, source_fps, target_fps)

    duration = round(time.perf_counter() - t0, 2)
    logger.info("Frame interpolation completed in %ss", duration)
    return out_dir, duration


def _fallback_ffmpeg_interpolate(in_dir: Path, out_dir: Path, source_fps: float, target_fps: float):
    in_pattern = in_dir / "%06d.png"
    out_pattern = out_dir / "%06d.png"
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(source_fps),
        "-i", str(in_pattern),
        "-vf", f"minterpolate=fps={int(target_fps)}:mi_mode=mci:mc_mode=aobmc",
        "-vsync", "0",
        str(out_pattern),
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg fallback interpolation failed: {res.stderr}")
