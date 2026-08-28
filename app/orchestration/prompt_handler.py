from __future__ import annotations

DEFAULT_NEGATIVE_PROMPT = "low quality, worst quality, deformed, distorted, blurry, jerky motion"

CAMERA_PROMPT_MODIFIERS = {
    "static": ", static camera, locked camera angle",
    "pan_left": ", slow camera pan left",
    "pan_right": ", slow camera pan right",
    "zoom_in": ", slow subtle zoom in",
}

SUBJECT_PROMPT_MODIFIERS = {
    "single": "",
    "two_subject": ", two distinct subjects in frame",
}

CINEMATIC_MODIFIER = ", cinematic lighting, photorealistic, 4k"


def process_prompt(
    user_prompt: str,
    mode: str = "raw",
    camera_preset: str = "static",
    subject_mode: str = "single",
) -> str:
    """
    Constructs the model inference prompt from user prompt and semantic controls.

    RAW INVARIANT:
    When mode is 'raw', the returned inference prompt MUST be exactly byte-for-byte identical
    to user_prompt. No camera, cinematic, or subject suffixes are permitted in RAW mode.
    """
    mode_normalized = (mode or "raw").strip().lower()

    # Absolute RAW bypass
    if mode_normalized == "raw":
        return user_prompt

    base = user_prompt.strip()
    if not base:
        return ""

    suffix_parts = []

    if mode_normalized == "cinematic":
        suffix_parts.append(CINEMATIC_MODIFIER.lstrip(", "))

    cam_mod = CAMERA_PROMPT_MODIFIERS.get(camera_preset.lower(), "")
    if cam_mod:
        suffix_parts.append(cam_mod.lstrip(", "))

    subj_mod = SUBJECT_PROMPT_MODIFIERS.get(subject_mode.lower(), "")
    if subj_mod:
        suffix_parts.append(subj_mod.lstrip(", "))

    if suffix_parts:
        return f"{base}, {', '.join(suffix_parts)}"

    return base


def get_effective_negative_prompt(custom_negative: str | None = None) -> str:
    if custom_negative and custom_negative.strip():
        return custom_negative.strip()
    return DEFAULT_NEGATIVE_PROMPT
