---
id: bug-0052
title: A sqlite error inside a route escapes the handler with no response written, so the client hangs
type: bug
status: open
priority: P2
parent: "ROADMAP Epic E #7b: reporting"
depends_on: []
touched_files:
  - scripts/observatory/serve.py
  - tests/test_observatory_serve.py
created: 2026-08-29
---

## Problem

`_with_store` in [`serve.py`](../scripts/observatory/serve.py) line 2157 converts exactly one
database failure into a response and lets every other one escape:

    try:
        conn = db.connect(store)
    except db.StoreUnusable as exc:
        return self._json({"store": str(store), "store_present": True,
                           "error": str(exc)}, 500)
    try:
        payload = build(conn)
    finally:
        conn.close()

A `sqlite3.OperationalError` is not a `db.StoreUnusable`, so one raised inside `db.connect` at line
2171 passes straight through that `except`. And `build(conn)` below it is wrapped in `try/finally`
with no `except` at all, so a failure there escapes too. In both cases the exception leaves `do_GET`
with **no response written**, and the client gets a dropped connection or hangs until its own
timeout rather than receiving an error.

**Observed, not inferred.** In 12 of 12 failures produced while investigating
[`bug-0051`](bug-0051-every-observatory-reader-takes-a-write-lock-on-connect.md), the exception was
raised inside `db.connect` and escaped at line 2171. Clients disconnected at 5.5 seconds; in one
harness two of them hung for 45 seconds. Full record in the `## Dogfood record` section of
[`feat-0062`](done/feat-0062-dogfood-systematic-debugging-then-promote-it.md).

**This is a separate defect from `bug-0051` and it outlives it.** `bug-0051` removes the contention
that makes `database is locked` likely. It does not make a sqlite failure impossible: a store on a
full disk, a store another process has corrupted, a store on a disconnected network path, and a
store the ingester is mid-migration on all still raise from the same two call sites. After
`bug-0051` this defect is rarer and exactly as silent.

**A caveat worth keeping when the fix is written.** The current shape is not sloppiness. `_with_store`
answers a **missing** store with a 200 and a `store_present: false` payload rather than an error,
which is a deliberate distinction the page relies on, and `StoreUnusable` is caught to give a
schema-version failure a readable message. Neither behavior should change; what is missing is the
branch for everything else.

## Scope

**In scope:** no exception from the store leaves a route without a response.

- **Both call sites**, `db.connect` and `build(conn)`. Only the first has been observed failing, and
  the second is the same gap reached from the other end.
- **A status that says which kind of failure it was.** A lock or a busy store is transient and a
  client may retry; a corrupt store is not. `503` against `500` is the obvious split and the decision
  belongs to whoever writes this.
- **The message must not leak a path an adopter did not ask to publish.** `serve.py` refuses a
  non-loopback `Host` for exactly this reason: the corpus carries every session's working directory.
  A raw sqlite message naming a store path is far milder and is still worth a deliberate decision
  rather than an accident of `str(exc)`.

**Out of scope:**

- **The contention that made this visible.** That is `bug-0051`. Fixing this one does not fix that
  one and does not depend on it, which is why they are two tasks.
- Retry, backoff, or any recovery behavior. A response is the deliverable; retrying is a different
  design question and belongs to a page that has one.
- Anything under `db.py`.

## Implementation notes

`ObservatoryHandler` extends `BaseHTTPRequestHandler`. An exception escaping `do_GET` is caught by
the base class, which logs a traceback and closes the connection, which is why the failure is silent
from the client's side and loud only in the server's own output. A test asserting the server logged
something is asserting the wrong half; the observable is what the client receives.

The natural shape is one `except sqlite3.Error` around both statements rather than a second `except`
per call site, since the response is the same in both cases and two branches drift.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] With the store made to fail, a store-reading route returns an HTTP response with a status and a
      JSON body. **Asserted on what the client receives**, not on what the server logged.
- [ ] The failure is injected at both call sites, `db.connect` and `build(conn)`, since only the
      first has ever been observed and the second is the same gap unreached.
- [ ] The regression test fails against the current code. Confirm it before the fix.
- [ ] A **missing** store still answers 200 with `store_present: false`, and a schema-version failure
      still answers with its readable `StoreUnusable` message. Both are existing behavior this must
      not fold into a generic error.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
