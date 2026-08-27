---
description: Execute the next LocalI2V fast-track task and verify it.
---

1. Read `docs/tasks/STATUS.md` and identify `CURRENT_TASK`.
2. Read that task file completely plus all workspace rules in `.agents/rules/`.
3. Execute the task end-to-end. Do not expand scope.
4. Run every listed verification command/check.
5. Write concrete evidence/results into the task file under `Execution Report`.
6. Update status in `docs/tasks/STATUS.md`.
7. If the next boundary is `SELF-CHECK`, continue to the next task automatically.
8. If the boundary is `OWNER GATE`, stop and report only: what passed, measured numbers, produced files, failures/risks, and the exact decision required from the owner.
