# TASK-00 — Bootstrap + Compatibility Probe

**Maps from Rev.2:** LV-001, LV-002, LV-003, LV-005 shell, LV-006.
**Gate:** SELF-CHECK. Auto-continue to TASK-01 if pass.

## Objective
Create a reproducible Pascal-compatible local environment and prove the shell/tooling works. No model download is required to mark this task done.

## Work
1. Run `scripts/bootstrap_windows.ps1`.
2. Keep PyTorch pinned to 2.13.0/cu126; ensure ComfyUI installation cannot replace it with CUDA 13.x.
3. Run `scripts/check_env.py` and capture GPU name, total/free VRAM, compute capability, `arch_list`, Python, ffmpeg, git.
4. If ffmpeg is missing, install it locally/system-wide and rerun check.
5. Run UI shell with `scripts/start_app.ps1`; verify localhost UI opens and writes `history/app.log`.
6. Confirm directories are writable.
7. Check Windows pagefile status; with 16GB RAM, ensure a system-managed pagefile or >=24GB configured virtual memory and sufficient disk space.

## Acceptance
- CUDA available.
- GPU name contains `GTX 1070`.
- Compute capability is 6.1 and/or `sm_61` is present in torch arch list.
- Total VRAM >=7GB. Free VRAM is recorded; <6GB triggers a warning, not automatic fail.
- Torch runtime reports CUDA 12.6 build path, not CUDA 13.x.
- ComfyUI source exists at pinned tag.
- Gradio shell opens only on 127.0.0.1 and logs locally.
- ffmpeg command is available.

## Execution Report

### Environment Metrics
- **Python**: 3.10.11 (`.venv\Scripts\python.exe`)
- **Platform**: Windows-10-10.0.26200-SP0
- **Git**: 2.55.0.windows.5 (`C:\Program Files\Git\cmd\git.EXE`)
- **FFmpeg**: 8.1.1 Essentials (`C:\Users\PC\AppData\Local\Microsoft\WinGet\Links\ffmpeg.EXE`)
- **GPU**: NVIDIA GeForce GTX 1070 (Compute Capability: 6.1 / `sm_61`)
- **VRAM**: 8.00 GB total, 7.05 GB free
- **PyTorch**: 2.13.0+cu126 (CUDA 12.6 runtime)
- **TorchVision**: 0.28.0+cu126
- **TorchAudio**: 2.11.0+cu126
- **Supported Architectures**: `sm_50`, `sm_60`, `sm_61`, `sm_70`, `sm_75`, `sm_80`, `sm_86`, `sm_90`
- **System Memory**: 15.84 GB physical RAM, 32.84 GB virtual memory (17.00 GB pagefile, exceeding >=24GB target)
- **Disk Headroom**: C: 533.94 GB free, D: 416.76 GB free

### Verification Summary
1. `scripts/bootstrap_windows.ps1` completed successfully with pinned PyTorch 2.13.0 cu126.
2. `scripts/check_env.py` probe passed all acceptance checks.
3. ComfyUI source cloned and pinned to release tag `v0.33.1`.
4. Gradio UI shell tested at `http://127.0.0.1:7860/` with `GRADIO_ANALYTICS_ENABLED=False`, successfully verified logging to `history/app.log`.
5. Directory writability verified for `history/`, `outputs/`, `models/`, `.cache/`, `comfyui/`.
6. Unit tests in `tests/test_env.py` passing (3/3).

### Gate Status
- **Self-Check**: PASS
- **Next Task**: TASK-01_MODEL_GATE (READY)
