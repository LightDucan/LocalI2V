from __future__ import annotations

import json
from pathlib import Path
from app.presets.model_adapters.ltxv_adapter import LTXVModelAdapter
from app.orchestration.prompt_handler import process_prompt


def test_semantic_to_model_adapter_mapping():
    base_wf = {
        "5": {"inputs": {"frame_rate": 8.0}},
        "7": {"inputs": {"strength": 1.0, "batch_size": 1}},
        "8": {"inputs": {"steps": 8, "cfg": 3.0, "denoise": 1.0, "seed": 42}},
    }

    # 1. Test Preserve Low vs High
    wf_low = LTXVModelAdapter.apply_controls(base_wf, preserve="low", motion="normal")
    assert wf_low["7"]["inputs"]["strength"] == 0.90
    assert wf_low["8"]["inputs"]["cfg"] == 2.5

    wf_high = LTXVModelAdapter.apply_controls(base_wf, preserve="high", motion="normal")
    assert wf_high["7"]["inputs"]["strength"] == 1.0
    assert wf_high["8"]["inputs"]["denoise"] == 0.92
    assert wf_high["8"]["inputs"]["cfg"] == 3.5

    # 2. Test Motion Subtle vs Strong
    wf_subtle = LTXVModelAdapter.apply_controls(base_wf, preserve="normal", motion="subtle")
    assert wf_subtle["5"]["inputs"]["frame_rate"] == 12.0
    assert wf_subtle["8"]["inputs"]["cfg"] == 2.5

    wf_strong = LTXVModelAdapter.apply_controls(base_wf, preserve="normal", motion="strong")
    assert wf_strong["5"]["inputs"]["frame_rate"] == 6.0
    assert wf_strong["8"]["inputs"]["cfg"] == 3.5


def test_raw_prompt_bypass_invariant():
    user_prompt = "A character turning left slowly. High quality 4k."
    for cam in ["static", "pan_left", "pan_right", "zoom_in"]:
        for subj in ["single", "two_subject"]:
            res = process_prompt(user_prompt, mode="raw", camera_preset=cam, subject_mode=subj)
            assert res == user_prompt
            assert res.encode("utf-8") == user_prompt.encode("utf-8")


def test_subject_and_camera_suffixes_outside_raw():
    user_prompt = "Two people walking"

    # Simple mode with pan_left and two_subject
    simple_res = process_prompt(user_prompt, mode="simple", camera_preset="pan_left", subject_mode="two_subject")
    assert "slow camera pan left" in simple_res
    assert "two distinct subjects in frame" in simple_res
    assert simple_res.startswith(user_prompt)

    # Cinematic mode
    cin_res = process_prompt(user_prompt, mode="cinematic", camera_preset="static", subject_mode="single")
    assert "cinematic lighting" in cin_res
    assert "static camera" in cin_res


def test_no_model_specific_node_ids_in_generic_ui_or_prompt_handler():
    root = Path(__file__).resolve().parents[1]
    ui_code = (root / "app" / "ui" / "main_ui.py").read_text(encoding="utf-8")
    prompt_code = (root / "app" / "orchestration" / "prompt_handler.py").read_text(encoding="utf-8")

    forbidden_patterns = ["LTXVImgToVideo", "CheckpointLoaderSimple", "KSampler", "VAEDecode"]
    for pattern in forbidden_patterns:
        assert pattern not in ui_code, f"Model node {pattern} leaked into main_ui.py"
        assert pattern not in prompt_code, f"Model node {pattern} leaked into prompt_handler.py"
