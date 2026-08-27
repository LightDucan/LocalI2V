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
Antigravity fills benchmark table, paths to videos, hardware metrics, errors/fixes, and exact owner decision requested.
