# Selected Model

Status: CANDIDATE_PROPOSED (Awaiting Owner Gate M0 review)

- **Model/checkpoint**: `ltxv-2b-0.9.6-distilled-04-25.safetensors`
- **Checkpoint SHA256**: `94891bd4bd08de30d484befbfc54fdcffe6d1596a131baad700b9baa5e1de86b`
- **Text encoder**: `t5xxl_fp8_e4m3fn.safetensors` (`7d330da4816157540d6bb7838bf63a0f02f573fc48ca4d8de34bb0cbfd514f09`)
- **VAE**: Embedded within LTX-Video checkpoint
- **ComfyUI tag**: `v0.33.1`
- **API workflow file**: `app/orchestration/workflow_ltxv_i2v.json`
- **Baseline resolution**: `512x288` (16:9)
- **Baseline frames/fps**: `25 frames` @ `8.0 fps` (3.12s video duration)
- **Steps/sampler/scheduler**: `8 steps`, `euler`, `normal`, `CFG 3.0`
- **25-frame runtime**: `~59.7s - 63.7s` (warm inference)
- **Peak VRAM**: `1.28 GB`
- **Peak RAM**: `13.86 GB`
- **Notes**: Successfully passes 4/4 benchmark tests (A, B, C, two-subject) on Pascal GTX 1070 8GB with zero OOM. Prompt text noticeably controls character motion. Video outputs generated and verified at `outputs/benchmark/`.
