# TASK-02 — Core I2V Pipeline

**Maps from Rev.2:** LV-020 through LV-028.
**Gate:** OWNER GATE M1.
**Prerequisite:** M0 passed and `docs/selected_model.md` exists.

## Objective
End-to-end local pipeline: image -> exact prompt handling -> ComfyUI API -> progress/cancel -> MP4 + metadata, with clear errors and no app crash.

## Work order
1. `image_handler.py`: validate PNG/JPG/WEBP; normalize safe temp input.
2. `prompt_handler.py`: implement Raw first; unit test byte-for-byte invariant.
3. `comfyui_client.py`: `/prompt`, `/history`, `/view`, `/system_stats`, interrupt/cancel; add WebSocket only after polling works.
4. Use the exported API workflow from TASK-01 as a template. Do not build a generalized graph generator.
5. `job_manager.py`: one active job is enough for V0.1 core; preserve cancel/status interface.
6. Seed injection + metadata.
7. Output saver to `outputs/YYYYMMDD_HHMMSS_seed.mp4` + same-name `.json`.
8. Progress: wire ComfyUI websocket events; gracefully fall back to coarse polling if event mapping changes.
9. Central error mapping: connection, OOM, missing model, bad image, timeout, missing output.
10. Timeout must be derived from M0 baseline: default `max(15 minutes, 3 * baseline_25_frame_runtime)` and configurable.
11. Wire the existing Gradio shell only enough to run E2E.

## Acceptance / Owner Gate M1
Fresh app start:
- Drop image -> preview.
- Enter prompt -> generate.
- Progress changes while running.
- Video appears in UI and on disk.
- Sidecar metadata exists and includes selected model, seed, exact user prompt/inference prompt, frame count, resolution, steps, timings.
- Cancel clears active work without crashing app.
- Invalid image produces readable error.
- ComfyUI offline produces readable error.
- RAW unit test proves exact prompt identity.
- Runtime remains localhost-only.

## Execution Report
Antigravity fills test commands/results, E2E output paths, timing, known limitations, and owner decision request.
