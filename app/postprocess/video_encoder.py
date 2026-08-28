from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path

logger = logging.getLogger("locali2v.video_encoder")


def encode_video_from_frames(
    frames_dir: str | Path,
    output_mp4: str | Path,
    fps: float = 24.0,
    crf: int = 18,
    preset: str = "medium",
) -> tuple[Path, float]:
    """
    Encodes PNG image sequence from frames_dir into an H.264 MP4 video.
    """
    in_dir = Path(frames_dir)
    out_path = Path(output_mp4)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    pattern = in_dir / "%06d.png"

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(pattern),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", str(crf),
        "-preset", preset,
        str(out_path),
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg video encoding failed: {res.stderr}")

    duration = round(time.perf_counter() - t0, 2)
    logger.info("Encoded video %s (@ %sfps) in %ss", out_path.name, fps, duration)
    return out_path, duration
