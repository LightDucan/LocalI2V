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
    payload = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "ffmpeg": shutil.which("ffmpeg"),
        "git": shutil.which("git"),
        "gpu": gpu,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if sys.version_info[:2] not in {(3, 10), (3, 11)}:
        print("WARN: Python 3.10/3.11 is recommended for this legacy-Pascal stack.")
    if not gpu.get("cuda_available"):
        return 2
    if "sm_61" not in gpu.get("arch_list", []):
        print("WARN: PyTorch wheel does not report sm_61 support; GTX 1070 may fail.")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
