from __future__ import annotations

import json
import platform
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.system.gpu_info import get_gpu_info  # noqa: E402


def main() -> int:
    gpu = get_gpu_info()
    ffmpeg_path = shutil.which("ffmpeg")
    git_path = shutil.which("git")

    payload = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "ffmpeg": ffmpeg_path,
        "git": git_path,
        "gpu": gpu,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    errors: list[str] = []

    if sys.version_info[:2] not in {(3, 10), (3, 11)}:
        print("WARN: Python 3.10/3.11 is recommended for this legacy-Pascal stack.")

    if not gpu.get("cuda_available"):
        errors.append("CUDA is not available.")
    else:
        gpu_name = gpu.get("name", "")
        if "GTX 1070" not in gpu_name and "1070" not in gpu_name:
            errors.append(f"GPU name does not contain GTX 1070: {gpu_name}")

        cc = gpu.get("compute_capability", "")
        arch_list = gpu.get("arch_list", [])
        if cc != "6.1" and "sm_61" not in arch_list:
            errors.append(f"Pascal compute capability 6.1 / sm_61 missing (got cc={cc}, arch_list={arch_list})")

        total_vram = float(gpu.get("vram_total_gb", 0))
        if total_vram < 7.0:
            errors.append(f"Total VRAM is less than 7GB ({total_vram} GB).")

        cuda_runtime = str(gpu.get("cuda_runtime", ""))
        if not cuda_runtime.startswith("12.6"):
            errors.append(f"PyTorch CUDA runtime must be 12.6, got {cuda_runtime}")

    if not ffmpeg_path:
        errors.append("ffmpeg executable was not found in PATH.")

    if not git_path:
        errors.append("git executable was not found in PATH.")

    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 1

    print("Environment check passed: all Pascal / LocalI2V prerequisites verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
