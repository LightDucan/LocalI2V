from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path

logger = logging.getLogger("locali2v.upscaler")

ROOT = Path(__file__).resolve().parents[2]
REALESRGAN_EXE = ROOT / "tools" / "realesrgan" / "realesrgan-ncnn-vulkan.exe"
REALESRGAN_MODELS = ROOT / "tools" / "realesrgan" / "models"


def upscale_frames(
    input_dir: str | Path,
    output_dir: str | Path,
    scale: int = 2,
    model_name: str = "realesrgan-x4plus",
) -> tuple[Path, float]:
    """
    Upscales image frames in input_dir using Real-ESRGAN NCNN Vulkan.
    Falls back to FFmpeg Lanczos scaling if standalone binary is not found.
    Returns: (output_dir_path, duration_seconds)
    """
    in_dir = Path(input_dir)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()

    if REALESRGAN_EXE.exists():
        logger.info("Running Real-ESRGAN NCNN Vulkan upscale (scale=%dx)...", scale)
        cmd = [
            str(REALESRGAN_EXE),
            "-i", str(in_dir),
            "-o", str(out_dir),
            "-s", str(scale),
            "-m", str(REALESRGAN_MODELS),
            "-n", model_name,
            "-f", "png",
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            logger.warning("Real-ESRGAN executable returned error (%s). Falling back to FFmpeg Lanczos upscale.", res.stderr)
            _fallback_ffmpeg_scale(in_dir, out_dir, scale)
    else:
        logger.info("Real-ESRGAN binary not found. Using FFmpeg Lanczos upscale (scale=%dx)...", scale)
        _fallback_ffmpeg_scale(in_dir, out_dir, scale)

    duration = round(time.perf_counter() - t0, 2)
    logger.info("Upscaling completed in %ss", duration)
    return out_dir, duration


def _fallback_ffmpeg_scale(in_dir: Path, out_dir: Path, scale: int):
    in_pattern = in_dir / "%06d.png"
    out_pattern = out_dir / "%06d.png"
    cmd = [
        "ffmpeg", "-y",
        "-i", str(in_pattern),
        "-vf", f"scale=iw*{scale}:ih*{scale}:flags=lanczos",
        str(out_pattern),
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg fallback upscaling failed: {res.stderr}")
