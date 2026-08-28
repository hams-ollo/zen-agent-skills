---
id: feat-0053
title: Build the observatory store and the incremental ingester that fills it from the session corpus
type: feat
status: done
priority: P2
parent: "ROADMAP Epic E #7b: reporting"
depends_on: []
spec: docs/spec/agent-observatory.md
scenarios: [S-005, S-006, S-007, S-008, S-009, S-022]
touched_files:
  - scripts/
  - tests/
  - docs/spec/agent-observatory.md
created: 2026-08-28
---

## Problem

[`docs/spec/agent-observatory.md`](../../docs/spec/agent-observatory.md) is approved and nothing
implements it. This task builds the layer every other scenario in that contract sits on: a local
store, and the ingester that fills it from the session corpus without changing anything it reads.

It deliberately produces no report surface. The six scenarios it covers are all properties of the
ingest run itself, and every one of them is verifiable from a command line, so building them first
means the hard guarantees are pinned before any of them has a user interface to hide behind.

Read the contract for what must be true. It is not restated here.

## Scope

**In scope:** the store, the ingester, and the tests that prove the six scenarios.

Files this task creates, with their exact paths:

- `scripts/observatory/__init__.py`
- `scripts/observatory/db.py`, the schema and its forward-only migrations
- `scripts/observatory/ingest.py`, the corpus walker and the `main(argv)` entry point
- `tests/test_observatory.py`, over committed fixture transcripts
- `tests/fixtures/observatory/`, the fixtures themselves

The store must hold enough for the later reports to be built without a second ingest pass: sessions,
messages with their per-kind token counts and skill attribution, tool calls, subagent runs, and the
ingest bookkeeping that makes `S-006` true.

**Out of scope:**

- **Any report, server, page, or view.** Those are `feat-0054` onward. This task's only output is a
  populated store and what the command prints about the run.
- **Cost.** No rate table, no monetary figure. `feat-0057` owns `S-010` and `S-011`.
- **Live updates.** `feat-0059` owns `S-013` to `S-015`. Ingest here is a run that starts and ends.
- **The quota and live-session sources.** `feat-0055` and `feat-0057` bring those in; this task reads
  the transcript corpus only.
- **Deciding retention.** Open Question 2 in the spec recommends none, and this task adds none.

## Implementation notes

`main(argv)` injectable, per the precedent [`chore-0017`](chore-0017-give-install-an-injectable-entry-point.md)
set for `install.py` and followed by [`.tasks/validate.py`](../validate.py). The tests depend on it.

**The read-only guarantee is the one to design for, not to assert.** `S-009` requires that every file
the harness owns is byte-for-byte unchanged, and the corpus belongs to a program that may be writing
to it while the ingester reads. Open files for reading only, never in a mode that can create or
truncate, and never write anywhere except the store's own path.

**`S-008` and `S-006` interact, and getting one wrong breaks the other.** A transcript's final line
may be half-written when the ingester reaches it. Recording a byte offset past a partial line means
the rest of that record is never read once it completes. Advance the offset only to the end of the
last record that parsed, so a partial tail is re-read next run rather than skipped.

**`S-007` needs an outcome a caller can distinguish**, not just different words on stdout. This
repository already uses exit codes as contract: [`run-checks.py`](../../scripts/run-checks.py) separates
"ran and failed" from "could not run" for exactly this reason. Follow that shape.

**Do not derive the skill and subagent handles from this task's prose.** Read the corpus and confirm
what the records actually carry before depending on a field name. The contract states what must be
reported, not which key holds it, and a field name written from memory into a task file is the
premise error `new-task` warns about.

## Risks and rollback

The task introduces a persisted data format, so the deterministic rule fires on the second condition.

The schema is the risk. Six later tasks read it, and a shape that cannot express waves or per-kind
tokens forces a migration through work already built on it. Design the schema against the whole
contract's Proposed Surface rather than against this task's six scenarios, then implement only these
six.

Forward-only migrations with a recorded schema version, so a store built by an earlier version is
detected rather than misread.

Rollback is deleting the store file and reverting one commit. The store is derived data with an
authoritative source on disk, so nothing is lost by rebuilding it, and it must be gitignored.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] New tests in `tests/test_observatory.py` cover S-005, S-006, S-007, S-008, S-009, and S-022,
      each named so the scenario it proves is identifiable from the test name.
- [x] Ingesting an unchanged corpus twice adds no rows on the second run (S-005).
- [x] The second run reads only records appended since the first, proven by a count the run reports
      rather than by timing (S-006).
- [x] An empty corpus produces an outcome distinguishable from a populated one, by exit code (S-007).
- [x] A truncated final record is reported as unread and is picked up once complete, not skipped
      (S-008).
- [x] A SHA256 of every file under the corpus root is identical before and after a full ingest
      (S-009).
- [x] No outbound connection is attempted during a full ingest (S-022).
- [x] The store path is gitignored, proven by `git status` staying clean after an ingest.
- [x] Standard library only: `python -c "import scripts.observatory.ingest"` needs no installed
      package.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] The conformance matrix for `agent-observatory` is created, covering the six scenarios this task
      claims and recording the remaining sixteen as not-built.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
