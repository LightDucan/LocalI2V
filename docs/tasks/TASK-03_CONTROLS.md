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
Antigravity records calibrated values, sample outputs and tests.
