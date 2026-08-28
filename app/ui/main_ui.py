from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import gradio as gr
from app.jobs.job_manager import JobManager
from app.system.logger import configure_logging

logger = configure_logging()
job_manager = JobManager()


def on_generate(image, prompt, seed, progress=gr.Progress(track_tqdm=False)):
    if not image:
        gr.Warning("Please upload a source image first.")
        yield None, "Error: No source image provided.", gr.update(interactive=True), gr.update(interactive=False)
        return

    if not prompt or not prompt.strip():
        gr.Warning("Please enter a motion prompt.")
        yield None, "Error: Motion prompt cannot be empty.", gr.update(interactive=True), gr.update(interactive=False)
        return

    yield None, "Starting generation...", gr.update(interactive=False), gr.update(interactive=True)

    video_result = None
    status_msg = "Running..."

    for pct, status_text, vid_path, err_msg in job_manager.run_job_stream(
        image_path=image,
        prompt=prompt,
        seed=int(seed) if seed is not None else -1,
        mode="raw",
    ):
        progress(pct, desc=status_text)
        if vid_path:
            video_result = vid_path
            status_msg = status_text
        elif err_msg:
            status_msg = f"Error: {err_msg}"
            gr.Warning(status_msg)
        else:
            status_msg = status_text

        yield video_result, status_msg, gr.update(interactive=False), gr.update(interactive=True)

    yield video_result, status_msg, gr.update(interactive=True), gr.update(interactive=False)


def on_cancel():
    success = job_manager.cancel()
    if success:
        return "Cancellation requested..."
    return "No active job to cancel."


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="LocalI2V V0.1 — Image to Video") as demo:
        gr.Markdown("# 🎬 LocalI2V V0.1")
        gr.Markdown(
            "Local-only AI Image-to-Video generation running on Pascal GTX 1070. "
            "Powered by LTX-Video 2B distilled and ComfyUI."
        )

        with gr.Row():
            with gr.Column(scale=1):
                image_input = gr.Image(label="Source Image (PNG, JPG, WEBP)", type="filepath")
                prompt_input = gr.Textbox(
                    label="Motion Prompt",
                    placeholder="Describe character motion (e.g., Character breathes slowly. Camera static.)",
                    lines=4,
                )
                with gr.Row():
                    seed_input = gr.Number(label="Seed (-1 for random)", value=-1, precision=0)

                with gr.Row():
                    generate_btn = gr.Button("Generate Video", variant="primary", interactive=True)
                    cancel_btn = gr.Button("Cancel", variant="stop", interactive=False)

            with gr.Column(scale=1):
                status_box = gr.Textbox(label="Status & Progress", value="Ready", interactive=False)
                video_output = gr.Video(label="Generated Video Output", interactive=False, autoplay=True)

        generate_event = generate_btn.click(
            fn=on_generate,
            inputs=[image_input, prompt_input, seed_input],
            outputs=[video_output, status_box, generate_btn, cancel_btn],
        )

        cancel_btn.click(
            fn=on_cancel,
            inputs=[],
            outputs=[status_box],
            cancels=[generate_event],
        )

    return demo


if __name__ == "__main__":
    logger.info("LocalI2V UI started on 127.0.0.1:7860")
    build_ui().launch(server_name="127.0.0.1", server_port=7860, share=False, inbrowser=False)
