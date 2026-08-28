from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("locali2v.video_probe")


def probe_video(video_path: str | Path) -> dict:
    """
    Probes video file using ffprobe and returns metadata dictionary:
    width, height, fps, frame_count, duration, codec.
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]

    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        data = json.loads(res.stdout)
    except Exception as exc:
        raise RuntimeError(f"ffprobe failed on {video_path}: {exc}") from exc

    video_stream = None
    for s in data.get("streams", []):
        if s.get("codec_type") == "video":
            video_stream = s
            break

    if not video_stream:
        raise ValueError(f"No video stream found in {video_path}")

    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))
    codec = video_stream.get("codec_name", "unknown")

    # Parse fps (e.g. '8/1' or '24/1')
    r_fps = video_stream.get("r_frame_rate", "8/1")
    if "/" in r_fps:
        num, den = r_fps.split("/")
        fps = round(float(num) / max(1.0, float(den)), 2)
    else:
        fps = float(r_fps)

    # Frame count
    nb_frames = video_stream.get("nb_frames")
    if nb_frames and nb_frames.isdigit():
        frame_count = int(nb_frames)
    else:
        duration_sec = float(data.get("format", {}).get("duration", 0.0))
        frame_count = int(round(duration_sec * fps))

    duration = float(data.get("format", {}).get("duration", 0.0))

    return {
        "width": width,
        "height": height,
        "fps": fps,
        "frame_count": frame_count,
        "duration_sec": duration,
        "codec": codec,
        "resolution": f"{width}x{height}",
    }
