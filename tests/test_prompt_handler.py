from __future__ import annotations

from app.orchestration.prompt_handler import process_prompt, get_effective_negative_prompt, DEFAULT_NEGATIVE_PROMPT


def test_raw_mode_exact_byte_for_byte_identity():
    test_cases = [
        "Character breathes slowly. Camera static.",
        "A woman looking left, 4k cinematic lighting, ultra-realistic",
        "  Leading and trailing whitespace test  \n\t",
        "Special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?",
        "Multi-line prompt\nSecond line\nThird line",
        "",
    ]
    for prompt in test_cases:
        inference_prompt = process_prompt(prompt, mode="raw")
        assert inference_prompt == prompt
        assert inference_prompt.encode("utf-8") == prompt.encode("utf-8")


def test_negative_prompt():
    assert get_effective_negative_prompt(None) == DEFAULT_NEGATIVE_PROMPT
    assert get_effective_negative_prompt("") == DEFAULT_NEGATIVE_PROMPT
    assert get_effective_negative_prompt("custom negative") == "custom negative"
