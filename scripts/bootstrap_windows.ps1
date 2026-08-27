$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
  throw "Python Launcher (py.exe) not found. Install Python 3.10 x64 first."
}

$py310 = & py -3.10 -c "import sys; print(sys.executable)" 2>$null
if (-not $py310) {
  throw "Python 3.10 x64 not found. Install Python 3.10, then rerun."
}

if (-not (Test-Path .venv)) {
  & py -3.10 -m venv .venv
}

$python = Join-Path $PWD ".venv\Scripts\python.exe"
& $python -m pip install --upgrade pip setuptools wheel

# GTX 1070 = Pascal/sm_61. CUDA 13.x builds do not support Pascal.
& $python -m pip install torch==2.13.0 torchvision==0.28.0 torchaudio --extra-index-url https://download.pytorch.org/whl/cu126
& $python -m pip install -r requirements\app.txt

if (-not (Test-Path comfyui\main.py)) {
  if (Test-Path comfyui) { Remove-Item -Recurse -Force comfyui }
  git clone --depth 1 --branch v0.33.1 https://github.com/Comfy-Org/ComfyUI.git comfyui
}

New-Item -ItemType Directory -Force .cache | Out-Null
$filtered = ".cache\comfyui-requirements-no-torch.txt"
Get-Content comfyui\requirements.txt |
  Where-Object { $_ -notmatch '^\s*(torch|torchvision|torchaudio)\s*([<>=!~].*)?$' } |
  Set-Content $filtered
& $python -m pip install -r $filtered --extra-index-url https://download.pytorch.org/whl/cu126

& $python scripts\check_env.py
Write-Host "Bootstrap complete. Next: execute docs/tasks/TASK-01_MODEL_GATE.md in Antigravity."
