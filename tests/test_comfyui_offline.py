from __future__ import annotations

import pytest
from app.orchestration.comfyui_client import ComfyUIClient, ComfyUIConnectionError


def test_comfyui_offline_readable_error():
    client = ComfyUIClient(base_url="http://127.0.0.1:9999")
    with pytest.raises(ComfyUIConnectionError, match="ComfyUI is offline or unreachable"):
        client.check_health(timeout=1.0)


def test_comfyui_offline_get_history_connection_error():
    client = ComfyUIClient(base_url="http://127.0.0.1:9999")
    with pytest.raises(ComfyUIConnectionError, match="Failed to connect to ComfyUI history endpoint"):
        client.get_history("dummy_prompt_id")


def test_comfyui_offline_wait_for_completion_fail_fast():
    client = ComfyUIClient(base_url="http://127.0.0.1:9999")
    with pytest.raises(ComfyUIConnectionError, match="Lost connection to ComfyUI during active job"):
        client.wait_for_completion(prompt_id="dummy_prompt_id", client_id="dummy_client_id", timeout_sec=60.0)
