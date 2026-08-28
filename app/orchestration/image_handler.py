from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from PIL import Image, ImageOps

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


class InvalidImageError(ValueError):
    """Raised when an uploaded image is invalid or cannot be processed."""
    pass


def preprocess_image_to_target(
    img: Image.Image,
    target_width: int = 512,
    target_height: int = 288,
    crop_fill: bool = False,
) -> Image.Image:
    """
    Preprocesses an input PIL image to target dimensions.
    
    If crop_fill is False (DEFAULT):
        Uses CONTAIN + PAD (letterbox/pillarbox). The entire input image composition
        is preserved without any cropping, scaled down/up to fit within target dimensions,
        and centered on a black canvas.
        
    If crop_fill is True:
        Uses CROP-TO-FILL. The image scales to cover the entire target canvas and
        is center-cropped to target dimensions.
    """
    # Convert mode to RGB safely
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        alpha_img = img.convert("RGBA")
        canvas = Image.new("RGBA", alpha_img.size, (0, 0, 0, 255))
        canvas.paste(alpha_img, mask=alpha_img.split()[3])
        rgb_img = canvas.convert("RGB")
    elif img.mode != "RGB":
        rgb_img = img.convert("RGB")
    else:
        rgb_img = img.copy()

    orig_w, orig_h = rgb_img.size

    if crop_fill:
        # CROP-TO-FILL
        scale = max(target_width / orig_w, target_height / orig_h)
        new_w = max(1, round(orig_w * scale))
        new_h = max(1, round(orig_h * scale))
        resized = rgb_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Center crop to target_width x target_height
        left = max(0, (new_w - target_width) // 2)
        top = max(0, (new_h - target_height) // 2)
        final_img = resized.crop((left, top, left + target_width, top + target_height))
    else:
        # CONTAIN + PAD (Letterbox / Pillarbox) - Default composition safe
        scale = min(target_width / orig_w, target_height / orig_h)
        new_w = max(1, round(orig_w * scale))
        new_h = max(1, round(orig_h * scale))
        resized = rgb_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        final_img = Image.new("RGB", (target_width, target_height), color=(0, 0, 0))
        paste_x = (target_width - new_w) // 2
        paste_y = (target_height - new_h) // 2
        final_img.paste(resized, (paste_x, paste_y))

    return final_img


def validate_and_prepare_image(
    image_source: str | Path,
    comfy_input_dir: str | Path = "comfyui/input",
    target_width: int = 512,
    target_height: int = 288,
    crop_fill: bool = False,
    save_preprocessed_path: str | Path | None = None,
) -> tuple[str, int, int, str]:
    """
    Validates the input image (PNG/JPG/WEBP), preprocesses it according to crop_fill mode
    (CONTAIN+PAD by default), and saves a safe copy into ComfyUI's input directory and
    optionally to save_preprocessed_path.

    Returns: (input_filename_in_comfy, orig_width, orig_height, preprocess_mode)
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
            orig_width, orig_height = img.size
            img_format = (img.format or "").upper()
            if img_format not in {"PNG", "JPEG", "WEBP", "JPG"}:
                raise InvalidImageError(f"Invalid image format decoded: {img_format}")
            
            # Preprocess image
            processed_img = preprocess_image_to_target(
                img=img,
                target_width=target_width,
                target_height=target_height,
                crop_fill=crop_fill,
            )
    except InvalidImageError:
        raise
    except Exception as exc:
        raise InvalidImageError(f"Failed to process image: {exc}") from exc

    target_dir = Path(comfy_input_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    dest_filename = f"locali2v_input_{uuid.uuid4().hex[:12]}.png"
    dest_path = target_dir / dest_filename
    processed_img.save(dest_path, format="PNG")

    preprocess_mode = "crop_fill" if crop_fill else "contain_pad"

    if save_preprocessed_path is not None:
        save_path = Path(save_preprocessed_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        processed_img.save(save_path, format="PNG")

    return dest_filename, orig_width, orig_height, preprocess_mode
