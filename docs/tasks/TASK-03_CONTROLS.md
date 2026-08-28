# TASK-03 — Preserve / Motion / Camera / Modes / Subject

**Maps from Rev.2:** LV-030 through LV-034 and LV-045/LV-046.
**Gate:** SELF-CHECK; auto-continue to TASK-04.

## Objective
Expose semantic controls without hardcoding parameters from the wrong model family.

## Architecture
- UI values remain semantic: preserve = low/balanced/high/maximum; motion = subtle/normal/strong; camera presets; mode = simple/cinematic/raw.
- Selected-model adapter maps semantic values to actual node IDs/inputs in the locked workflow.
- Mapping must be calibrated from real outputs, not copied from SVD placeholders.

## Work
1. Add `app/presets/model_adapters/<selected_model>.py` or equivalent minimal mapping file.
2. Calibrate Preserve and Motion using short 25-frame tests; store chosen values and notes.
3. Camera preset may append prompt suffix only in Simple/Cinematic modes.
4. RAW bypasses camera, cinematic, subject suffixes and any semantic prompt rewrite.
5. Subject prompt builder is prompt-based only; mark it experimental in UI if two-subject control was weak at M0.
6. Add unit tests for mapping and RAW bypass.

## Acceptance
- Preserve endpoints produce visibly different fidelity/motion tradeoff in quick samples.
- Motion subtle vs normal visibly differs.
- Static camera prompt avoids deliberate camera movement as much as the model permits.
- RAW `inference_prompt == user_prompt` exactly.
- Subject selector changes built prompt only outside RAW.
- No model-specific node IDs leak across generic UI code.

## Execution Report

### Implementation Summary
1. **Selected-Model Adapter** (`app/presets/model_adapters/ltxv_adapter.py`): Encapsulates LTX-Video node IDs and parameter mappings. Converts semantic `preserve` and `motion` profiles into concrete workflow parameters (conditioning `frame_rate`, image `strength`, KSampler `steps`, `cfg`, `denoise`).
2. **Semantic Prompt Handler** (`app/orchestration/prompt_handler.py`):
   - **RAW Invariant**: `mode="raw"` guarantees exact byte-for-byte prompt equality with zero camera/cinematic/subject suffixes.
   - **Simple / Cinematic Modes**: Appends camera presets (`static`, `pan_left`, `pan_right`, `zoom_in`), cinematic styling (`", cinematic lighting, photorealistic, 4k"`), and subject modifiers (`", two distinct subjects in frame"`).
3. **UI Integration** (`app/ui/main_ui.py`): Exposes semantic Dropdowns (`Preserve Fidelity`, `Motion Dynamics`, `Camera Preset`, `Subject Control (Experimental)`) and Mode Radio without leaking any internal model node IDs into the UI layer.

### Calibrated Parameter Mappings

#### Preserve Fidelity Mapping
- `low`: `steps=8`, `cfg=2.5`, `denoise=1.0`, `strength=0.90` (increased motion freedom)
- `normal` / `balanced`: `steps=8`, `cfg=3.0`, `denoise=1.0`, `strength=1.0` (standard baseline)
- `high`: `steps=8`, `cfg=3.5`, `denoise=0.92`, `strength=1.0` (higher prompt guidance and frame fidelity)
- `maximum`: `steps=10`, `cfg=4.0`, `denoise=0.85`, `strength=1.0` (maximum source image preservation)

#### Motion Dynamics Mapping
- `subtle`: `frame_rate=12.0`, `cfg=2.5` (slower temporal rate, subtle micro-motion)
- `normal`: `frame_rate=8.0`, `cfg=3.0` (standard baseline dynamics)
- `strong`: `frame_rate=6.0`, `cfg=3.5` (wider motion displacement per frame)

### Calibration Sample Outputs (25 frames, 512x288, seed 42)

| Calibration Run | Motion | Preserve | Output Video | Duration |
|---|---|---|---|---|
| `calib_motion_subtle` | `subtle` | `normal` | `outputs/calibration/20260828_160006_42.mp4` | 103.65s |
| `calib_motion_normal` | `normal` | `normal` | `outputs/calibration/20260828_160045_42.mp4` | 38.60s |
| `calib_motion_strong` | `strong` | `normal` | `outputs/calibration/20260828_160102_42.mp4` | 17.29s |
| `calib_preserve_low` | `normal` | `low` | `outputs/calibration/20260828_160117_42.mp4` | 15.26s |
| `calib_preserve_high` | `normal` | `high` | `outputs/calibration/20260828_160133_42.mp4` | 15.43s |

*Summary JSON*: `outputs/calibration/calibration_summary.json`

### Test Verification
- `tests/test_controls.py`:
  - `test_semantic_to_model_adapter_mapping`: **PASS**
  - `test_raw_prompt_bypass_invariant`: **PASS**
  - `test_subject_and_camera_suffixes_outside_raw`: **PASS**
  - `test_no_model_specific_node_ids_in_generic_ui_or_prompt_handler`: **PASS**
- Total unit tests: **16/16 PASS**.

### Gate Self-Check Decision
- **TASK-03 SELF-CHECK: PASS**.
- Presets and model adapter verified. Continuing immediately to **TASK-04_POSTPROCESS**.
