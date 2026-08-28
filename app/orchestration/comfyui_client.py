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

    def interrupt(self, prompt_id: str | None = None) -> bool:
        """Interrupts currently executing prompt and clears queued items on ComfyUI."""
        success = False
        try:
            req = urllib.request.Request(f"{self.base_url}/interrupt", data=b"", headers={})
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                success = (resp.status == 200)
        except Exception as exc:
            logger.warning("Failed to call ComfyUI /interrupt: %s", exc)

        # Also purge from queue if prompt_id is given or clear queue
        try:
            delete_payload = {"delete": [prompt_id]} if prompt_id else {"clear": True}
            req_q = urllib.request.Request(
                f"{self.base_url}/queue",
                data=json.dumps(delete_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req_q, timeout=3.0) as resp_q:
                pass
        except Exception:
            pass

        return success

    def get_history(self, prompt_id: str, timeout: float = 3.0) -> dict | None:
        """Fetches execution history for a given prompt_id. Propagates connection errors."""
        try:
            req = urllib.request.Request(f"{self.base_url}/history/{prompt_id}")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get(prompt_id)
        except (urllib.error.URLError, ConnectionError, OSError, TimeoutError) as exc:
            raise ComfyUIConnectionError(f"Failed to connect to ComfyUI history endpoint: {exc}") from exc
        except Exception as exc:
            logger.debug("Failed to parse history for %s: %s", prompt_id, exc)
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
        Guarantees strictly monotonic progress reporting up to 0.92 max.
        Fails fast after 5 consecutive connection failures.
        """
        start_time = time.perf_counter()
        ws_connected = False
        ws = None
        consecutive_poll_errors = 0
        max_poll_errors = 5

        # Monotonic progress tracking helper
        current_max_pct = [0.10]

        def emit_progress(pct: float, text: str):
            if progress_callback:
                monitored_pct = max(current_max_pct[0], min(0.92, round(pct, 3)))
                current_max_pct[0] = monitored_pct
                progress_callback(monitored_pct, text)

        try:
            ws = websocket.create_connection(f"{self.ws_url}?clientId={client_id}", timeout=5.0)
            ws.settimeout(0.5)
            ws_connected = True
            logger.info("Connected to ComfyUI WebSocket at %s", self.ws_url)
        except Exception as exc:
            logger.warning("Could not connect to ComfyUI WebSocket (%s). Falling back to polling.", exc)

        total_steps = 8
        current_step = 0

        try:
            while True:
                if cancel_check and cancel_check():
                    self.interrupt(prompt_id)
                    raise ComfyUIInterruptedError("Generation was cancelled by user.")

                elapsed = time.perf_counter() - start_time
                if elapsed > timeout_sec:
                    self.interrupt(prompt_id)
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
                                emit_progress(0.12, "Starting model execution in ComfyUI...")

                            elif mtype == "executing" and mdata.get("prompt_id") == prompt_id:
                                node = mdata.get("node")
                                if node is not None:
                                    emit_progress(0.15, f"Executing node {node}...")

                            elif mtype == "progress" and mdata.get("prompt_id") == prompt_id:
                                value = mdata.get("value", 0)
                                max_v = mdata.get("max", total_steps)
                                total_steps = max(total_steps, max_v)
                                current_step = value
                                # Map sampler steps smoothly to 0.15 -> 0.85 range
                                ratio = min(1.0, current_step / max(1, total_steps))
                                pct = 0.15 + 0.70 * ratio
                                emit_progress(pct, f"Sampling: step {current_step}/{total_steps} ({int(ratio * 100)}%)")

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
                try:
                    history = self.get_history(prompt_id)
                    consecutive_poll_errors = 0
                except ComfyUIConnectionError as poll_err:
                    consecutive_poll_errors += 1
                    logger.warning("Connection failure during active polling %d/%d: %s", consecutive_poll_errors, max_poll_errors, poll_err)
                    if consecutive_poll_errors >= max_poll_errors:
                        raise ComfyUIConnectionError("Lost connection to ComfyUI during active job (5 consecutive polling failures).") from poll_err
                    history = None

                if history:
                    status = history.get("status", {})
                    if status.get("completed", False):
                        emit_progress(0.90, "Decoded video frames from VAE. Finalizing...")
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
                    time.sleep(0.05)

        finally:
            if ws:
                try:
                    ws.close()
                except Exception:
                    pass
