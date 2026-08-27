$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$python = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "Run scripts/bootstrap_windows.ps1 first." }
$env:GRADIO_ANALYTICS_ENABLED = "False"
& $python app\ui\main_ui.py
