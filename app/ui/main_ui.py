from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import gradio as gr

from app.system.logger import configure_logging

logger = configure_logging()


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="LocalI2V V0.1") as demo:
        gr.Markdown("# LocalI2V V0.1")
        gr.Markdown("Bootstrap shell only — feature wiring is implemented by the task queue.")
        with gr.Row():
            with gr.Column():
                gr.Image(label="Source Image", type="filepath")
            with gr.Column():
                gr.Textbox(label="Motion Prompt", lines=5)
                gr.Button("Generate", variant="primary", interactive=False)
                gr.Button("Cancel", interactive=False)
        gr.Video(label="Output Preview")
    return demo


if __name__ == "__main__":
    logger.info("LocalI2V UI shell started")
    build_ui().launch(server_name="127.0.0.1", share=False, inbrowser=True)
