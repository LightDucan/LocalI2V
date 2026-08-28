from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("locali2v.frame_extractor")


def extract_frames(video_path: str | Path, output_dir: str | Path) -> list[Path]:
    """
    Extracts all video frames into sequentially numbered PNG images (%06d.png).
    """
    in_path = Path(video_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pattern = out_dir / "%06d.png"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(in_path),
        "-vsync", "0",
        "-qscale:v", "1",
        str(pattern),
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Frame extraction failed: {res.stderr}")

    extracted_files = sorted(list(out_dir.glob("*.png")))
    if not extracted_files:
        raise RuntimeError(f"No frames were extracted to {out_dir}")

    logger.info("Extracted %d frames from %s to %s", len(extracted_files), in_path.name, out_dir)
    return extracted_files
