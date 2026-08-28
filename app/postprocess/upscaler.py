from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path
from PIL import Image
import numpy as np

logger = logging.getLogger("locali2v.upscaler")

ROOT = Path(__file__).resolve().parents[2]
REALESRGAN_EXE = ROOT / "tools" / "realesrgan" / "realesrgan-ncnn-vulkan.exe"
REALESRGAN_MODELS = ROOT / "tools" / "realesrgan" / "models"
MIN_SANITY_PSNR = 18.0


def calculate_psnr(source_frame_path: str | Path, upscaled_frame_path: str | Path) -> float:
    """
    Downscales the upscaled frame back to source frame dimensions and calculates PSNR (dB).
    """
    src_img = Image.open(source_frame_path).convert("RGB")
    up_img = Image.open(upscaled_frame_path).convert("RGB")

    # Downscale upscaled frame back to source size for comparison
    downscaled = up_img.resize(src_img.size, Image.Resampling.LANCZOS)

    src_arr = np.array(src_img, dtype=np.float32)
    down_arr = np.array(downscaled, dtype=np.float32)

    mse = float(np.mean((src_arr - down_arr) ** 2))
    if mse < 1e-10:
        return 99.0
    return round(float(10.0 * np.log10((255.0 ** 2) / mse)), 2)


def upscale_frames(
    input_dir: str | Path,
    output_dir: str | Path,
    scale: int = 2,
    model_name: str | None = None,
    min_psnr_threshold: float = MIN_SANITY_PSNR,
) -> tuple[Path, float, str, bool, float]:
    """
    Upscales image frames in input_dir.
    1. Runs Real-ESRGAN NCNN Vulkan with native scale models (2x: realesr-animevideov3-x2, 4x: realesrgan-x4plus).
    2. Runs automated PSNR sanity check guard on the first frame.
    3. If PSNR < min_psnr_threshold (gross tile corruption), automatically rejects and falls back to FFmpeg Lanczos.

    Returns:
        (output_dir_path, duration_seconds, engine_used, fallback_used, sanity_psnr)
    """
    in_dir = Path(input_dir)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    input_frames = sorted(list(in_dir.glob("*.png")))
    if not input_frames:
        raise ValueError(f"No PNG frames found in {in_dir} to upscale")

    first_src_frame = input_frames[0]
    t0 = time.perf_counter()

    # Determine optimal model for requested scale
    if model_name is None:
        model_name = "realesr-animevideov3-x2" if scale == 2 else "realesrgan-x4plus"

    engine_used = "realesrgan_ncnn_vulkan"
    fallback_used = False
    sanity_psnr = 0.0

    if REALESRGAN_EXE.exists():
        logger.info("Running Real-ESRGAN NCNN Vulkan (model=%s, scale=%dx)...", model_name, scale)
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
        if res.returncode == 0:
            # Check sanity PSNR on the first upscaled frame
            first_up_frame = out_dir / first_src_frame.name
            if first_up_frame.exists():
                sanity_psnr = calculate_psnr(first_src_frame, first_up_frame)
                if sanity_psnr < min_psnr_threshold:
                    logger.warning(
                        "AI upscale sanity check FAILED (PSNR=%.2f dB < %.2f dB threshold). Gross corruption detected! Falling back to FFmpeg Lanczos 2x.",
                        sanity_psnr, min_psnr_threshold,
                    )
                    _fallback_ffmpeg_scale(in_dir, out_dir, scale)
                    engine_used = "ffmpeg_lanczos"
                    fallback_used = True
                else:
                    logger.info("AI upscale sanity check PASSED (PSNR=%.2f dB >= %.2f dB).", sanity_psnr, min_psnr_threshold)
            else:
                logger.warning("First upscaled frame not found. Falling back to FFmpeg Lanczos.")
                _fallback_ffmpeg_scale(in_dir, out_dir, scale)
                engine_used = "ffmpeg_lanczos"
                fallback_used = True
        else:
            logger.warning("Real-ESRGAN execution failed (%s). Falling back to FFmpeg Lanczos.", res.stderr)
            _fallback_ffmpeg_scale(in_dir, out_dir, scale)
            engine_used = "ffmpeg_lanczos"
            fallback_used = True
    else:
        logger.info("Real-ESRGAN binary not found. Using FFmpeg Lanczos upscale (scale=%dx)...", scale)
        _fallback_ffmpeg_scale(in_dir, out_dir, scale)
        engine_used = "ffmpeg_lanczos"
        fallback_used = True

    # If fallback was used, calculate PSNR of Lanczos output
    if fallback_used:
        first_up_frame = out_dir / first_src_frame.name
        if first_up_frame.exists():
            sanity_psnr = calculate_psnr(first_src_frame, first_up_frame)

    duration = round(time.perf_counter() - t0, 2)
    logger.info("Upscaling completed in %ss (engine=%s, fallback=%s, psnr=%.2f dB)", duration, engine_used, fallback_used, sanity_psnr)
    return out_dir, duration, engine_used, fallback_used, sanity_psnr


def _fallback_ffmpeg_scale(in_dir: Path, out_dir: Path, scale: int):
    out_dir.mkdir(parents=True, exist_ok=True)
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
