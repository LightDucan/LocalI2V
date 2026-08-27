$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$python = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Run scripts/bootstrap_windows.ps1 first." }
if (-not (Test-Path comfyui\main.py)) { throw "ComfyUI is not installed." }

# Conservative Pascal defaults: avoid xformers-only kernels and keep memory pressure low.
& $python comfyui\main.py --listen 127.0.0.1 --port 8188 --disable-xformers --use-split-cross-attention --lowvram
