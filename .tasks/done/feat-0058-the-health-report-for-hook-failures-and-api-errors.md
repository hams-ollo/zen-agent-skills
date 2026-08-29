---
id: feat-0058
title: Report what failed during a run, since hook failures and retried API errors currently reach nobody
type: feat
status: done
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
The hooks module contract in [`.agents/hooks/README.md`](../../.agents/hooks/README.md) requires a
reminder to exit cleanly whatever happens, which is correct and means a broken hook is invisible: it
stops contributing and nothing says so.

Retried API errors have the same shape. The retry succeeds, the session continues, and the fact that
it took four attempts reaches nobody.

`S-016` in [`docs/spec/agent-observatory.md`](../../docs/spec/agent-observatory.md) is one scenario and it
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

- [x] A new test covers S-016, named so the scenario it proves is identifiable.
- [x] A hook failure is reported with its session, its time, its exit status, and what it wrote
      (S-016).
- [x] A retried API error is reported with its attempt count, whether or not it eventually succeeded
      (S-016).
- [x] A run that ended abnormally is reported as such (S-016).
- [x] The report states that a failure leaving no record in the corpus is invisible to it.
- [x] A corpus with no health events renders an explicitly empty report, not a blank panel.
- [x] Existing tests still pass, unchanged in intent.

## Decisions

- **A count is of events, not of stored rows, and the grouping happens in the report.** Rejected:
  a `COUNT(*)` over `health_event`, which is what the table's shape invites. A forked or resumed
  session replays records verbatim under a new session id, so 428 rows on this machine are 345
  distinct events and the 19 that look like hook failures are 14. `message` and
  `message_occurrence` already solve exactly this for messages; `health_event` has no equivalent
  split, so `health_events()` groups on everything but the session and carries the full session
  list. Also rejected: adding that split to the store, because the schema is `feat-0053`'s and a
  migration is not this task's to slip in. **The seam:** if a later report needs the same grouping,
  the store is the right place for it and this function is the thing to lift.

- **Which session a replayed event is attributed to is deterministic rather than meaningful, and
  that is a seam.** The corpus does not record which session originally produced a replayed
  record: every forked pair carrying a health event on this machine shares a `first_ts`, because
  the fork replays the parent's earliest record too, so the `(first_ts, session_id)` sort always
  falls through to the id. Rather than picking one and hiding the rest, every session an event was
  seen in is reported beside it. Do not read the first as "where it happened".

- **API errors are grouped into retry episodes rather than listed one attempt at a time.** The
  scenario asks for a retry count, and 10 rows reading "attempt 1" to "attempt 10" state that only
  to a reader who adds them up. Rejected: deriving whether the retry eventually succeeded. The
  corpus records the retries and not the verdict, and the task's own note says the signal is the
  cost of the request rather than its outcome.

- **A kind this report does not count is listed and labelled, not filtered out.** `stop_hook_summary`
  is the reason: it is a recorded bound (the branch writes no row on this corpus and
  `prevented_continuation` is NULL everywhere), and a ledger built only from what the store holds
  would render that bound as an absence. **Both bounds were re-checked and both still hold**: 0
  rows of that kind and 0 carrying a `prevented_continuation` value, out of 428, on 2026-08-29.
  A filtered-to-zero branch is a bound, not a repair, and this report says so on the page.

- **No bound, threshold, or alert, deliberately.** ROADMAP Epic E item 7(c) holds those. The report
  says a request took ten attempts and never that ten is too many.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] The `agent-observatory` conformance matrix is updated for S-016.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
