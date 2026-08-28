from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import gradio as gr
from app.history.database import HistoryDatabase
from app.jobs.job_manager import JobManager
from app.postprocess.postprocess_pipeline import postprocess_video
from app.system.diagnostics import get_system_status_summary
from app.system.logger import configure_logging

logger = configure_logging()
db = HistoryDatabase()
job_manager = JobManager(db=db)


def format_history_table() -> list[list[str]]:
    jobs = db.get_latest_jobs(10)
    rows = []
    for j in jobs:
        created = j["created_at"].split("T")[1][:8] if "T" in j["created_at"] else j["created_at"]
        raw_name = Path(j["raw_output"]).name if j.get("raw_output") else "-"
        enh_name = Path(j["enhanced_output"]).name if j.get("enhanced_output") else "-"
        rows.append([
            j["job_id"][:8],
            created,
            j["status"],
            j["mode"],
            str(j["seed"]),
            (j["user_prompt"] or "")[:40],
            raw_name,
            enh_name,
        ])
    return rows


def get_job_choices() -> list[str]:
    jobs = db.get_latest_jobs(10)
    return [j["job_id"] for j in jobs]


def on_mode_change(mode: str):
    is_raw = mode.lower() == "raw"
    return (
        gr.update(visible=not is_raw),
        gr.update(visible=not is_raw),
    )


