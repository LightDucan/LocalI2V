from __future__ import annotations

import pytest
from app.orchestration.comfyui_client import ComfyUIClient, ComfyUIConnectionError


def test_comfyui_offline_readable_error():
    client = ComfyUIClient(base_url="http://127.0.0.1:9999")
    with pytest.raises(ComfyUIConnectionError, match="ComfyUI is offline or unreachable"):
        client.check_health(timeout=1.0)
