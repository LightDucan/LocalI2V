from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path
import torch

logger = logging.getLogger("locali2v.diagnostics")

ROOT = Path(__file__).resolve().parents[2]


def check_gpu() -> dict:
    if not torch.cuda.is_available():
        return {"status": "FAIL", "message": "CUDA is not available"}
    device_name = torch.cuda.get_device_name(0)
    vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
    cc = torch.cuda.get_device_capability(0)
    return {
        "status": "PASS",
        "device": device_name,
        "vram_gb": vram_gb,
        "compute_capability": f"{cc[0]}.{cc[1]}",
        "message": f"{device_name} ({vram_gb} GB VRAM, CC {cc[0]}.{cc[1]})",
    }


def check_comfyui(url: str = "http://127.0.0.1:8188") -> dict:
    try:
        req = urllib.request.Request(f"{url}/system_stats")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return {"status": "PASS", "message": f"Connected ({url})"}
    except Exception as exc:
        return {"status": "OFFLINE", "message": f"Offline ({url})"}
    return {"status": "OFFLINE", "message": f"Offline ({url})"}


def check_checkpoint() -> dict:
    ckpt_path = ROOT / "comfyui" / "models" / "checkpoints" / "ltxv-2b-0.9.6-distilled-04-25.safetensors"
    if not ckpt_path.exists():
        ckpt_path = ROOT / "models" / "checkpoints" / "ltxv-2b-0.9.6-distilled-04-25.safetensors"
    if ckpt_path.exists() and ckpt_path.stat().st_size > 1024 * 1024 * 100:
        return {"status": "PASS", "message": "LTXV 2B Distilled present"}
    return {"status": "FAIL", "message": "LTXV 2B Checkpoint missing"}


def check_output_dir(output_dir: Path | str = "outputs") -> dict:
    p = Path(output_dir)
    try:
        p.mkdir(parents=True, exist_ok=True)
        test_file = p / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        return {"status": "PASS", "message": "Outputs writable"}
    except Exception as exc:
        return {"status": "FAIL", "message": f"Output dir unwritable: {exc}"}


def check_ffmpeg() -> dict:
    ffmpeg_found = shutil.which("ffmpeg") is not None
    ffprobe_found = shutil.which("ffprobe") is not None
    if ffmpeg_found and ffprobe_found:
        return {"status": "PASS", "message": "FFmpeg & FFprobe available"}
    return {"status": "FAIL", "message": "FFmpeg or FFprobe missing"}


def check_postprocess_tools() -> dict:
    realesrgan = ROOT / "tools" / "realesrgan" / "realesrgan-ncnn-vulkan.exe"
    rife = ROOT / "tools" / "rife" / "rife-ncnn-vulkan.exe"
    has_real = realesrgan.exists()
    has_rife = rife.exists()
    if has_real and has_rife:
        return {"status": "PASS", "message": "Real-ESRGAN & RIFE Vulkan ready"}
    elif has_real:
        return {"status": "PARTIAL", "message": "Real-ESRGAN ready (RIFE fallback)"}
    elif has_rife:
        return {"status": "PARTIAL", "message": "RIFE ready (Lanczos fallback)"}
    return {"status": "FALLBACK", "message": "FFmpeg native fallback"}


def get_system_status_summary() -> dict:
    gpu = check_gpu()
    comfy = check_comfyui()
    ckpt = check_checkpoint()
    out = check_output_dir()
    ff = check_ffmpeg()
    tools = check_postprocess_tools()

    summary_text = (
        f"**GPU:** {gpu['message']} | "
        f"**ComfyUI:** {comfy['message']} | "
        f"**Model:** {ckpt['message']} | "
        f"**Post-Process:** {tools['message']}"
    )

    return {
        "gpu": gpu,
        "comfyui": comfy,
        "checkpoint": ckpt,
        "output_dir": out,
        "ffmpeg": ff,
        "postprocess_tools": tools,
        "summary_markdown": summary_text,
    }
