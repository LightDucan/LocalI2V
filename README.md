# LocalI2V V0.1 — Antigravity Fast-Track Bootstrap

This repository is the audited bootstrap for the original `LocalI2V_ProjectPlan` targeting GTX 1070 8GB.

## Start in Google Antigravity
1. Open this folder as the workspace/repository.
2. Antigravity should pick up `.agents/rules/` workspace rules.
3. Run the workspace workflow `/run-next-task` if available, or tell the agent: `Read docs/tasks/STATUS.md and execute CURRENT_TASK to completion.`
4. Antigravity may auto-continue through SELF-CHECK boundaries. It must stop at OWNER GATE M0/M1/M2/M3.

## Manual first command (Windows)
```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_windows.ps1
```

## Important hardware note
GTX 1070 is Pascal/sm_61. Do not use the default CUDA 13.x PyTorch wheel. The bootstrap pins PyTorch 2.13.0 on CUDA 12.6.

## Plan documents
- Audit: `docs/PLAN_AUDIT_2026-08-28.md`
- Fast track: `docs/FAST_TRACK_PLAN.md`
- Current task: `docs/tasks/STATUS.md`
- Original source plan: `docs/reference/LocalI2V_ProjectPlan_Rev2.md`
