---
id: bug-0051
title: Every observatory reader takes a write lock on connect, so a concurrent ingester takes the page down
type: bug
status: done
priority: P1
parent: "ROADMAP Epic E #7b: reporting"
depends_on: []
touched_files:
  - scripts/observatory/db.py
  - tests/test_observatory.py
created: 2026-08-29
---

## Problem

While another process holds a write transaction on `.observatory/store.db`, every store-reading
route of [`serve.py`](../../scripts/observatory/serve.py) fails with
`sqlite3.OperationalError: database is locked`. Observed live twice, on 2026-08-28 and again on
2026-08-29 during reconciliation, in the ordinary case: a page open in a browser while a concurrent
session's ingester runs.

**Diagnosed, not guessed.** The full record, including two disproved hypotheses and a refutation of
the first cause this investigation named, is the `## Dogfood record` section of
[`feat-0062`](feat-0062-dogfood-systematic-debugging-then-promote-it.md). This task carries what
that record established and nothing it did not.

**The cause is one statement.** [`db.py`](../../scripts/observatory/db.py) line 254 issues an
unconditional

    conn.execute(
        "INSERT INTO schema_meta (key, value) VALUES ('schema_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()

on **every** call to `connect()`. `connect()` is the component's only
connection factory: no other `sqlite3.connect` exists anywhere under `scripts/`, so the server, the
ingester and every test share it. A read-only HTTP GET therefore takes a write lock, contends with
any concurrent writer, and waits.

**How long it waits is a second contribution, at line 215.** `sqlite3.connect(str(path))` is called
with no `timeout=`, so every reader inherits SQLite's 5 second default busy timeout. Five seconds is
well inside the normal range for this component's own ingester: the same full corpus pass measured
22.8s cold and 1.7s warm on one machine, the difference being page cache.

**Two things this is not, both excluded by measurement rather than by argument.** The journal mode
is not involved: converted to WAL with nothing else changed, the failure is byte-identical. And it is
not the `CREATE TABLE IF NOT EXISTS schema_meta` earlier in the same function, which boundary probes
showed returning in 0.000s under a held writer.

**The contract does not describe this.** `agent-observatory.md`'s Constraints cover the *corpus*
being written concurrently by the harness that owns it. Two observatory processes contending on the
observatory's *own store* is undescribed, which is why this task declares no `spec` and no
`scenarios`. Whether the contract should gain a scenario is a question for whoever fixes this, and it
is an amendment task if the answer is yes, not an edit to make here.

## Reproduction

Four cells, one variable each, against a writer holding a write transaction for a fixed 12 seconds,
with three store-reading routes plus one route that never opens the store. Run against copies of the
store, never the tracked one.

| Cell | The one variable | Store routes answering | Latency |
|---|---|---|---|
| as shipped | none | **0 of 3**, 3 lock errors | fails at 5.55s |
| WAL | journal mode only | **0 of 3**, 3 lock errors | fails at 5.51s |
| `timeout=30` | the timeout only | 3 of 3 | 11.6s to 11.8s |
| upsert guarded | the write on open only | **3 of 3** | **0.01s to 0.19s** |

The route that never opens the store answers in 0.00s in every cell, which is what localizes the
failure to `connect()` rather than to the server.

**The fourth cell is the one to read.** Guarding the upsert removes the contention, so readers return
at baseline speed. Raising the timeout only widens the window, so readers still wait out the entire
writer hold. They are not equivalent fixes and the difference is two orders of magnitude.

## Scope

**In scope:** stop a reader taking a write lock it does not need.

- **The upsert at line 254 runs only when it would change something.** `found` is already in scope
  from the version check above it and is `None` for a fresh store and an `int` otherwise, so the
  guard is available without new state.
- **Decide the `timeout=` question separately and record the decision.** It is not the cause, and
  removing the contention may make it moot. A timeout is still cheap insurance against the writer
  this component cannot see, and leaving the default at 5 seconds is a choice rather than an
  oversight once this task has looked at it. Say which, and why.
- **A regression test that fails against the current code**, and that pins the behavior rather than
  the repair; see the acceptance criteria for why that distinction matters here.

**Out of scope:**

- **The unhandled error path.** A `sqlite3.OperationalError` raised inside `connect()` escapes
  `_with_store` with no response written, which is why the symptom is a dropped connection rather
  than a 500. That is [`bug-0052`](bug-0052-a-sqlite-error-in-a-route-escapes-with-no-response-written.md),
  it is independently fixable, and it stays a defect after this one is closed.
- Converting the store to WAL. Measured above as having no effect on this defect. It may be worth
  doing for other reasons, and that is a separate decision with its own evidence.
- Any change to `serve.py`. The cause is in `db.py` and the fix belongs where the cause is.

## Implementation notes

`connect()` is called by the ingester too, which legitimately writes. The guard must not break the
path that establishes the version on a fresh store or after a forward migration, which is exactly
the case `found` distinguishes. The schema-version write is the only unconditional write in the
function; `conn.executescript(SCHEMA)` above it is `CREATE TABLE IF NOT EXISTS` throughout and
returned in 0.001s under the held writer.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] With a writer holding a write transaction on the store, a store-reading route returns a
      response, and returns it without waiting out the writer's hold.
- [x] The regression test fails against the current code. Confirm it does before the fix, per the
      discipline in `.agents/skills/test-author/SKILL.md`.
- [x] **The test pins the behavior, not the repair.** A test asserting on `PRAGMA busy_timeout`
      passes for a change that leaves every reader waiting out the writer, and fails for the better
      fix that removes the contention. The observable is that a route answers under a held writer.
- [x] Opening a fresh store still records the schema version, and a forward migration still updates
      it. Both are what the guard must not break.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
