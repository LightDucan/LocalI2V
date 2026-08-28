from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Generator

from app.history.database import HistoryDatabase
from app.orchestration.pipeline import GenerationResult, I2VPipeline
from app.postprocess.postprocess_pipeline import postprocess_video

logger = logging.getLogger("locali2v.job_manager")


class JobManager:
    def __init__(self, pipeline: I2VPipeline | None = None, db: HistoryDatabase | None = None):
        self.pipeline = pipeline or I2VPipeline()
        self.db = db or HistoryDatabase()
        self._lock = threading.Lock()
        self._active_job_id: str | None = None
        self._cancel_requested = False
        self._status = "IDLE"
        self._status_text = "Ready"
        self._progress = 0.0
        self._latest_result: dict[str, Any] | None = None

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
            if self._active_job_id:
                self.db.update_job_status(self._active_job_id, status="CANCELLED", error_message="Cancelled by user")
            logger.info("Cancellation requested for job %s", self._active_job_id)

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
        enhance_enabled: bool = True,
    ) -> Generator[tuple[float, str, str | None, str | None], None, None]:
        """
        Executes a generation job on a background worker thread with real-time streaming progress,
        integrated post-processing enhancement (2x + 24fps), and SQLite job lifecycle persistence.

        Yields:
            (progress_float: float, status_text: str, video_path: str | None, error_msg: str | None)
        """
        job_id = str(uuid.uuid4())

        with self._lock:
            if self._status == "RUNNING":
                yield 0.0, "Another generation is currently in progress.", None, "A job is already running."
                return

            self._active_job_id = job_id
            self._cancel_requested = False
            self._status = "RUNNING"
            self._status_text = "Starting generation..."
            self._progress = 0.0
            self._latest_result = None

        # Persist job in SQLite with initial QUEUED status
        settings = {
            "width": width,
            "height": height,
            "length": length,
            "fps": fps,
            "steps": steps,
            "cfg": cfg,
            "enhance_enabled": enhance_enabled,
        }
        self.db.create_job(
            job_id=job_id,
            source_image=image_path,
            user_prompt=prompt,
            seed=seed,
            mode=mode,
            preserve=preserve,
            motion=motion,
            camera_preset=camera_preset,
            subject_mode=subject_mode,
            enhance_enabled=enhance_enabled,
            settings=settings,
        )
        self.db.update_job_status(job_id=job_id, status="RUNNING")

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
                # 1. Base I2V Generation (0.0 -> 0.70 of total progress if enhance is on, or 1.0)
                gen_scale = 0.70 if enhance_enabled else 1.0

                def scaled_progress(p: float, t: str):
                    on_progress(p * gen_scale, t)

                gen_res = self.pipeline.generate(
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
                    progress_callback=scaled_progress,
                    cancel_check=check_cancel,
                )

                if not gen_res.success:
                    event_queue.put(("RESULT", gen_res, None))
                    return

                raw_video_path = gen_res.video_path
                inference_prompt = gen_res.metadata.get("inference_prompt", prompt)
                effective_seed = gen_res.metadata.get("seed", seed)

                # Update DB with raw output and actual inference prompt
                self.db.update_job_status(
                    job_id=job_id,
                    status="RUNNING",
                    raw_output=raw_video_path,
                    inference_prompt=inference_prompt,
                    settings_update={"effective_seed": effective_seed},
                )

                # 2. Integrated Post-Processing Enhancement (0.70 -> 1.0)
                enhanced_video_path = None
                post_details = None

                if enhance_enabled and raw_video_path and not check_cancel():
                    on_progress(0.72, "Starting 2x upscale & 24fps frame interpolation...")

                    def post_progress(p: float, t: str):
                        on_progress(0.70 + p * 0.28, t)

                    post_res = postprocess_video(
                        raw_video_path=raw_video_path,
                        source_fps=fps,
                        enable_upscale=True,
                        upscale_scale=2,
                        enable_interpolate=True,
                        target_fps=24.0,
                        progress_callback=post_progress,
                    )
                    if post_res.success:
                        enhanced_video_path = post_res.enhanced_video_path
                        post_details = post_res.details
                    else:
                        logger.warning("Post-processing failed (%s), raw video retained.", post_res.error_message)

                event_queue.put(("RESULT", gen_res, enhanced_video_path, post_details))

            except Exception as exc:
                event_queue.put(("ERROR", str(exc)))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        last_yielded_pct = 0.0
        last_yielded_text = "Starting pipeline..."
        yield 0.01, last_yielded_text, None, None

        final_gen_res: GenerationResult | None = None
        final_enhanced_path: str | None = None
        final_post_details: dict | None = None
        error_result: str | None = None

        try:
            while thread.is_alive() or not event_queue.empty():
                try:
                    event = event_queue.get(timeout=0.1)
                    etype = event[0]

                    if etype == "PROGRESS":
                        _, pct, text = event
                        last_yielded_pct = max(last_yielded_pct, pct)
                        last_yielded_text = text
                        yield last_yielded_pct, last_yielded_text, None, None

                    elif etype == "RESULT":
                        final_gen_res = event[1]
                        if len(event) > 2:
                            final_enhanced_path = event[2]
                        if len(event) > 3:
                            final_post_details = event[3]
                        break

                    elif etype == "ERROR":
                        error_result = event[1]
                        break

                except queue.Empty:
                    pass

            if final_gen_res is None and error_result is None:
                try:
                    event = event_queue.get_nowait()
                    if event[0] == "RESULT":
                        final_gen_res = event[1]
                        if len(event) > 2:
                            final_enhanced_path = event[2]
                        if len(event) > 3:
                            final_post_details = event[3]
                    elif event[0] == "ERROR":
                        error_result = event[1]
                except queue.Empty:
                    pass

            with self._lock:
                if final_gen_res is not None:
                    if final_gen_res.success:
                        chosen_video = final_enhanced_path or final_gen_res.video_path
                        self._status = "DONE"
                        self._status_text = f"Complete! Video: {Path(chosen_video).name}"
                        self._progress = 1.0

                        # Persist successful completion in SQLite
                        self.db.update_job_status(
                            job_id=job_id,
                            status="DONE",
                            raw_output=final_gen_res.video_path,
                            enhanced_output=final_enhanced_path,
                            inference_prompt=final_gen_res.metadata.get("inference_prompt"),
                            settings_update={"postprocess": final_post_details} if final_post_details else None,
                        )
                        yield 1.0, self._status_text, chosen_video, None
                    else:
                        if self._cancel_requested:
                            self._status = "CANCELLED"
                            self._status_text = "Generation was cancelled."
                            self.db.update_job_status(job_id=job_id, status="CANCELLED")
                        else:
                            self._status = "FAILED"
                            self._status_text = f"Failed: {final_gen_res.error_message}"
                            self.db.update_job_status(job_id=job_id, status="FAILED", error_message=final_gen_res.error_message)
                        yield last_yielded_pct, self._status_text, None, final_gen_res.error_message
                elif error_result is not None:
                    self._status = "FAILED"
                    self._status_text = f"Failed: {error_result}"
                    self.db.update_job_status(job_id=job_id, status="FAILED", error_message=error_result)
                    yield last_yielded_pct, self._status_text, None, error_result
                else:
                    self._status = "FAILED"
                    self._status_text = "Pipeline terminated unexpectedly."
                    self.db.update_job_status(job_id=job_id, status="FAILED", error_message="Worker exited without result")
                    yield last_yielded_pct, self._status_text, None, "Worker exited without result."

        finally:
            with self._lock:
                self._status = "IDLE"
                self._active_job_id = None
                self._cancel_requested = False