def on_generate(
    image,
    prompt,
    seed,
    mode,
    preserve,
    motion,
    camera_preset,
    subject_mode,
    enhance_enabled,
    progress=gr.Progress(track_tqdm=False),
):
    if not image:
        gr.Warning("Please upload a source image first.")
        yield None, "Error: No source image provided.", gr.update(interactive=True), gr.update(interactive=False), format_history_table(), gr.update(choices=get_job_choices())
        return

    if not prompt or not prompt.strip():
        gr.Warning("Please enter a motion prompt.")
        yield None, "Error: Motion prompt cannot be empty.", gr.update(interactive=True), gr.update(interactive=False), format_history_table(), gr.update(choices=get_job_choices())
        return

    yield None, "Starting generation...", gr.update(interactive=False), gr.update(interactive=True), format_history_table(), gr.update(choices=get_job_choices())

    video_result = None
    status_msg = "Running..."

    for pct, status_text, vid_path, err_msg in job_manager.run_job_stream(
        image_path=image,
        prompt=prompt,
        seed=int(seed) if seed is not None else -1,
        mode=mode.lower(),
        preserve=preserve.lower(),
        motion=motion.lower(),
        camera_preset=camera_preset.lower(),
        subject_mode=subject_mode.lower(),
        enhance_enabled=bool(enhance_enabled),
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

        yield video_result, status_msg, gr.update(interactive=False), gr.update(interactive=True), format_history_table(), gr.update(choices=get_job_choices())

    yield video_result, status_msg, gr.update(interactive=True), gr.update(interactive=False), format_history_table(), gr.update(choices=get_job_choices())


def on_cancel():
    success = job_manager.cancel()
    if success:
        return "Cancellation requested..."
    return "No active job to cancel."


def on_manual_enhance(current_video, progress=gr.Progress(track_tqdm=False)):
    if not current_video:
        gr.Warning("No video available to enhance.")
        return None, "Error: No video to enhance."

    progress(0.1, desc="Starting manual 2x upscale + 24fps enhancement...")
    res = postprocess_video(
        raw_video_path=current_video,
        source_fps=8.0,
        enable_upscale=True,
        upscale_scale=2,
        enable_interpolate=True,
        target_fps=24.0,
        progress_callback=lambda p, t: progress(p, desc=t),
    )
    if res.success:
        return res.enhanced_video_path, f"Enhancement complete in {res.timings.get('total_postprocess_time_sec', 0)}s"
    return None, f"Enhancement failed: {res.error_message}"


def open_folder(folder_path: str = "outputs"):
    path = Path(folder_path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(str(path))
    else:
        subprocess.run(["xdg-open", str(path)])
    return f"Opened folder: {path}"


def on_play_history(job_id: str):
    if not job_id:
        return None, "Select a job ID first."
    job = db.get_job(job_id)
    if not job:
        return None, f"Job {job_id} not found."
    vid = job.get("enhanced_output") or job.get("raw_output")
    if vid and Path(vid).exists():
        return str(vid), f"Loaded video for job {job_id[:8]}"
    return None, f"Video file not found on disk for job {job_id[:8]}"


def on_duplicate_settings(job_id: str):
    if not job_id:
        return [gr.update()] * 8
    job = db.get_job(job_id)
    if not job:
        return [gr.update()] * 8

    img = job.get("source_image") if job.get("source_image") and Path(job.get("source_image")).exists() else None
    prompt = job.get("user_prompt", "")
    seed = job.get("seed", -1)
    mode = (job.get("mode") or "raw").capitalize()
    preserve = job.get("preserve") or "normal"
    motion = job.get("motion") or "normal"
    cam = job.get("camera_preset") or "static"
    subj = job.get("subject_mode") or "single"

    return [
        gr.update(value=img),
        gr.update(value=prompt),
        gr.update(value=seed),
        gr.update(value=mode),
        gr.update(value=preserve),
        gr.update(value=motion),
        gr.update(value=cam),
        gr.update(value=subj),
    ]


def on_reuse_seed(job_id: str):
    if not job_id:
        return gr.update()
    job = db.get_job(job_id)
    if not job:
        return gr.update()
    return gr.update(value=job.get("seed", -1))


def on_retry_job(job_id: str):
    """Duplicates settings and triggers a new generation job."""
    if not job_id:
        yield None, "Select a job ID to retry.", format_history_table(), gr.update(choices=get_job_choices())
        return
    job = db.get_job(job_id)
    if not job:
        yield None, f"Job {job_id} not found.", format_history_table(), gr.update(choices=get_job_choices())
        return

    # Call on_generate with duplicated settings
    img = job.get("source_image")
    prompt = job.get("user_prompt")
    seed = job.get("seed", -1)
    mode = (job.get("mode") or "raw").capitalize()
    preserve = job.get("preserve") or "normal"
    motion = job.get("motion") or "normal"
    cam = job.get("camera_preset") or "static"
    subj = job.get("subject_mode") or "single"
    enhance = bool(job.get("enhance_enabled", 1))

    for out in on_generate(img, prompt, seed, mode, preserve, motion, cam, subj, enhance):
        yield out[0], out[1], out[4], out[5]


def build_ui() -> gr.Blocks:
    sys_status = get_system_status_summary()

    with gr.Blocks(title="LocalI2V V0.1 — Image to Video") as demo:
        gr.Markdown("# 🎬 LocalI2V V0.1 — Image to Video")
        status_banner = gr.Markdown(value=sys_status["summary_markdown"])

        with gr.Row():
            with gr.Column(scale=1):
                image_input = gr.Image(label="Source Image (PNG, JPG, WEBP)", type="filepath")
                prompt_input = gr.Textbox(
                    label="Motion Prompt",
                    placeholder="Describe character motion (e.g. Character turns head slowly. Camera static.)",
                    lines=3,
                )

                with gr.Row():
                    mode_input = gr.Radio(
                        label="Prompt Mode",
                        choices=["Raw", "Simple", "Cinematic"],
                        value="Raw",
                        info="Raw sends exact prompt without alterations. Simple/Cinematic apply camera & styling.",
                    )
                    seed_input = gr.Number(label="Seed (-1 for random)", value=-1, precision=0)

                with gr.Accordion("Semantic Controls", open=True):
                    with gr.Row():
                        preserve_input = gr.Dropdown(
                            label="Preserve Fidelity",
                            choices=["low", "normal", "high", "maximum"],
                            value="normal",
                            info="Source image preservation vs motion dynamic freedom.",
                        )
                        motion_input = gr.Dropdown(
                            label="Motion Dynamics",
                            choices=["subtle", "normal", "strong"],
                            value="normal",
                            info="Per-frame motion scale & temporal speed.",
                        )

                    with gr.Row():
                        camera_input = gr.Dropdown(
                            label="Camera Preset",
                            choices=["static", "pan_left", "pan_right", "zoom_in"],
                            value="static",
                            visible=False,
                            info="Active in Simple/Cinematic modes only. Ignored in Raw mode.",
                        )
                        subject_input = gr.Dropdown(
                            label="Subject Control (Experimental)",
                            choices=["single", "two_subject"],
                            value="single",
                            visible=False,
                            info="Active in Simple/Cinematic modes only. Ignored in Raw mode.",
                        )

                enhance_checkbox = gr.Checkbox(
                    label="Enhance output (2x Real-ESRGAN Upscale + 24fps RIFE Interpolation)",
                    value=True,
                )

                with gr.Row():
                    generate_btn = gr.Button("Generate Video", variant="primary", interactive=True)
                    cancel_btn = gr.Button("Cancel", variant="stop", interactive=False)

            with gr.Column(scale=1):
                status_box = gr.Textbox(label="Status & Progress", value="Ready", interactive=False)
                video_output = gr.Video(label="Video Output", interactive=False, autoplay=True)

                with gr.Row():
                    enhance_btn = gr.Button("Enhance Current Video", variant="secondary")
                    open_dir_btn = gr.Button("Open Outputs Folder", variant="secondary")

        # Bottom: SQLite Job History
        with gr.Accordion("Job History (Latest 10)", open=True):
            history_table = gr.Dataframe(
                headers=["Job ID", "Created", "Status", "Mode", "Seed", "Prompt", "Raw Video", "Enhanced Video"],
                value=format_history_table(),
                interactive=False,
            )

            with gr.Row():
                job_selector = gr.Dropdown(
                    label="Select Job",
                    choices=get_job_choices(),
                    value=get_job_choices()[0] if get_job_choices() else None,
                )
                play_history_btn = gr.Button("Play Video")
                duplicate_btn = gr.Button("Duplicate Settings")
                reuse_seed_btn = gr.Button("Reuse Seed")
                retry_btn = gr.Button("Retry Job", variant="primary")
                refresh_history_btn = gr.Button("Refresh History")

        # Wire Mode Change events
        mode_input.change(
            fn=on_mode_change,
            inputs=[mode_input],
            outputs=[camera_input, subject_input],
        )

        # Wire Generation & Cancel
        gen_event = generate_btn.click(
            fn=on_generate,
            inputs=[
                image_input,
                prompt_input,
                seed_input,
                mode_input,
                preserve_input,
                motion_input,
                camera_input,
                subject_input,
                enhance_checkbox,
            ],
            outputs=[video_output, status_box, generate_btn, cancel_btn, history_table, job_selector],
        )

        cancel_btn.click(
            fn=on_cancel,
            inputs=[],
            outputs=[status_box],
            cancels=[gen_event],
        )

        enhance_btn.click(
            fn=on_manual_enhance,
            inputs=[video_output],
            outputs=[video_output, status_box],
        )

        open_dir_btn.click(
            fn=open_folder,
            inputs=[],
            outputs=[status_box],
        )

        # History Actions
        play_history_btn.click(
            fn=on_play_history,
            inputs=[job_selector],
            outputs=[video_output, status_box],
        )

        duplicate_btn.click(
            fn=on_duplicate_settings,
            inputs=[job_selector],
            outputs=[
                image_input,
                prompt_input,
                seed_input,
                mode_input,
                preserve_input,
                motion_input,
                camera_input,
                subject_input,
            ],
        )

        reuse_seed_btn.click(
            fn=on_reuse_seed,
            inputs=[job_selector],
            outputs=[seed_input],
        )

        retry_btn.click(
            fn=on_retry_job,
            inputs=[job_selector],
            outputs=[video_output, status_box, history_table, job_selector],
        )

        refresh_history_btn.click(
            fn=lambda: (format_history_table(), gr.update(choices=get_job_choices())),
            inputs=[],
            outputs=[history_table, job_selector],
        )

    return demo


if __name__ == "__main__":
    logger.info("LocalI2V UI started on 127.0.0.1:7860")
    build_ui().launch(server_name="127.0.0.1", server_port=7860, share=False, inbrowser=False)
