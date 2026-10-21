# Evaluation slice, 2026-10-21

**Status: plan and harness ready, no model run yet.** This file will hold the results of the
evaluation slice ranked ninth in the [kit refresh audit](2026-10-kit-refresh-audit.md). Until then it
records where the work stands.

## Where it stands

- **Base (`A9`).** The worktree was cut from `main` at `fbc5a8f`, 49 commits behind
  `origin/developer`. It was reset to `origin/developer` at `66b16e1`, which carries PRs #91, #92, #94
  and #95, before anything was read.
- **Plan.** Scenarios, rubric, run counts, cost estimate and decision rules are in
  [`evals/rank9/PLAN.md`](../../evals/rank9/PLAN.md), committed before any run: 413 headless runs,
  estimated at about $125 with a hard stop at $200.
- **Harness.** [`evals/rank9/`](../../evals/rank9/README.md). Its self-test, which checks every
  fixture, condition and grader without calling a model, passes with no failures.
- **Blocker.** A headless child run cannot authenticate on this machine. The probe returned "Failed
  to authenticate: OAuth session expired and could not be refreshed". The desktop app manages its own
  sign-in, and the CLI's stored session has expired. Copying credentials or pointing the child at the
  host's session would breach the brief, so nothing was run.
