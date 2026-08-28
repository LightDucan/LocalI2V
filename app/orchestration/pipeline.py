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

logger = logging.getLogger("locali2v.pipeline")

# Baseline timeout: max(15 minutes, 3 * baseline_25_frame_runtime = 3 * 64s = 192s) = 900 seconds
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
        steps: int = 8,
        cfg: float = 3.0,
        mode: str = "raw",
        timeout_sec: float = DEFAULT_TIMEOUT_SECONDS,
        progress_callback: Callable[[float, str], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> GenerationResult:
        """
        Executes the full local Image-to-Video generation pipeline.
        """
        start_time = time.perf_counter()
        if seed is None or seed < 0:
            seed = random.randint(0, 2**31 - 1)

        try:
            if progress_callback:
                progress_callback(0.02, "Checking ComfyUI connection...")

            # 1. Health check
            self.client.check_health()

            if progress_callback:
                progress_callback(0.05, "Validating source image...")

            # 2. Image validation and staging
            image_filename, orig_w, orig_h = validate_and_prepare_image(
                image_source=image_path,
                comfy_input_dir=self.comfy_input_dir,
            )

            # 3. Prompt handling (RAW mode invariant preserved)
            inference_prompt = process_prompt(prompt, mode=mode)
            eff_negative = get_effective_negative_prompt(negative_prompt)

            if progress_callback:
                progress_callback(0.08, "Configuring workflow...")

            # 4. Construct API workflow payload
            wf = self.load_workflow_template()
            prefix = f"locali2v_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{seed}"

            wf["3"]["inputs"]["text"] = inference_prompt
            wf["4"]["inputs"]["text"] = eff_negative
            wf["5"]["inputs"]["frame_rate"] = fps
            wf["6"]["inputs"]["image"] = image_filename
            wf["7"]["inputs"]["width"] = width
            wf["7"]["inputs"]["height"] = height
            wf["7"]["inputs"]["length"] = length
            wf["7"]["inputs"]["batch_size"] = 1
            if "batch_type" in wf["7"]["inputs"]:
                del wf["7"]["inputs"]["batch_type"]
            wf["8"]["inputs"]["seed"] = seed
            wf["8"]["inputs"]["steps"] = steps
            wf["8"]["inputs"]["cfg"] = cfg
            wf["10"]["inputs"]["filename_prefix"] = prefix

            client_id = str(uuid.uuid4())
            prompt_id = self.client.queue_prompt(workflow=wf, client_id=client_id)
            logger.info("Queued prompt %s (seed=%d, frames=%d)", prompt_id, seed, length)

            # 5. Wait for execution
            frame_files = self.client.wait_for_completion(
                prompt_id=prompt_id,
                client_id=client_id,
                timeout_sec=timeout_sec,
                progress_callback=progress_callback,
                cancel_check=cancel_check,
            )

            if progress_callback:
                progress_callback(0.9, "Assembling MP4 video...")

            # 6. Assemble MP4 and write metadata
            video_path = assemble_video(
                frame_files=frame_files,
                comfy_output_dir=self.comfy_output_dir,
                output_dir=self.output_dir,
                seed=seed,
                fps=fps,
            )

            gen_duration = round(time.perf_counter() - start_time, 2)
            meta = {
                "selected_model": "ltxv-2b-0.9.6-distilled-04-25.safetensors",
                "checkpoint_sha256": "94891bd4bd08de30d484befbfc54fdcffe6d1596a131baad700b9baa5e1de86b",
                "text_encoder": "t5xxl_fp8_e4m3fn.safetensors",
                "source_image": Path(image_path).name,
                "user_prompt": prompt,
                "inference_prompt": inference_prompt,
                "negative_prompt": eff_negative,
                "mode": mode,
                "seed": seed,
                "width": width,
                "height": height,
                "resolution": f"{width}x{height}",
                "frame_count": length,
                "fps": fps,
                "duration_seconds": round(length / fps, 2),
                "steps": steps,
                "cfg": cfg,
                "output_video": video_path.name,
                "generation_time_seconds": gen_duration,
                "created_at": datetime.datetime.now().isoformat(),
                "status": "SUCCESS",
            }
            json_path = save_metadata(video_path=video_path, metadata=meta)

            if progress_callback:
                progress_callback(1.0, "Complete!")

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
