from __future__ import annotations

import datetime
import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("locali2v.output_saver")


def assemble_video(
    frame_files: list[str],
    comfy_output_dir: str | Path,
    output_dir: str | Path,
    seed: int,
    fps: float = 8.0,
) -> Path:
    """
    Assembles generated image frames into an MP4 video in the outputs directory
    with naming pattern: outputs/YYYYMMDD_HHMMSS_{seed}.mp4
    """
    comfy_out = Path(comfy_output_dir)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    mp4_path = out_dir / f"{timestamp}_{seed}.mp4"

    sorted_frames = sorted(frame_files)
    if not sorted_frames:
        raise ValueError("No frame files provided to assemble_video")

    temp_list_path = out_dir / f".temp_concat_{timestamp}_{seed}.txt"
    try:
        with open(temp_list_path, "w", encoding="utf-8") as f:
            for fname in sorted_frames:
                frame_path = (comfy_out / fname).resolve().as_posix()
                f.write(f"file '{frame_path}'\n")
                f.write(f"duration {1.0 / fps}\n")
            # Repeat last frame for ffmpeg duration boundary
            last_path = (comfy_out / sorted_frames[-1]).resolve().as_posix()
            f.write(f"file '{last_path}'\n")

        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(temp_list_path),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
            "-preset", "fast",
            "-r", str(fps),
            str(mp4_path)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg video assembly failed: {res.stderr}")

        logger.info("Successfully encoded video to %s", mp4_path)
        return mp4_path

    finally:
        if temp_list_path.exists():
            try:
                temp_list_path.unlink()
            except Exception:
                pass


def save_metadata(
    video_path: Path,
    metadata: dict,
) -> Path:
    """
    Saves a companion JSON sidecar metadata file with the exact same base name as the MP4.
    """
    json_path = video_path.with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    logger.info("Saved metadata sidecar to %s", json_path)
    return json_path
