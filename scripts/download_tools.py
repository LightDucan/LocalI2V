from __future__ import annotations

import io
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"


def download_realesrgan():
    target_dir = TOOLS_DIR / "realesrgan"
    target_exe = target_dir / "realesrgan-ncnn-vulkan.exe"
    if target_exe.exists():
        print("Real-ESRGAN NCNN Vulkan is already installed.")
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    url = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip"
    print(f"Downloading Real-ESRGAN from {url}...")
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        z = zipfile.ZipFile(io.BytesIO(resp.read()))
        z.extractall(target_dir)
    print("Real-ESRGAN installed to tools/realesrgan")


def download_rife():
    target_dir = TOOLS_DIR / "rife"
    target_exe = target_dir / "rife-ncnn-vulkan.exe"
    if target_exe.exists():
        print("RIFE NCNN Vulkan is already installed.")
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    url = "https://github.com/nihui/rife-ncnn-vulkan/releases/download/20221029/rife-ncnn-vulkan-20221029-windows.zip"
    print(f"Downloading RIFE from {url}...")
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        z = zipfile.ZipFile(io.BytesIO(resp.read()))
        z.extractall(target_dir)

    # Flatten if nested
    nested = target_dir / "rife-ncnn-vulkan-20221029-windows"
    if nested.exists():
        for item in nested.iterdir():
            dest = target_dir / item.name
            if not dest.exists():
                item.rename(dest)
        try:
            nested.rmdir()
        except Exception:
            pass
    print("RIFE installed to tools/rife")


def main():
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    download_realesrgan()
    download_rife()
    print("Post-processing tools download complete.")


if __name__ == "__main__":
    main()
