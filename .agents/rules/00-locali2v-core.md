# LocalI2V Always-On Project Rules

## Objective
Ship a local-only Image-to-Video V0.1 as quickly as possible on the target PC.

## Scope
- Input: PNG/JPG/WEBP image + motion prompt.
- Output: local MP4 + JSON metadata.
- Core controls: Preserve, Motion, Camera, duration, seed, Simple/Cinematic/Raw.
- Post-process: upscale and interpolation; face restore optional.
- Local queue/history/retry.

## Operating policy
1. Read `docs/tasks/STATUS.md`; execute only the current task packet unless it explicitly allows continuation.
2. Make implementation choices autonomously when they are reversible and low risk. Record them in the task report.
3. Do not create extra architecture, abstractions, services, cloud components, accounts, telemetry, or feature scope.
4. Keep localhost bindings only: `127.0.0.1`. Never enable Gradio share links.
5. Setup may access the internet for dependency/model downloads. Generation/runtime must not require outbound calls.
6. Set `GRADIO_ANALYTICS_ENABLED=False` for app runtime.
7. RAW mode invariant: inference prompt must equal user prompt byte-for-byte; no camera/cinematic/subject suffix.
8. A task is done only when its acceptance checks pass and evidence is written to its report section.
9. Continue through SELF-CHECK gates automatically. Stop and report at OWNER GATE only.
10. Prefer modifying the smallest number of files that cleanly solves the current task.

## Source plan
The original Rev.2 plan is preserved at `docs/reference/LocalI2V_ProjectPlan_Rev2.md`. The fast-track task files supersede it where the audit documents a correction.
