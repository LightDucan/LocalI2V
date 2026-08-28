from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Generator

from app.orchestration.pipeline import GenerationResult, I2VPipeline

logger = logging.getLogger("locali2v.job_manager")


class JobManager:
    def __init__(self, pipeline: I2VPipeline | None = None):
        self.pipeline = pipeline or I2VPipeline()
        self._lock = threading.Lock()
        self._active_job_id: str | None = None
        self._cancel_requested = False
        self._status = "IDLE"
        self._status_text = "Ready"
        self._progress = 0.0
        self._latest_result: GenerationResult | None = None

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._status == "RUNNING"

    def cancel(self) -> bool:
        with self._lock:
            if self._status != "RUNNING":
                return False
            self._cancel_requested = True
            self._status_text = "Cancelling generation..."
            logger.info("Cancellation requested for job %s", self._active_job_id)
        # Attempt immediate interrupt via ComfyUI client
        self.pipeline.client.interrupt()
        return True

    def run_job_stream(
        self,
        image_path: str,
        prompt: str,
        negative_prompt: str | None = None,
        seed: int = -1,
        width: int = 512,
        height: int = 288,
        length: int = 25,
        fps: float = 8.0,
        steps: int = 8,
        cfg: float = 3.0,
        mode: str = "raw",
    ) -> Generator[tuple[float, str, str | None, str | None], None, None]:
        """
        Executes a job synchronously while yielding progress tuples:
        yields: (progress_float, status_text, video_path_or_none, error_message_or_none)
        """
        with self._lock:
            if self._status == "RUNNING":
                yield 0.0, "Another generation is currently in progress. Please wait or cancel.", None, "A job is already running."
                return

            self._active_job_id = str(uuid.uuid4())
            self._cancel_requested = False
            self._status = "RUNNING"
            self._status_text = "Initializing pipeline..."
            self._progress = 0.0
            self._latest_result = None

        yield 0.05, "Validating input and connecting to engine...", None, None

        current_progress = [0.05]
        current_text = ["Validating input..."]

        def on_progress(pct: float, text: str):
            current_progress[0] = pct
            current_text[0] = text
            self._progress = pct
            self._status_text = text

        def check_cancel() -> bool:
            return self._cancel_requested

        try:
            result = self.pipeline.generate(
                image_path=image_path,
                prompt=prompt,
                negative_prompt=negative_prompt,
                seed=seed,
                width=width,
                height=height,
                length=length,
                fps=fps,
                steps=steps,
                cfg=cfg,
                mode=mode,
                progress_callback=on_progress,
                cancel_check=check_cancel,
            )

            with self._lock:
                self._latest_result = result
                if result.success:
                    self._status = "COMPLETED"
                    self._status_text = f"Generation complete in {result.generation_time}s"
                    self._progress = 1.0
                    yield 1.0, self._status_text, result.video_path, None
                else:
                    if self._cancel_requested:
                        self._status = "CANCELLED"
                        self._status_text = "Generation cancelled."
                    else:
                        self._status = "FAILED"
                        self._status_text = f"Failed: {result.error_message}"
                    yield current_progress[0], self._status_text, None, result.error_message

        except Exception as exc:
            with self._lock:
                self._status = "FAILED"
                self._status_text = f"Unhandled Error: {exc}"
                yield 0.0, self._status_text, None, str(exc)

        finally:
            with self._lock:
                self._status = "IDLE"
                self._active_job_id = None
                self._cancel_requested = False
