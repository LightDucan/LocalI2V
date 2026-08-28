from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Callable

import websocket

logger = logging.getLogger("locali2v.comfyui_client")


class ComfyUIError(RuntimeError):
    """Base exception for ComfyUI client errors."""
    pass


class ComfyUIConnectionError(ComfyUIError):
    """Raised when ComfyUI server cannot be reached."""
    pass


class ComfyUIExecutionError(ComfyUIError):
    """Raised when a node or execution fails inside ComfyUI."""
    pass


class ComfyUIOOMError(ComfyUIExecutionError):
    """Raised when CUDA out of memory occurs during generation."""
    pass


class ComfyUITimeoutError(ComfyUIError):
    """Raised when execution times out."""
    pass


class ComfyUIInterruptedError(ComfyUIError):
    """Raised when execution was cancelled or interrupted."""
    pass


class ComfyUIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8188"):
        self.base_url = base_url.rstrip("/")
        parsed = urllib.parse.urlparse(self.base_url)
        self.host = parsed.netloc or "127.0.0.1:8188"
        self.ws_url = f"ws://{self.host}/ws"

    def check_health(self, timeout: float = 3.0) -> dict:
        """Verifies ComfyUI server is reachable and returns system stats."""
        try:
            req = urllib.request.Request(f"{self.base_url}/system_stats")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status != 200:
                    raise ComfyUIConnectionError(f"ComfyUI returned status code {resp.status}")
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as exc:
            raise ComfyUIConnectionError(
                f"ComfyUI is offline or unreachable at {self.base_url}. Please ensure ComfyUI is running."
            ) from exc

    def queue_prompt(self, workflow: dict, client_id: str | None = None) -> str:
        """Submits a prompt workflow to ComfyUI and returns the prompt_id."""
        client_id = client_id or str(uuid.uuid4())
        payload = json.dumps({"prompt": workflow, "client_id": client_id}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/prompt",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "error" in data:
                    raise ComfyUIExecutionError(f"Prompt validation error: {data['error']}")
                prompt_id = data.get("prompt_id")
                if not prompt_id:
                    raise ComfyUIExecutionError(f"No prompt_id returned from ComfyUI: {data}")
                return prompt_id
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            raise ComfyUIExecutionError(f"ComfyUI rejected prompt (HTTP {exc.code}): {err_body}") from exc
        except (urllib.error.URLError, ConnectionError, OSError) as exc:
            raise ComfyUIConnectionError(f"Failed to submit prompt to ComfyUI: {exc}") from exc

    def interrupt(self) -> bool:
        """Interrupts currently executing prompt on ComfyUI."""
        try:
            req = urllib.request.Request(f"{self.base_url}/interrupt", data=b"", headers={})
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                return resp.status == 200
        except Exception as exc:
            logger.warning("Failed to call ComfyUI /interrupt: %s", exc)
            return False

    def get_history(self, prompt_id: str) -> dict | None:
        """Fetches execution history for a given prompt_id."""
        try:
            req = urllib.request.Request(f"{self.base_url}/history/{prompt_id}")
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get(prompt_id)
        except Exception as exc:
            logger.debug("Failed to get history for %s: %s", prompt_id, exc)
            return None

    def wait_for_completion(
        self,
        prompt_id: str,
        client_id: str,
        timeout_sec: float = 900.0,
        progress_callback: Callable[[float, str], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> list[str]:
        """
        Listens for execution events over WebSocket (with polling fallback) until prompt finishes.
        Returns list of generated image filenames.
        """
        start_time = time.perf_counter()
        ws_connected = False
        ws = None

        try:
            ws = websocket.create_connection(f"{self.ws_url}?clientId={client_id}", timeout=5.0)
            ws.settimeout(1.0)
            ws_connected = True
            logger.info("Connected to ComfyUI WebSocket at %s", self.ws_url)
        except Exception as exc:
            logger.warning("Could not connect to ComfyUI WebSocket (%s). Falling back to polling.", exc)

        total_steps = 8
        current_step = 0

        try:
            while True:
                if cancel_check and cancel_check():
                    self.interrupt()
                    raise ComfyUIInterruptedError("Generation was cancelled by user.")

                elapsed = time.perf_counter() - start_time
                if elapsed > timeout_sec:
                    self.interrupt()
                    raise ComfyUITimeoutError(f"Generation timed out after {int(elapsed)} seconds (limit: {int(timeout_sec)}s).")

                # 1. Read WebSocket messages if connected
                if ws_connected and ws:
                    try:
                        raw_msg = ws.recv()
                        if isinstance(raw_msg, str):
                            msg = json.loads(raw_msg)
                            mtype = msg.get("type")
                            mdata = msg.get("data", {})

                            if mtype == "execution_start" and mdata.get("prompt_id") == prompt_id:
                                if progress_callback:
                                    progress_callback(0.05, "Starting model execution...")

                            elif mtype == "executing" and mdata.get("prompt_id") == prompt_id:
                                node = mdata.get("node")
                                if node is None:  # Execution complete
                                    pass
                                else:
                                    if progress_callback:
                                        progress_callback(0.1, f"Executing node {node}...")

                            elif mtype == "progress" and mdata.get("prompt_id") == prompt_id:
                                value = mdata.get("value", 0)
                                max_v = mdata.get("max", total_steps)
                                total_steps = max(total_steps, max_v)
                                current_step = value
                                # Map sampler steps to 0.2 -> 0.8 range
                                ratio = min(1.0, current_step / max(1, total_steps))
                                pct = 0.2 + 0.6 * ratio
                                if progress_callback:
                                    progress_callback(pct, f"Sampling: step {current_step}/{total_steps} ({int(ratio*100)}%)")

                            elif mtype == "execution_error" and mdata.get("prompt_id") == prompt_id:
                                err_msg = mdata.get("exception_message", "Unknown execution error")
                                if "out of memory" in err_msg.lower() or "cuda oom" in err_msg.lower():
                                    raise ComfyUIOOMError(f"CUDA Out of Memory during inference: {err_msg}")
                                raise ComfyUIExecutionError(f"ComfyUI node error: {err_msg}")

                            elif mtype == "execution_interrupted" and mdata.get("prompt_id") == prompt_id:
                                raise ComfyUIInterruptedError("ComfyUI execution was interrupted.")

                    except websocket.WebSocketTimeoutException:
                        pass
                    except (websocket.WebSocketConnectionClosedException, OSError) as ws_err:
                        logger.warning("WebSocket disconnected (%s). Switching to polling.", ws_err)
                        ws_connected = False
                        ws = None

                # 2. Check history status
                history = self.get_history(prompt_id)
                if history:
                    status = history.get("status", {})
                    if status.get("completed", False):
                        if progress_callback:
                            progress_callback(1.0, "Decoding and saving video frames...")
                        outputs = history.get("outputs", {})
                        image_files = []
                        for node_id, node_out in outputs.items():
                            if "images" in node_out:
                                image_files.extend([img["filename"] for img in node_out["images"]])
                        if not image_files:
                            raise ComfyUIExecutionError("Generation finished but no output images were produced.")
                        return image_files

                    # Check for errors in history status
                    messages = status.get("messages", [])
                    for m in messages:
                        if isinstance(m, list) and len(m) > 1 and m[0] == "execution_error":
                            err_info = str(m[1])
                            if "out of memory" in err_info.lower() or "cuda oom" in err_info.lower():
                                raise ComfyUIOOMError(f"CUDA Out of Memory: {err_info}")
                            raise ComfyUIExecutionError(f"ComfyUI execution error: {err_info}")

                if not ws_connected:
                    time.sleep(1.0)
                else:
                    time.sleep(0.1)

        finally:
            if ws:
                try:
                    ws.close()
                except Exception:
                    pass
