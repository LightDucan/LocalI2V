from __future__ import annotations

import pytest
from pathlib import Path
from PIL import Image

from app.orchestration.image_handler import validate_and_prepare_image, InvalidImageError, preprocess_image_to_target


def test_portrait_contain_pad_preserves_framing():
    # 512x768 portrait image
    portrait = Image.new("RGB", (512, 768), color=(255, 0, 0))
    processed = preprocess_image_to_target(portrait, target_width=512, target_height=288, crop_fill=False)
    
    assert processed.size == (512, 288)
    # Height should scale to 288, width should scale to 288 * (512/768) = 192, padded horizontally with black
    # Check that left/right borders are black padding (0, 0, 0)
    assert processed.getpixel((10, 144)) == (0, 0, 0)
    assert processed.getpixel((500, 144)) == (0, 0, 0)
    # Check that center contains the red image content
    assert processed.getpixel((256, 144)) == (255, 0, 0)


def test_square_contain_pad_preserves_framing():
    # 512x512 square image
    square = Image.new("RGB", (512, 512), color=(0, 255, 0))
    processed = preprocess_image_to_target(square, target_width=512, target_height=288, crop_fill=False)
    
    assert processed.size == (512, 288)
    # Height scales to 288, width scales to 288, pillarboxed on left and right
    assert processed.getpixel((10, 144)) == (0, 0, 0)
    assert processed.getpixel((500, 144)) == (0, 0, 0)
    assert processed.getpixel((256, 144)) == (0, 255, 0)


def test_landscape_contain_pad_exact():
    # 1920x1080 16:9 image
    landscape = Image.new("RGB", (1920, 1080), color=(0, 0, 255))
    processed = preprocess_image_to_target(landscape, target_width=512, target_height=288, crop_fill=False)
    
    assert processed.size == (512, 288)
    # Scales exactly to 512x288 without padding
    assert processed.getpixel((0, 0)) == (0, 0, 255)
    assert processed.getpixel((511, 287)) == (0, 0, 255)


def test_crop_fill_mode():
    # 512x512 square image cropped to fill 512x288
    square = Image.new("RGB", (512, 512), color=(100, 150, 200))
    processed = preprocess_image_to_target(square, target_width=512, target_height=288, crop_fill=True)
    
    assert processed.size == (512, 288)
    # Center crop: no black bars anywhere
    assert processed.getpixel((0, 0)) == (100, 150, 200)
    assert processed.getpixel((511, 287)) == (100, 150, 200)


def test_validate_and_prepare_image_saving(tmp_path: Path):
    comfy_input = tmp_path / "comfy_input"
    saved_preprocessed = tmp_path / "preprocessed_input.png"
    
    png_path = tmp_path / "test.png"
    img = Image.new("RGB", (300, 600), color="yellow")
    img.save(png_path, format="PNG")
    
    dest_name, orig_w, orig_h, mode = validate_and_prepare_image(
        image_source=png_path,
        comfy_input_dir=comfy_input,
        target_width=512,
        target_height=288,
        crop_fill=False,
        save_preprocessed_path=saved_preprocessed,
    )
    
    assert (comfy_input / dest_name).exists()
    assert saved_preprocessed.exists()
    assert orig_w == 300
    assert orig_h == 600
    assert mode == "contain_pad"
    
    with Image.open(saved_preprocessed) as saved_img:
        assert saved_img.size == (512, 288)


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
