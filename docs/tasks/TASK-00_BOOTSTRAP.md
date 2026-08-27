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
Antigravity fills this section with commands, versions, measured values, files changed, and any warnings.
