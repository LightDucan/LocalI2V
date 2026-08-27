# TASK-06 — Fresh-Start Release Verification

**Maps from Rev.2:** GATE-C plus final privacy/reproducibility checks.
**Gate:** OWNER GATE M3.

## Objective
Prove V0.1 works from a clean start and generation does not depend on outbound network calls.

## Work
1. Add one command/script to start required local services in correct order or document two explicit launch commands.
2. Run all unit tests.
3. Fresh-start E2E from a new terminal session.
4. Test: image preview, generate, progress, output preview, postprocess, metadata, history, retry, RAW invariant, cancel, invalid image.
5. Restart app and confirm history persists.
6. Privacy test: after all dependencies/models are already local, disable internet or monitor outbound traffic while generating. No required outbound request is allowed.
7. Write `docs/RELEASE_V0.1.md` with exact versions, selected model, startup commands, known limitations and benchmark timing on GTX 1070.

## Owner Gate M3
Provide a compact release report:
- PASS/FAIL for each E2E item.
- Exact output sample paths.
- Selected model + hashes/version info.
- 25-frame baseline generation time and postprocess time.
- Peak VRAM/RAM observed.
- Privacy result.
- Remaining known limitations.

V0.1 is released only after owner sign-off.

## Execution Report
Antigravity fills final test evidence and release candidate summary.
