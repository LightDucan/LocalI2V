from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from PIL import Image

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


class InvalidImageError(ValueError):
    """Raised when an uploaded image is invalid or cannot be processed."""
    pass


def validate_and_prepare_image(image_source: str | Path, comfy_input_dir: str | Path = "comfyui/input") -> tuple[str, int, int]:
    """
    Validates the input image (PNG/JPG/WEBP) and copies a safe copy into ComfyUI's input directory.
    Returns: (input_filename_in_comfy, width, height)
    """
    path = Path(image_source)
    if not path.exists() or not path.is_file():
        raise InvalidImageError(f"Image file does not exist: {image_source}")

    ext = path.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise InvalidImageError(
            f"Unsupported image format '{ext}'. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    try:
        with Image.open(path) as img:
            img.verify()
    except Exception as exc:
        raise InvalidImageError(f"File is corrupted or not a valid image: {exc}") from exc

    try:
        with Image.open(path) as img:
            width, height = img.size
            img_format = (img.format or "").upper()
            if img_format not in {"PNG", "JPEG", "WEBP", "JPG"}:
                raise InvalidImageError(f"Invalid image format decoded: {img_format}")
    except Exception as exc:
        raise InvalidImageError(f"Failed to read image dimensions: {exc}") from exc

    target_dir = Path(comfy_input_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    dest_filename = f"locali2v_input_{uuid.uuid4().hex[:12]}{ext}"
    dest_path = target_dir / dest_filename
    shutil.copy2(path, dest_path)

    return dest_filename, width, height
