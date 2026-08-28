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

### Implementation Summary
1. **SQLite Persistence Engine** (`app/history/database.py`):
   - Implemented using Python standard-library `sqlite3` only (zero ORM overhead).
   - Table `jobs` records `job_id`, `created_at`, `updated_at`, `status` (`QUEUED`, `RUNNING`, `DONE`, `FAILED`, `CANCELLED`), `source_image`, `raw_output`, `enhanced_output`, `user_prompt`, `inference_prompt`, `seed`, `mode`, `preserve`, `motion`, `camera_preset`, `subject_mode`, `enhance_enabled`, `settings_json`, `error_message`.
   - Indexed on `created_at DESC` and `job_id`.
2. **Integrated Post-Processing & Job Manager** (`app/jobs/job_manager.py`):
   - Seamlessly orchestrates Base Generation (`0.0 -> 0.70`) followed by 2x Upscale + 24fps RIFE Interpolation (`0.70 -> 1.0`).
   - Automatically records both raw output path and enhanced output path in SQLite database.
3. **Compact Gradio UI** (`app/ui/main_ui.py`):
   - **Startup Diagnostic Banner**: Real live status check for GPU (GTX 1070 VRAM), ComfyUI connection, LTXV checkpoint, output directory write permissions, FFmpeg/FFprobe, and Real-ESRGAN/RIFE Vulkan tools.
   - **Dynamic Mode Logic**: RAW mode hides camera and subject prompt controls to protect the byte-for-byte prompt invariant. Simple/Cinematic modes reveal camera presets and subject controls.
   - **Job History Table (Latest 10)**: Displays recent jobs with `Play Video`, `Duplicate Settings`, `Reuse Seed`, `Retry Job` (creates a new distinct job), `Open Outputs Folder` (native Windows `os.startfile`), and `Refresh History`.

### Test Verification
- `tests/test_history.py`:
  - `test_sqlite_persistence_across_reopen`: **PASS** (3 jobs verified across cold database reload)
  - `test_retry_creates_distinct_job`: **PASS** (new UUID created without mutating prior history)
  - `test_mode_ui_logic`: **PASS** (RAW hides camera/subject, Simple/Cinematic reveal controls)
  - `test_diagnostics_real_checks`: **PASS** (accurate real machine hardware & tool checks)
  - `test_latest_10_ordering`: **PASS** (15 jobs inserted -> exact 10 newest returned in order)
- Total test suite: **26/26 PASS** across all modules.

### Gate Self-Check Decision
- **TASK-05 SELF-CHECK: PASS**.
- All acceptance criteria satisfied. Continuing immediately to **TASK-06_RELEASE**.
