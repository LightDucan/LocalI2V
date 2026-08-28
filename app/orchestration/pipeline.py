from __future__ import annotations

import datetime
import json
import logging
import random
import time
import uuid
from pathlib import Path
from typing import Callable

from app.orchestration.comfyui_client import (
    ComfyUIClient,
    ComfyUIConnectionError,
    ComfyUIExecutionError,
    ComfyUIInterruptedError,
    ComfyUIOOMError,
    ComfyUITimeoutError,
)
from app.orchestration.image_handler import InvalidImageError, validate_and_prepare_image
from app.orchestration.output_saver import assemble_video, save_metadata
from app.orchestration.prompt_handler import get_effective_negative_prompt, process_prompt
from app.presets.model_adapters.ltxv_adapter import LTXVModelAdapter

logger = logging.getLogger("locali2v.pipeline")

DEFAULT_TIMEOUT_SECONDS = 900.0


class GenerationResult:
    def __init__(
        self,
        success: bool,
        video_path: str | None = None,
        metadata_path: str | None = None,
        error_message: str | None = None,
        generation_time: float = 0.0,
        metadata: dict | None = None,
    ):
        self.success = success
        self.video_path = video_path
        self.metadata_path = metadata_path
        self.error_message = error_message
        self.generation_time = generation_time
        self.metadata = metadata or {}


