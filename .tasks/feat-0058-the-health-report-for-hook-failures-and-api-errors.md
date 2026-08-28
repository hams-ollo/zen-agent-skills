---
id: feat-0058
title: Report what failed during a run, since hook failures and retried API errors currently reach nobody
type: feat
status: open
priority: P2
parent: "ROADMAP Epic E #7b: reporting"
depends_on: [feat-0054]
spec: docs/spec/agent-observatory.md
scenarios: [S-016]
touched_files:
  - scripts/
  - tests/
  - docs/spec/agent-observatory.md
created: 2026-08-28
---

## Problem

This kit runs hooks inside real sessions, and a hook that fails does so without blocking, by design.
The hooks module contract in [`.agents/hooks/README.md`](../.agents/hooks/README.md) requires a
reminder to exit cleanly whatever happens, which is correct and means a broken hook is invisible: it
stops contributing and nothing says so.

Retried API errors have the same shape. The retry succeeds, the session continues, and the fact that
it took four attempts reaches nobody.

`S-016` in [`docs/spec/agent-observatory.md`](../docs/spec/agent-observatory.md) is one scenario and it
is kept as its own task rather than folded into a neighbour, because it is the only report about the
kit's own machinery failing rather than about the work it produced. Read the contract for what must be
true; it is not restated here.

## Scope

**In scope:** the health report, covering hook failures, retried API errors, and runs that ended
abnormally, each with its session, its time, and what it reported.

**Out of scope:**

- **Fixing anything it finds.** This reports; it repairs no hook and retries nothing.
- **Alerting, thresholds, or a failure budget.** Epic E item 7(c) holds bounds behind item 5.
- **Hook failures outside the corpus.** A hook that failed before writing anything is not visible here,
  and the report says so rather than implying completeness.
- **Judging whether a hook's output was correct.** Only whether it ran and what it exited with.

## Implementation notes

**Confirm what the corpus actually records for each of the three cases before depending on a field.**
Hook outcomes, API retries, and abnormal termination are recorded in different shapes, and this task
is short enough that reading them first costs less than guessing once.

**The report must say what it cannot see.** A hook that never ran, or that failed before producing a
record, leaves no trace, so a clean health report is not evidence that nothing failed. That
qualification belongs in the report surface rather than in a code comment, for the same reason
`AGENTS.md` says a passing gate set is necessary but not sufficient.

**A retried error that eventually succeeded is not a failure, and is worth reporting anyway.** Report
the attempt count rather than collapsing the event to success or failure, since the interesting signal
is a session that is quietly taking four attempts per request.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] A new test covers S-016, named so the scenario it proves is identifiable.
- [ ] A hook failure is reported with its session, its time, its exit status, and what it wrote
      (S-016).
- [ ] A retried API error is reported with its attempt count, whether or not it eventually succeeded
      (S-016).
- [ ] A run that ended abnormally is reported as such (S-016).
- [ ] The report states that a failure leaving no record in the corpus is invisible to it.
- [ ] A corpus with no health events renders an explicitly empty report, not a blank panel.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] The `agent-observatory` conformance matrix is updated for S-016.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
