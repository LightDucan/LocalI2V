# LocalI2V V0.1 — Fast Track

## Critical path
`TASK-00 Bootstrap` -> `TASK-01 Model Gate` -> OWNER M0 -> `TASK-02 Core` -> OWNER M1 -> `TASK-03 Controls` -> `TASK-04 Post` -> OWNER M2 -> `TASK-05 UI/History` -> `TASK-06 Release` -> OWNER M3

## Goal
Get a usable local I2V path working before spending time on UI polish or persistence.

## Deliberately deferred until core works
- Fancy UI styling
- Full 5-test benchmark matrix across multiple models
- Face restore tuning
- History thumbnails/polish
- General multi-model architecture beyond one selected-model adapter

## Baseline decisions
- OS target: Windows 10/11 x64.
- Python: 3.10 x64.
- PyTorch: 2.13.0 + cu126 (Pascal-compatible baseline).
- ComfyUI: pinned release tag, initially v0.33.1; never auto-follow `master` during V0.1.
- Primary model: LTX-Video 2B 0.9.6 distilled I2V.
- Generation baseline: 512x288, 25 frames, 8fps, static camera, lowest stable step count for distilled workflow.
- Server binding: localhost only.
