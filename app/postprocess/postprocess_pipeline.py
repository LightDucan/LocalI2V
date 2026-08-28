from __future__ import annotations

import datetime
import json
import logging
import shutil
import tempfile
import time
from pathlib import Path
from typing import Callable

from app.postprocess.frame_extractor import extract_frames
from app.postprocess.interpolator import interpolate_frames
from app.postprocess.upscaler import upscale_frames
from app.postprocess.video_encoder import encode_video_from_frames
from app.postprocess.video_probe import probe_video

logger = logging.getLogger("locali2v.postprocess_pipeline")


class PostprocessResult:
    def __init__(
        self,
        success: bool,
        raw_video_path: str,
        enhanced_video_path: str | None = None,
        metadata_path: str | None = None,
        timings: dict[str, float] | None = None,
        error_message: str | None = None,
        details: dict | None = None,
    ):
        self.success = success
        self.raw_video_path = raw_video_path
        self.enhanced_video_path = enhanced_video_path
        self.metadata_path = metadata_path
        self.timings = timings or {}
        self.error_message = error_message
        self.details = details or {}


def postprocess_video(
    raw_video_path: str | Path,
    output_dir: str | Path | None = None,
    source_fps: float | None = None,
    enable_upscale: bool = True,
    upscale_scale: int = 2,
    enable_interpolate: bool = True,
    target_fps: float = 24.0,
    progress_callback: Callable[[float, str], None] | None = None,
) -> PostprocessResult:
    """
    Executes the full post-processing pipeline:
    Extract -> Upscale (Real-ESRGAN/Lanczos) -> Interpolate (RIFE/minterpolate) -> Encode (H.264 24fps).
    Preserves raw input video intact.
    """
    t_start = time.perf_counter()
    raw_path = Path(raw_video_path)
    if not raw_path.exists():
        return PostprocessResult(
            success=False,
            raw_video_path=str(raw_path),
            error_message=f"Raw video not found: {raw_path}",
        )

    out_directory = Path(output_dir) if output_dir else raw_path.parent
    out_directory.mkdir(parents=True, exist_ok=True)

    timings: dict[str, float] = {}

    try:
        if progress_callback:
            progress_callback(0.05, "Probing raw video stream...")

        probe_info = probe_video(raw_path)
        effective_source_fps = source_fps if source_fps is not None else (probe_info["fps"] if probe_info["fps"] < 20.0 else 8.0)
        src_res = probe_info["resolution"]
        logger.info("Raw video: %s (%s @ %sfps, %d frames)", raw_path.name, src_res, effective_source_fps, probe_info["frame_count"])

        temp_workspace = Path(tempfile.mkdtemp(prefix="locali2v_postprocess_"))

        try:
            frames_dir = temp_workspace / "extracted"
            upscaled_dir = temp_workspace / "upscaled"
            interpolated_dir = temp_workspace / "interpolated"

            # 1. Extract Frames
            if progress_callback:
                progress_callback(0.10, "Extracting video frames...")
            t0 = time.perf_counter()
            extracted = extract_frames(raw_path, frames_dir)
            timings["extraction_time_sec"] = round(time.perf_counter() - t0, 2)

            current_frames_dir = frames_dir
            current_fps = effective_source_fps

            # 2. Upscale Frames
            up_engine = "none"
            up_fallback = False
            up_psnr = 0.0

            if enable_upscale:
                if progress_callback:
                    progress_callback(0.30, f"Upscaling frames ({upscale_scale}x)...")
                t0 = time.perf_counter()
                _, up_time, up_engine, up_fallback, up_psnr = upscale_frames(
                    input_dir=current_frames_dir,
                    output_dir=upscaled_dir,
                    scale=upscale_scale,
                )
                timings["upscale_time_sec"] = up_time
                current_frames_dir = upscaled_dir
            else:
                timings["upscale_time_sec"] = 0.0

            # 3. Interpolate Frames (8fps -> 24fps)
            if enable_interpolate and target_fps > current_fps:
                if progress_callback:
                    progress_callback(0.65, f"Interpolating frames ({int(current_fps)}fps -> {int(target_fps)}fps)...")
                t0 = time.perf_counter()
                _, interp_time = interpolate_frames(
                    input_dir=current_frames_dir,
                    output_dir=interpolated_dir,
                    source_fps=current_fps,
                    target_fps=target_fps,
                )
                timings["interpolate_time_sec"] = interp_time
                current_frames_dir = interpolated_dir
                current_fps = target_fps
            else:
                timings["interpolate_time_sec"] = 0.0

            # 4. Final Video Encoding
            if progress_callback:
                progress_callback(0.88, f"Encoding final enhanced video ({int(current_fps)}fps)...")
            t0 = time.perf_counter()
            enhanced_filename = f"{raw_path.stem}_enhanced.mp4"
            enhanced_path = out_directory / enhanced_filename

            encode_video_from_frames(
                frames_dir=current_frames_dir,
                output_mp4=enhanced_path,
                fps=current_fps,
                crf=18,
            )
            timings["encoding_time_sec"] = round(time.perf_counter() - t0, 2)

            total_post_time = round(time.perf_counter() - t_start, 2)
            timings["total_postprocess_time_sec"] = total_post_time

            final_probe = probe_video(enhanced_path)

            details = {
                "raw_video": str(raw_path),
                "enhanced_video": str(enhanced_path),
                "input_resolution": src_res,
                "final_resolution": final_probe["resolution"],
                "input_fps": effective_source_fps,
                "final_fps": final_probe["fps"],
                "input_frame_count": probe_info["frame_count"],
                "final_frame_count": final_probe["frame_count"],
                "duration_seconds": final_probe["duration_sec"],
                "upscale_enabled": enable_upscale,
                "upscale_scale": upscale_scale,
                "upscale_engine": up_engine,
                "upscale_fallback_used": up_fallback,
                "upscale_sanity_psnr": up_psnr,
                "interpolate_enabled": enable_interpolate,
                "target_fps": target_fps,
                "timings": timings,
                "timestamp": datetime.datetime.now().isoformat(),
                "status": "SUCCESS",
            }

            meta_path = enhanced_path.with_suffix(".json")
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(details, f, indent=2)

            if progress_callback:
                progress_callback(1.0, f"Post-processing complete in {total_post_time}s")

            logger.info("Post-processing finished: %s -> %s (Total: %ss)", raw_path.name, enhanced_path.name, total_post_time)

            return PostprocessResult(
                success=True,
                raw_video_path=str(raw_path),
                enhanced_video_path=str(enhanced_path),
                metadata_path=str(meta_path),
                timings=timings,
                details=details,
            )

        finally:
            shutil.rmtree(temp_workspace, ignore_errors=True)

    except Exception as exc:
        logger.exception("Post-processing pipeline failed: %s", exc)
        return PostprocessResult(
            success=False,
            raw_video_path=str(raw_path),
            error_message=f"Postprocess Error: {exc}",
            timings=timings,
        )
