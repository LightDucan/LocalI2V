<#
.SYNOPSIS
    LocalI2V V0.1 — One-Click Local Startup Script for Windows
.DESCRIPTION
    Validates environment, launches ComfyUI local backend on 127.0.0.1:8188,
    waits for health check, and launches LocalI2V Gradio UI on 127.0.0.1:7860.
#>

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent $PSScriptRoot
Set-Location $ROOT

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "🎬 LocalI2V V0.1 — Image to Video Startup" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Check Virtual Environment
$PYTHON = Join-Path $ROOT ".venv\Scripts\python.exe"
if (-not (Test-Path $PYTHON)) {
    Write-Error "Virtual environment not found at .venv. Please run scripts/bootstrap_windows.ps1 first."
    exit 1
}

# 2. Check Environment
Write-Host "[1/4] Checking Python and GPU environment..." -ForegroundColor Yellow
& $PYTHON scripts/check_env.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Environment check failed. Please verify hardware and dependencies."
    exit 1
}

# 3. Check / Start ComfyUI
Write-Host "[2/4] Checking ComfyUI backend on 127.0.0.1:8188..." -ForegroundColor Yellow
$comfyReady = $false
try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8188/system_stats" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
    if ($resp.StatusCode -eq 200) {
        $comfyReady = $true
        Write-Host "  -> Existing ComfyUI process detected and healthy." -ForegroundColor Green
    }
} catch {}

$comfyProc = $null
if (-not $comfyReady) {
    Write-Host "  -> Starting local ComfyUI backend..." -ForegroundColor Yellow
    $comfyScript = Join-Path $ROOT "comfyui\main.py"
    $comfyProc = Start-Process -FilePath $PYTHON -ArgumentList "$comfyScript --listen 127.0.0.1 --port 8188 --lowvram --fp8_e4m3fn-text-enc --fast" -PassThru -NoNewWindow

    # Poll until ready
    $retries = 30
    while ($retries -gt 0) {
        Start-Sleep -Seconds 1
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8188/system_stats" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
            if ($resp.StatusCode -eq 200) {
                $comfyReady = $true
                Write-Host "  -> ComfyUI backend is online and ready!" -ForegroundColor Green
                break
            }
        } catch {}
        $retries--
    }

    if (-not $comfyReady) {
        Write-Error "ComfyUI failed to start within timeout."
        if ($comfyProc) { Stop-Process -Id $comfyProc.Id -Force -ErrorAction SilentlyContinue }
        exit 1
    }
}

# 4. Start LocalI2V Gradio UI
Write-Host "[3/4] Launching LocalI2V UI on http://127.0.0.1:7860..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop LocalI2V." -ForegroundColor Gray
Write-Host "==================================================" -ForegroundColor Cyan

try {
    $env:GRADIO_ANALYTICS_ENABLED = "False"
    & $PYTHON app/ui/main_ui.py
} finally {
    Write-Host "`nStopping LocalI2V..." -ForegroundColor Yellow
    if ($comfyProc -and -not $comfyProc.HasExited) {
        Write-Host "Terminating background ComfyUI process..." -ForegroundColor Yellow
        Stop-Process -Id $comfyProc.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "LocalI2V stopped cleanly." -ForegroundColor Green
}
