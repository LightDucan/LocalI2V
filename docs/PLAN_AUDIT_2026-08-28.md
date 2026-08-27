# LocalI2V Plan Audit — 2026-08-28

## Verdict
The product direction is viable to prototype, but Rev.2 cannot be executed literally on GTX 1070 in 2026. The fastest safe route is to preserve the product scope while correcting the model/runtime assumptions and reducing manual gates.

## P0 corrections (must apply)

### A1 — LTX generation mismatch
Rev.2 says to install the LTX-Video node/extension. The current Lightricks ComfyUI-LTXVideo extension is for LTX-2 and advertises 32GB+ VRAM. That is not the target for GTX 1070 8GB.

**Correction:** use ComfyUI core LTXV support and legacy LTX-Video 2B first. Candidate order:
1. `ltxv-2b-0.9.6-distilled` (primary; known I2V workflow)
2. `ltxv-2b-0.9.8-distilled` (secondary)
3. SVD-XT only as hardware fallback, not feature-equivalent.

### A2 — Pascal runtime must be pinned
GTX 1070 is Pascal/sm_61. Current default CUDA 13.x PyTorch paths do not support Pascal. PyTorch 2.13 + CUDA 12.6 is the current stable legacy-compatible baseline as of this audit.

**Correction:** Python 3.10 + torch 2.13.0 / torchvision 0.28.0 / cu126. Never let an unpinned ComfyUI install silently replace this with CUDA 13.x.

### A3 — CogVideoX-2B is not an I2V candidate
The official CogVideoX I2V model is the 5B-I2V line. 2B is not the image-to-video model required by this product.

**Correction:** delete CogVideoX-2B from Gate-A candidates.

### A4 — SVD-XT has no text control
SVD-XT can animate an image, but its model card states that it cannot be controlled through text.

**Correction:** it may validate that the hardware can render I2V, but it cannot pass the product's motion-prompt/subject-control gate.

### A5 — Invalid LTX frame counts
Rev.2 uses 24 and 48 frames. ComfyUI's LTXV I2V node exposes frame length starting at 9 with a step of 8.

**Correction:** baseline 25 frames (~3.1s at 8fps); long test 41 frames (~5.1s). Workflow is source of truth if the selected legacy checkpoint imposes tighter constraints.

### A6 — Model-specific presets are defined too early
`motion_bucket_id` is SVD-style; the placeholder `image_strength/noise_aug_strength` mapping is not guaranteed for LTX.

**Correction:** UI exposes semantic presets (`Preserve`, `Motion`, `Camera`), while a selected-model adapter maps them to actual workflow node inputs after Gate M0.

### A7 — `sqlite3` must not be installed by pip
It is a Python standard-library module.

**Correction:** remove `sqlite3` from requirements.

### A8 — 7.5GB free VRAM gate is too strict for an 8GB display GPU
Windows/display allocation can make this fail on an otherwise usable GTX 1070.

**Correction:** require total VRAM >=7GB and report free VRAM. Treat <6GB free as a warning/action item (close GPU apps), not automatic hardware failure.

### A9 — fixed 5-minute timeout is premature
Pascal is slow for modern video inference. A fixed timeout can misclassify a working model as broken.

**Correction:** benchmark first; set job timeout from observed runtime (recommended starting rule: max(15 min, 3x measured 25-frame baseline)).

### A10 — privacy gate must distinguish setup from inference
Model/dependency downloads require network; release inference must not.

**Correction:** allow network during bootstrap. Disable Gradio analytics/share and runtime update/download helpers. Run release generation with network disconnected or monitored.

## Process compression
Original Rev.2 has many owner pauses. For fastest completion, reduce them to four owner gates:
- **M0 Model Gate** — real video + benchmark viability.
- **M1 Core Gate** — image -> prompt -> ComfyUI -> MP4 + metadata + cancel/error.
- **M2 Quality Gate** — upscale/interpolate quality and runtime.
- **M3 Release Gate** — fresh-start E2E + privacy.

Everything else is Antigravity self-check and auto-continue.
