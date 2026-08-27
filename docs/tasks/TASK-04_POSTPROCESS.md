# TASK-04 — Post-Processing Quality Pipeline

**Maps from Rev.2:** LV-040 through LV-044.
**Gate:** OWNER GATE M2.

## Objective
Improve output resolution and smoothness without destabilizing the inference Python environment.

## Fast implementation preference
Prefer isolated executable tools where practical:
- FFmpeg/ffprobe for extraction/encoding.
- `realesrgan-ncnn-vulkan` for upscale if Python Real-ESRGAN dependency conflicts or VRAM pressure appear.
- `rife-ncnn-vulkan` for interpolation.

Python wrappers may call these tools; avoid pulling a second conflicting torch stack into the core env just for post-processing.

## Work
1. FFmpeg probe/extract/encode wrappers with subprocess error capture.
2. Upscale raw output to target up to 1080p; choose 2x/4x based on source dimensions so aspect ratio is preserved.
3. Interpolate source fps to 24fps.
4. Face restore remains optional and is skipped if it adds dependency/runtime risk before M2.
5. Orchestrate Generate -> Upscale -> optional Face Restore -> Interpolate -> Encode.
6. Log each stage duration and errors; keep raw source video.

## Owner Gate M2
Using one M1 output:
- Final video plays correctly.
- Resolution is meaningfully higher; no severe ringing/face corruption.
- 24fps is visibly smoother; no severe ghosting.
- No OOM.
- Total stage timings are reported. The old fixed <=5 minute target is informational, not a blocker until owner sees quality/speed tradeoff.

## Execution Report
Antigravity records tool versions, before/after video info, timings, output paths and owner decision request.
