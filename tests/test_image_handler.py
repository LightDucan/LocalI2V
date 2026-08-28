from __future__ import annotations

import pytest
from pathlib import Path
from PIL import Image

from app.orchestration.image_handler import validate_and_prepare_image, InvalidImageError


def test_valid_image_formats(tmp_path: Path):
    comfy_input = tmp_path / "comfy_input"
    
    # 1. Valid PNG
    png_path = tmp_path / "test.png"
    img = Image.new("RGB", (256, 256), color="red")
    img.save(png_path, format="PNG")
    dest_name, w, h = validate_and_prepare_image(png_path, comfy_input_dir=comfy_input)
    assert (comfy_input / dest_name).exists()
    assert w == 256 and h == 256

    # 2. Valid JPG
    jpg_path = tmp_path / "test.jpg"
    img.save(jpg_path, format="JPEG")
    dest_name, w, h = validate_and_prepare_image(jpg_path, comfy_input_dir=comfy_input)
    assert (comfy_input / dest_name).exists()
    assert w == 256 and h == 256

    # 3. Valid WEBP
    webp_path = tmp_path / "test.webp"
    img.save(webp_path, format="WEBP")
    dest_name, w, h = validate_and_prepare_image(webp_path, comfy_input_dir=comfy_input)
    assert (comfy_input / dest_name).exists()
    assert w == 256 and h == 256


def test_nonexistent_file(tmp_path: Path):
    with pytest.raises(InvalidImageError, match="does not exist"):
        validate_and_prepare_image(tmp_path / "nonexistent.png", comfy_input_dir=tmp_path)


def test_unsupported_extension(tmp_path: Path):
    txt_path = tmp_path / "test.txt"
    txt_path.write_text("not an image", encoding="utf-8")
    with pytest.raises(InvalidImageError, match="Unsupported image format"):
        validate_and_prepare_image(txt_path, comfy_input_dir=tmp_path)


def test_corrupted_image(tmp_path: Path):
    corrupt_png = tmp_path / "corrupt.png"
    corrupt_png.write_bytes(b"NOT_A_PNG_HEADER_RANDOM_GARBAGE_BYTES")
    with pytest.raises(InvalidImageError, match="corrupted or not a valid image"):
        validate_and_prepare_image(corrupt_png, comfy_input_dir=tmp_path)
