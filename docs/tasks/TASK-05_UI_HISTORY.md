# TASK-05 — UI Final + SQLite History

**Maps from Rev.2:** LV-050 through LV-053 and LV-060 through LV-062.
**Gate:** SELF-CHECK; auto-continue to TASK-06.

## Objective
Finish usability and persistence only after generation and quality are proven.

## Work
1. SQLite jobs table; standard-library `sqlite3` only.
2. Save queued/running/done/failed/cancelled state and settings JSON.
3. History shows latest 10 jobs with Play/Open Folder/Retry/Duplicate Settings/Reuse Seed.
4. Retry creates a new job with exact prior settings.
5. Implement final compact Gradio layout from Rev.2; no decorative redesign.
6. Mode selector hides/shows relevant controls.
7. Startup status: GPU, ComfyUI connectivity, selected model availability, output writable, ffmpeg/post tools.
8. Keep localhost-only and analytics disabled.

## Acceptance
- Three jobs persist across restart.
- Retry creates a new job and reuses settings.
- Open Folder works on Windows.
- Mode changes UI controls correctly.
- Startup header reflects real state.
- No extra feature scope.

## Execution Report
Antigravity records DB migration/schema, UI checks, restart test, files changed.
