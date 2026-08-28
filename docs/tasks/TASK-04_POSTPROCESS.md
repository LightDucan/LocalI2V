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

### Toolchain & Configuration
- **Upscaling Tool**: `realesrgan-ncnn-vulkan` (v0.2.5.0, model `realesrgan-x4plus`, Vulkan device: `NVIDIA GeForce GTX 1070`) with FFmpeg Lanczos fallback.
- **Interpolation Tool**: `rife-ncnn-vulkan` (v20221029, model `rife-v4.6`, Vulkan device: `NVIDIA GeForce GTX 1070`) with FFmpeg motion interpolation fallback.
- **Video Extraction & Encoding**: FFmpeg 8.1.1 / FFprobe (H.264, yuv420p, CRF 18, preset medium).
- **Environment Isolation**: All post-processing runs via isolated standalone executables / Vulkan hardware acceleration with zero extra Python Torch dependencies or conflicting CUDA runtime packages.

### Representative Video Transformation (Gate M2 Sample)

| Metric | Raw Video (M1 Benchmark A) | Enhanced Video (TASK-04 Postprocessed) |
|---|---|---|
| **File Path** | `outputs/benchmark/benchmark_A.mp4` | `outputs/benchmark/benchmark_A_enhanced.mp4` |
| **Sidecar JSON** | `outputs/benchmark/benchmark_A.json` | `outputs/benchmark/benchmark_A_enhanced.json` |
| **Resolution** | `512x288` (16:9) | `1024x576` (2x upscale, 16:9 aspect ratio preserved) |
| **Frame Rate** | `8.0 fps` | `24.0 fps` (smooth motion interpolation) |
| **Frame Count** | 26 frames | 76 frames |
| **Duration** | 3.12s | 3.17s |
| **Video Codec** | H.264 / yuv420p | H.264 / yuv420p |

### Stage Timings & Performance Breakdown

| Stage | Tool / Engine | Duration |
|---|---|---|
| 1. Frame Extraction | FFmpeg PNG extraction (`%06d.png`) | **0.08s** |
| 2. Video Upscaling (2x) | Real-ESRGAN NCNN Vulkan (`realesrgan-x4plus`) | **42.09s** |
| 3. Frame Interpolation | RIFE NCNN Vulkan (`rife-v4.6`, 8fps -> 24fps) | **2.58s** |
| 4. Video Encoding | FFmpeg H.264 (24fps, CRF 18) | **0.38s** |
| **Total Postprocess Time** | | **45.16s** |

### Automated Test Verification
- `tests/test_postprocess.py`:
  - `test_video_probe`: **PASS**
  - `test_frame_extractor`: **PASS**
  - `test_postprocess_pipeline_execution`: **PASS**
- Full test suite: **19/19 tests PASS**.

### Owner Gate M2 Acceptance Status
- [x] Final video plays smoothly at 24fps without severe ghosting.
- [x] Resolution is 2x higher (`1024x576`), aspect ratio strictly preserved.
- [x] Raw source video is preserved intact on disk.
- [x] Zero Out-of-Memory (OOM) errors encountered on GTX 1070 8GB.
- [x] Total post-processing completed in ~45 seconds (well within the informational 5-minute budget).
- [x] Standing by for Owner / ChatGPT Gate M2 audit.
