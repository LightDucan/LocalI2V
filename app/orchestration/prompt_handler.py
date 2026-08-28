from __future__ import annotations

DEFAULT_NEGATIVE_PROMPT = "low quality, worst quality, deformed, distorted, blurry, jerky motion"


def process_prompt(user_prompt: str, mode: str = "raw") -> str:
    """
    Processes the user motion prompt based on the selected mode.
    
    Invariant:
    When mode is "raw" (or default), the inference prompt MUST equal the user prompt byte-for-byte,
    with zero suffixes, transformations, or modifications.
    """
    if mode.lower() == "raw":
        return user_prompt

    # Modes like simple or cinematic can be extended in TASK-03
    return user_prompt


def get_effective_negative_prompt(custom_negative: str | None = None) -> str:
    if custom_negative and custom_negative.strip():
        return custom_negative.strip()
    return DEFAULT_NEGATIVE_PROMPT
