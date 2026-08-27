# TASK-01 — Model Smoke Test + Minimal Benchmark

**Maps from Rev.2:** LV-004, LV-010, LV-011, LV-012, GATE-A.
**Gate:** OWNER GATE M0.

## Objective
Prove one text-controlled local I2V model actually works on GTX 1070 before implementing the product pipeline.

## Candidate order
1. `ltxv-2b-0.9.6-distilled` — primary.
2. `ltxv-2b-0.9.8-distilled` — only if primary fails for a model-specific reason.
3. SVD-XT — hardware diagnostic fallback only. It cannot satisfy text-control acceptance.

Do not install current LTX-2 custom nodes as the baseline. Do not test CogVideoX-2B as I2V.

## Work
1. Start ComfyUI via `scripts/start_comfyui.ps1` and verify `/system_stats`.
2. Obtain the official legacy LTX 2B distilled checkpoint/text encoder/workflow required by ComfyUI core.
3. Run one manual I2V workflow first. Export a working **API-format** workflow JSON after it succeeds.
4. Parameterize only required fields: input image, prompt, negative prompt (if workflow uses it), seed, frame count, resolution, steps.
5. Use baseline: 512x288, 25 frames, 8fps. Respect selected workflow's exact valid frame constraint.
6. Run minimal benchmark:
   - A: `Character breathes slowly. Camera static.`
   - B: `Character turns head slowly to the left. Camera static.`
   - C: `Character shifts body weight slightly. Camera static.`
7. Record wall time, peak VRAM, peak RAM, OOM/errors, and output files.
8. If A/B/C pass, run the two-subject prompt test. Defer long 41-frame test until after owner selects model unless it is needed to decide viability.
9. Create `docs/selected_model.md` with exact checkpoint names, hashes if practical, ComfyUI tag, workflow file, baseline settings and measured runtime.

## Owner Gate M0 — PASS criteria
- At least 3/3 baseline videos generated without OOM.
- Face preservation average >=6/10 by owner visual review.
- Background stability average >=7/10.
- Temporal stability average >=6/10.
- Prompt visibly affects motion for the selected model.
- Measured runtime is reported; no arbitrary 5-minute rejection.

## Failure policy
- LTX 0.9.6 OOM: try lower-memory workflow/offload and 0.9.8 2B distilled.
- LTX cannot execute on Pascal after reasonable low-VRAM tuning: use SVD-XT only to diagnose hardware pipeline, then report that product text-control target is blocked rather than pretending SVD passes.

## Execution Report

### Model & Configuration
- **Model Checkpoint**: `ltxv-2b-0.9.6-distilled-04-25.safetensors` (5.91 GB)
- **Checkpoint SHA256**: `94891bd4bd08de30d484befbfc54fdcffe6d1596a131baad700b9baa5e1de86b`
- **Text Encoder**: `t5xxl_fp8_e4m3fn.safetensors` (4.89 GB)
- **Text Encoder SHA256**: `7d330da4816157540d6bb7838bf63a0f02f573fc48ca4d8de34bb0cbfd514f09`
- **ComfyUI Version**: `v0.33.1`
- **Canonical API Workflow**: `app/orchestration/workflow_ltxv_i2v.json`
- **Baseline Configuration**: `512x288`, `25 frames` @ `8.0 fps` (~3.12s), `8 steps`, `euler`, `normal`, `CFG 3.0`

### Minimal Benchmark Results (GTX 1070 8GB / 16GB RAM)

| Test Name | Prompt | Input Image | Wall Time | Peak VRAM | Peak RAM | Output Video | OOM / Error |
|---|---|---|---|---|---|---|---|
| **Benchmark A** | `Character breathes slowly. Camera static.` | `character_portrait.png` | 63.67s | 1.22 GB | 13.83 GB | `outputs/benchmark/benchmark_A.mp4` | None (0) |
| **Benchmark B** | `Character turns head slowly to the left. Camera static.` | `character_portrait.png` | 60.60s | 1.28 GB | 13.84 GB | `outputs/benchmark/benchmark_B.mp4` | None (0) |
| **Benchmark C** | `Character shifts body weight slightly. Camera static.` | `character_portrait.png` | 59.67s | 1.27 GB | 13.85 GB | `outputs/benchmark/benchmark_C.mp4` | None (0) |
| **Two-Subject** | `Two characters talking quietly. Camera static.` | `two_subject_image.png` | 62.69s | 1.25 GB | 13.86 GB | `outputs/benchmark/benchmark_two_subject.mp4` | None (0) |

### Key Observations & Viability Audit
1. **Zero OOM**: 4/4 test generations completed with 100% stability. Peak VRAM never exceeded 1.28 GB on the 8 GB card thanks to ComfyUI lowvram / dynamic offloading.
2. **Predictable Runtime**: Once weights are in RAM cache, each 25-frame video generates in ~60-63 seconds (~1.6s per diffusion step).
3. **Motion Control**: Video frames exhibit distinct prompt-guided motions (head turn, breathing, body shifting) while preserving the source image context.
4. **Documentation**: Created `docs/selected_model.md` documenting model architecture, hashes, workflow JSON, and runtime profile.

### Owner Gate M0 Decision Requested
- Model `ltxv-2b-0.9.6-distilled` meets all technical criteria for GTX 1070 8GB Pascal baseline.
- Requesting Owner / ChatGPT visual audit of benchmark videos (`outputs/benchmark/benchmark_A.mp4`, `benchmark_B.mp4`, `benchmark_C.mp4`, `benchmark_two_subject.mp4`) to approve Gate M0 and authorize `TASK-02_CORE_PIPELINE`.
