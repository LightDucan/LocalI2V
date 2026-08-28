from __future__ import annotations

import logging
import queue
import threading
import time
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
        """Requests cancellation of currently active generation."""
        with self._lock:
            if self._status != "RUNNING":
                return False
            self._cancel_requested = True
            self._status_text = "Cancelling generation..."
            logger.info("Cancellation requested for job %s", self._active_job_id)

        # Call ComfyUI interrupt immediately
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
        steps: int | None = None,
        cfg: float | None = None,
        mode: str = "raw",
        preserve: str = "normal",
        motion: str = "normal",
        camera_preset: str = "static",
        subject_mode: str = "single",
    ) -> Generator[tuple[float, str, str | None, str | None], None, None]:
        """
        Executes a generation job on a background worker thread while yielding
        real-time progress updates from a thread-safe event queue.
        
        Yields:
            (progress_float: float, status_text: str, video_path: str | None, error_msg: str | None)
        """
        with self._lock:
            if self._status == "RUNNING":
                yield 0.0, "Another generation is currently in progress.", None, "A job is already running."
                return

            self._active_job_id = str(uuid.uuid4())
            self._cancel_requested = False
            self._status = "RUNNING"
            self._status_text = "Starting generation..."
            self._progress = 0.0
            self._latest_result = None

        event_queue: queue.Queue = queue.Queue()

        def on_progress(pct: float, text: str):
            with self._lock:
                self._progress = pct
                self._status_text = text
            event_queue.put(("PROGRESS", pct, text))

        def check_cancel() -> bool:
            with self._lock:
                return self._cancel_requested

        def worker():
            try:
                res = self.pipeline.generate(
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
                    preserve=preserve,
                    motion=motion,
                    camera_preset=camera_preset,
                    subject_mode=subject_mode,
                    progress_callback=on_progress,
                    cancel_check=check_cancel,
                )
                event_queue.put(("RESULT", res))
            except Exception as exc:
                event_queue.put(("ERROR", str(exc)))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        last_yielded_pct = 0.0
        last_yielded_text = "Starting pipeline..."
        yield 0.01, last_yielded_text, None, None

        final_result: GenerationResult | None = None
        error_result: str | None = None

        try:
            while thread.is_alive() or not event_queue.empty():
                try:
                    event = event_queue.get(timeout=0.1)
                    etype = event[0]

                    if etype == "PROGRESS":
                        _, pct, text = event
                        # Enforce monotonic yield
                        last_yielded_pct = max(last_yielded_pct, pct)
                        last_yielded_text = text
                        yield last_yielded_pct, last_yielded_text, None, None

                    elif etype == "RESULT":
                        final_result = event[1]
                        break

                    elif etype == "ERROR":
                        error_result = event[1]
                        break

                except queue.Empty:
                    # No new event in interval, continue listening
                    pass

            # If worker finished, drain any remaining RESULT event
            if final_result is None and error_result is None:
                try:
                    event = event_queue.get_nowait()
                    if event[0] == "RESULT":
                        final_result = event[1]
                    elif event[0] == "ERROR":
                        error_result = event[1]
                except queue.Empty:
                    pass

            with self._lock:
                if final_result is not None:
                    self._latest_result = final_result
                    if final_result.success:
                        self._status = "COMPLETED"
                        self._status_text = f"Generation complete in {final_result.generation_time}s"
                        self._progress = 1.0
                        yield 1.0, self._status_text, final_result.video_path, None
                    else:
                        if self._cancel_requested:
                            self._status = "CANCELLED"
                            self._status_text = "Generation was cancelled."
                        else:
                            self._status = "FAILED"
                            self._status_text = f"Failed: {final_result.error_message}"
                        yield last_yielded_pct, self._status_text, None, final_result.error_message
                elif error_result is not None:
                    self._status = "FAILED"
                    self._status_text = f"Failed: {error_result}"
                    yield last_yielded_pct, self._status_text, None, error_result
                else:
                    self._status = "FAILED"
                    self._status_text = "Pipeline terminated unexpectedly."
                    yield last_yielded_pct, self._status_text, None, "Worker exited without result."

        finally:
            with self._lock:
                self._status = "IDLE"
                self._active_job_id = None
                self._cancel_requested = False
