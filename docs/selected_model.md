# Selected Model

**Status**: `SELECTED_FOR_V0.1`  
**Owner Gate M0**: `PASS`

### Audit Scores & Decision
- **Face Preservation AVG**: 8.2/10 (PASS)
- **Background Stability AVG**: 8.8/10 (PASS)
- **Temporal Stability AVG**: 8.5/10 (PASS)
- **Zero OOM**: PASS (Peak VRAM: 1.28 GB on 8 GB GTX 1070)
- **Runtime**: ~60-64s per 25-frame clip (PASS)
- **Text-conditioned Motion**: PASS (motion exists and is prompt-guided)

### Model Specifications
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

### Known Risks & Operational Guidance
1. **Motion prompt adherence**: Weak for subtle body-motion instructions; motion strength / prompt calibration will be addressed in TASK-03.
2. **Two-subject deformation**: Two-subject benchmark shows identity/background deformation; deferred to later Subject Control improvements.
3. **Execution Policy**: Do not optimize model quality during TASK-02; prioritize fastest path to working end-to-end product.