class I2VPipeline:
    def __init__(
        self,
        comfy_url: str = "http://127.0.0.1:8188",
        workflow_path: str | Path = "app/orchestration/workflow_ltxv_i2v.json",
        output_dir: str | Path = "outputs",
        comfy_input_dir: str | Path = "comfyui/input",
        comfy_output_dir: str | Path = "comfyui/output",
    ):
        self.client = ComfyUIClient(base_url=comfy_url)
        self.workflow_template_path = Path(workflow_path)
        self.output_dir = Path(output_dir)
        self.comfy_input_dir = Path(comfy_input_dir)
        self.comfy_output_dir = Path(comfy_output_dir)

    def load_workflow_template(self) -> dict:
        if not self.workflow_template_path.exists():
            raise FileNotFoundError(f"Workflow template not found at {self.workflow_template_path}")
        with open(self.workflow_template_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def generate(
        self,
        image_path: str | Path,
        prompt: str,
        negative_prompt: str | None = None,
        seed: int | None = None,
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
        crop_fill: bool = False,
        timeout_sec: float = DEFAULT_TIMEOUT_SECONDS,
        progress_callback: Callable[[float, str], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> GenerationResult:
        """
        Executes the full local Image-to-Video generation pipeline with framing preservation and semantic controls.
        """
        start_time = time.perf_counter()
        if seed is None or seed < 0:
            seed = random.randint(0, 2**31 - 1)

        highest_progress = [0.0]

        def emit_progress(pct: float, text: str):
            if progress_callback:
                p = max(highest_progress[0], round(pct, 3))
                highest_progress[0] = p
                progress_callback(p, text)

        try:
            emit_progress(0.02, "Checking ComfyUI connection...")

            # 1. Health check
            self.client.check_health()

            emit_progress(0.05, "Validating and preprocessing source image...")

            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            preprocessed_out_path = self.output_dir / f"{timestamp_str}_{seed}_preprocessed_input.png"

            # 2. Image validation and staging with CONTAIN+PAD / CROP_FILL
            image_filename, orig_w, orig_h, preprocess_mode = validate_and_prepare_image(
                image_source=image_path,
                comfy_input_dir=self.comfy_input_dir,
                target_width=width,
                target_height=height,
                crop_fill=crop_fill,
                save_preprocessed_path=preprocessed_out_path,
            )

            # 3. Prompt handling (RAW mode invariant strictly preserved)
            inference_prompt = process_prompt(
                user_prompt=prompt,
                mode=mode,
                camera_preset=camera_preset,
                subject_mode=subject_mode,
            )
            eff_negative = get_effective_negative_prompt(negative_prompt)

            emit_progress(0.08, "Configuring workflow and applying semantic adapter...")

            # 4. Construct API workflow payload via LTXVModelAdapter
            raw_wf = self.load_workflow_template()
            prefix = f"locali2v_{timestamp_str}_{seed}"

            # Apply semantic controls via model adapter (modulates steps, cfg, strength, frame_rate)
            wf = LTXVModelAdapter.apply_controls(
                workflow=raw_wf,
                preserve=preserve,
                motion=motion,
                custom_seed=seed,
                custom_steps=steps,
                custom_cfg=cfg,
            )

            # Inject inputs
            wf["3"]["inputs"]["text"] = inference_prompt
            wf["4"]["inputs"]["text"] = eff_negative
            wf["6"]["inputs"]["image"] = image_filename
            wf["7"]["inputs"]["width"] = width
            wf["7"]["inputs"]["height"] = height
            wf["7"]["inputs"]["length"] = length
            wf["10"]["inputs"]["filename_prefix"] = prefix

            emit_progress(0.10, "Submitting prompt to ComfyUI...")

            client_id = str(uuid.uuid4())
            prompt_id = self.client.queue_prompt(workflow=wf, client_id=client_id)
            logger.info("Queued prompt %s (seed=%d, frames=%d, mode=%s, preserve=%s, motion=%s, framing=%s)", prompt_id, seed, length, mode, preserve, motion, preprocess_mode)

            # 5. Wait for execution (progress 0.10 -> 0.90)
            frame_files = self.client.wait_for_completion(
                prompt_id=prompt_id,
                client_id=client_id,
                timeout_sec=timeout_sec,
                progress_callback=emit_progress,
                cancel_check=cancel_check,
            )

            emit_progress(0.92, "Assembling MP4 video with FFmpeg...")

            # 6. Assemble MP4, extract preview frames, and write metadata
            video_path, preview_frames = assemble_video(
                frame_files=frame_files,
                comfy_output_dir=self.comfy_output_dir,
                output_dir=self.output_dir,
                seed=seed,
                fps=fps,
            )

            emit_progress(0.98, "Writing metadata sidecar...")

            gen_duration = round(time.perf_counter() - start_time, 2)
            meta = {
                "selected_model": "ltxv-2b-0.9.6-distilled-04-25.safetensors",
                "checkpoint_sha256": "94891bd4bd08de30d484befbfc54fdcffe6d1596a131baad700b9baa5e1de86b",
                "text_encoder": "t5xxl_fp8_e4m3fn.safetensors",
                "source_image": Path(image_path).name,
                "preprocess_mode": preprocess_mode,
                "original_input_size": f"{orig_w}x{orig_h}",
                "inference_input_size": f"{width}x{height}",
                "preprocessed_image": preprocessed_out_path.name if preprocessed_out_path.exists() else None,
                "preview_frames": preview_frames,
                "user_prompt": prompt,
                "inference_prompt": inference_prompt,
                "negative_prompt": eff_negative,
                "mode": mode,
                "preserve": preserve,
                "motion": motion,
                "camera_preset": camera_preset,
                "subject_mode": subject_mode,
                "seed": seed,
                "width": width,
                "height": height,
                "resolution": f"{width}x{height}",
                "frame_count": length,
                "fps": fps,
                "duration_seconds": round(length / fps, 2),
                "steps": wf["8"]["inputs"].get("steps", 8),
                "cfg": wf["8"]["inputs"].get("cfg", 3.0),
                "strength": wf["7"]["inputs"].get("strength", 0.82),
                "output_video": video_path.name,
                "generation_time_seconds": gen_duration,
                "created_at": datetime.datetime.now().isoformat(),
                "status": "SUCCESS",
            }
            json_path = save_metadata(video_path=video_path, metadata=meta)

            emit_progress(1.0, f"Generation complete in {gen_duration}s")

            return GenerationResult(
                success=True,
                video_path=str(video_path),
                metadata_path=str(json_path),
                generation_time=gen_duration,
                metadata=meta,
            )

        except InvalidImageError as exc:
            logger.error("Image validation error: %s", exc)
            return GenerationResult(
                success=False,
                error_message=f"Invalid Image: {exc}",
                generation_time=round(time.perf_counter() - start_time, 2),
            )
        except ComfyUIConnectionError as exc:
            logger.error("ComfyUI connection error: %s", exc)
            return GenerationResult(
                success=False,
                error_message=f"Connection Error: {exc}",
                generation_time=round(time.perf_counter() - start_time, 2),
            )
        except ComfyUIInterruptedError as exc:
            logger.info("Generation cancelled: %s", exc)
            return GenerationResult(
                success=False,
                error_message="Generation was cancelled by user.",
                generation_time=round(time.perf_counter() - start_time, 2),
            )
        except ComfyUIOOMError as exc:
            logger.error("CUDA OOM: %s", exc)
            return GenerationResult(
                success=False,
                error_message=f"Out of Memory: {exc}",
                generation_time=round(time.perf_counter() - start_time, 2),
            )
        except ComfyUITimeoutError as exc:
            logger.error("Generation timeout: %s", exc)
            return GenerationResult(
                success=False,
                error_message=f"Timeout: {exc}",
                generation_time=round(time.perf_counter() - start_time, 2),
            )
        except Exception as exc:
            logger.exception("Unexpected pipeline failure: %s", exc)
            return GenerationResult(
                success=False,
                error_message=f"Pipeline Failure: {exc}",
                generation_time=round(time.perf_counter() - start_time, 2),
            )
