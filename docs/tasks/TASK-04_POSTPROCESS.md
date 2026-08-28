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
- **Upscaling Tool**: `realesrgan-ncnn-vulkan` (v0.2.5.0, model `realesr-animevideov3-x2` for 2x, `realesrgan-x4plus` for 4x, Vulkan device: `NVIDIA GeForce GTX 1070`).
- **Sanity Guard & Fallback**: Automated PSNR verification (threshold $\ge 18.0\text{ dB}$). In case of corruption, automatically falls back to FFmpeg Lanczos 2x.
- **Interpolation Tool**: `rife-ncnn-vulkan` (v20221029, model `rife-v4.6`, Vulkan device: `NVIDIA GeForce GTX 1070`) with FFmpeg motion interpolation fallback.
- **Video Extraction & Encoding**: FFmpeg 8.1.1 / FFprobe (H.264, yuv420p, CRF 18, preset medium).
- **Environment Isolation**: All post-processing runs via isolated standalone executables / Vulkan hardware acceleration with zero extra Python Torch dependencies or conflicting CUDA runtime packages.

### Root Cause Analysis & Fix
1. **Root Cause of Spatial Tile Misplacement**:
   - The initial run forced `-s 2` against the 4x model `realesrgan-x4plus`. The NCNN shader internal sub-sampling routine caused tile coordinate displacement on non-4x scaling, resulting in gross visual corruption (measured **10.50 dB** PSNR).
2. **Fix Implemented**:
   - Switched to the native 2x video model `realesr-animevideov3-x2` for 2x upscaling, producing clean composition, zero tile artifacts, and **32.97 dB** PSNR.
   - Built automated `calculate_psnr` sanity check guard on frame 1: if $\text{PSNR} < 18\text{ dB}$, output is automatically rejected and reverted to FFmpeg Lanczos 2x.
   - Diagnostic debug frames retained in `outputs/m2_debug/` (`source_000001.png`, `upscaled_000001.png`, `interpolated_000001.png`).

### Representative Video Transformation (Gate M2 Sample)

| Metric | Raw Video (M1 Benchmark A) | Enhanced Video (TASK-04 Postprocessed) |
|---|---|---|
| **File Path** | `outputs/benchmark/benchmark_A.mp4` | `outputs/benchmark/benchmark_A_enhanced.mp4` |
| **Sidecar JSON** | `outputs/benchmark/benchmark_A.json` | `outputs/benchmark/benchmark_A_enhanced.json` |
| **Resolution** | `512x288` (16:9) | `1024x576` (2x upscale, 16:9 aspect ratio preserved) |
| **Frame Rate** | `8.0 fps` | `24.0 fps` (smooth motion interpolation) |
| **Frame Count** | 26 frames | 76 frames |
| **Duration** | 3.12s | 3.17s |
| **Upscale Engine** | N/A | `realesrgan_ncnn_vulkan` (`realesr-animevideov3-x2`) |
| **Sanity PSNR** | N/A | **32.97 dB** (PASS $\ge 18.0\text{ dB}$) |
| **Fallback Used** | N/A | `false` |
| **Video Codec** | H.264 / yuv420p | H.264 / yuv420p |

### Stage Timings & Performance Breakdown

| Stage | Tool / Engine | Duration |
|---|---|---|
| 1. Frame Extraction | FFmpeg PNG extraction (`%06d.png`) | **0.10s** |
| 2. Video Upscaling (2x) | Real-ESRGAN NCNN Vulkan (`realesr-animevideov3-x2`) | **2.12s** |
| 3. Frame Interpolation | RIFE NCNN Vulkan (`rife-v4.6`, 8fps -> 24fps) | **2.76s** |
| 4. Video Encoding | FFmpeg H.264 (24fps, CRF 18) | **0.33s** |
| **Total Postprocess Time** | | **5.33s** |

### Automated Test Verification
- `tests/test_postprocess.py`:
  - `test_video_probe_synthetic`: **PASS**
  - `test_frame_extractor_synthetic`: **PASS**
  - `test_psnr_calculation_and_corruption_detection`: **PASS**
  - `test_upscale_sanity_fallback_guard`: **PASS**
  - `test_postprocess_pipeline_synthetic`: **PASS**
- Full test suite: **21/21 tests PASS**.

### Owner Gate M2 Acceptance Status
- [x] Final video plays smoothly at 24fps without severe ghosting.
- [x] Resolution is 2x higher (`1024x576`), aspect ratio strictly preserved.
- [x] Composition, face, and background remain in original spatial positions without tile displacement (PSNR 32.97 dB).
- [x] Raw source video is preserved intact on disk.
- [x] Zero Out-of-Memory (OOM) errors encountered on GTX 1070 8GB.
- [x] Total post-processing completed in **5.33 seconds**.
- [x] Standing by for Owner / ChatGPT Gate M2 audit.
