from __future__ import annotations

import json
from pathlib import Path
from PIL import Image
import pytest

from app.orchestration.image_handler import preprocess_image_to_target, validate_and_prepare_image
from app.orchestration.prompt_handler import process_prompt, get_effective_negative_prompt, DEFAULT_NEGATIVE_PROMPT
from app.presets.model_adapters.ltxv_adapter import LTXVModelAdapter


def test_h1_framing_contain_pad_composition_preservation(tmp_path: Path):
    """
    TASK-H1 Acceptance Test:
    Ensures portrait and square inputs are contained and padded rather than cropped by default.
    """
    # 1. Portrait 400x800
    portrait_path = tmp_path / "tall_portrait.png"
    img_tall = Image.new("RGB", (400, 800), color=(200, 50, 50))
    img_tall.save(portrait_path)

    saved_prep = tmp_path / "preprocessed_input.png"
    dest, orig_w, orig_h, mode = validate_and_prepare_image(
        image_source=portrait_path,
        comfy_input_dir=tmp_path / "comfy_in",
        target_width=512,
        target_height=288,
        crop_fill=False,
        save_preprocessed_path=saved_prep,
    )

    assert mode == "contain_pad"
    assert orig_w == 400 and orig_h == 800
    assert saved_prep.exists()

    with Image.open(saved_prep) as p_img:
        assert p_img.size == (512, 288)
        # Left and right borders must be black pillarbox padding
        assert p_img.getpixel((10, 144)) == (0, 0, 0)
        assert p_img.getpixel((500, 144)) == (0, 0, 0)
        # Center contains original red content
        assert p_img.getpixel((256, 144)) == (200, 50, 50)


def test_h1_crop_fill_toggle_behavior(tmp_path: Path):
    """
    TASK-H1 Acceptance Test:
    Ensures crop_fill=True fills the target frame without letterbox padding when explicitly requested.
    """
    square_path = tmp_path / "square.png"
    img_sq = Image.new("RGB", (500, 500), color=(50, 150, 250))
    img_sq.save(square_path)

    saved_prep = tmp_path / "preprocessed_crop.png"
    dest, orig_w, orig_h, mode = validate_and_prepare_image(
        image_source=square_path,
        comfy_input_dir=tmp_path / "comfy_in",
        target_width=512,
        target_height=288,
        crop_fill=True,
        save_preprocessed_path=saved_prep,
    )

    assert mode == "crop_fill"
    with Image.open(saved_prep) as p_img:
        assert p_img.size == (512, 288)
        # All corners contain content, no black padding
        assert p_img.getpixel((0, 0)) == (50, 150, 250)
        assert p_img.getpixel((511, 287)) == (50, 150, 250)


def test_h2_motion_calibration_dynamic_profiles():
    """
    TASK-H2 Acceptance Test:
    Verifies that Subtle, Normal, and Strong motion dynamics map to distinct, calibrated
    effective conditioning strengths and frame rate guidance.
    """
    dummy_wf = {
        "5": {"inputs": {"frame_rate": 8.0}},
        "7": {"inputs": {"strength": 1.0}},
        "8": {"inputs": {"steps": 8, "cfg": 3.0, "denoise": 1.0}},
    }

    subtle_wf = LTXVModelAdapter.apply_controls(dummy_wf, preserve="normal", motion="subtle")
    normal_wf = LTXVModelAdapter.apply_controls(dummy_wf, preserve="normal", motion="normal")
    strong_wf = LTXVModelAdapter.apply_controls(dummy_wf, preserve="normal", motion="strong")

    # Strength progression: Strong has lower latent clamp -> allows structural subject movement
    assert strong_wf["7"]["inputs"]["strength"] < normal_wf["7"]["inputs"]["strength"]
    assert normal_wf["7"]["inputs"]["strength"] < subtle_wf["7"]["inputs"]["strength"]

    # Frame rate guidance progression
    assert strong_wf["5"]["inputs"]["frame_rate"] == 6.0
    assert normal_wf["5"]["inputs"]["frame_rate"] == 8.0
    assert subtle_wf["5"]["inputs"]["frame_rate"] == 10.0

    # CFG progression
    assert strong_wf["8"]["inputs"]["cfg"] > normal_wf["8"]["inputs"]["cfg"]
    assert normal_wf["8"]["inputs"]["cfg"] > subtle_wf["8"]["inputs"]["cfg"]


def test_h3_raw_prompt_invariant_and_hardened_negative():
    """
    TASK-H3 Acceptance Test:
    Ensures RAW mode preserves byte-for-byte user prompt, suppresses watermark/text overlays,
    and never leaks camera or cinematic suffixes.
    """
    user_prompt = "A character wearing a red kimono looking forward."
    processed = process_prompt(user_prompt, mode="raw", camera_preset="pan_left", subject_mode="two_subject")

    # Absolute byte-for-byte equality
    assert processed == user_prompt
    assert processed.encode("utf-8") == user_prompt.encode("utf-8")
    assert "pan_left" not in processed
    assert "two_subject" not in processed
    assert "cinematic" not in processed

    # Hardened negative prompt includes anti-watermark and anti-text tokens
    eff_neg = get_effective_negative_prompt()
    assert "watermark" in eff_neg
    assert "text" in eff_neg
    assert "subtitles" in eff_neg
    assert "sticker" in eff_neg
    assert "overlay" in eff_neg
