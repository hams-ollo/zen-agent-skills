---
id: bug-0059
title: A transcript replaced with a file of the same byte count is classified as unchanged and never re-read
type: bug
status: open
priority: P1
parent: "ROADMAP Epic E #7b: reporting"
depends_on: []
spec: docs/spec/agent-observatory.md
scenarios: ["S-005"]
touched_files:
  - scripts/observatory/ingest.py
  - tests/test_observatory.py
  - docs/spec/agent-observatory.conformance.md
created: 2026-08-31
---

## Problem

`ingest` in [`ingest.py`](../scripts/observatory/ingest.py) decides whether a transcript needs
reading from two fields, and the row it writes three statements later carries a third:

    row = conn.execute(
        "SELECT offset, size FROM ingest_state WHERE path = ?", (key,)
    ).fetchone()
    ...
    if row and stat.st_size == row["size"] and start == stat.st_size:
        continue  # unchanged since last run: S-005's cheap path

`ingest_state` stores `mtime_ns NOT NULL` and the `INSERT` below populates it, but the `SELECT`
never asks for it. So a transcript **replaced** by different content of the same byte count matches
on size and offset, takes the cheap path, and is skipped. It stays skipped on every later run until
some other change moves its size, because nothing in the decision ever looks at the marker that did
change.

**The subsystem already knows this case occurs.** `corpus_fingerprint` in
[`serve.py`](../scripts/observatory/serve.py) states the counter-argument in its own docstring:

> Size and modification time together, because either alone misses a case: a rewritten transcript
> can keep its size, and a same-second append can keep its timestamp.

The live watcher reasons about it and the ingest branch it calls does not, so the two halves of one
subsystem disagree about the same file.

**The live path makes it worse rather than better.** `LiveWatcher.poll_once` notices the change
through `corpus_fingerprint`, calls `ingest`, gets `records: 0` back, and returns `None` without
publishing an event. An open page receives nothing and keeps showing the superseded figures. That
is the shape [`SECURITY.md`](../SECURITY.md) names as a safety problem rather than a bug: a step
that appears to work while quietly doing nothing.

**Measured on 2026-08-31**, in a temporary corpus and a temporary store, both removed afterwards.
The repository's own `.observatory/store.db` was never opened. Two records of identical length
differing only in `uuid`:

```text
len(a)=463 len(b)=463 equal=True
first  ingest: files_read=1 records=1
second ingest: files_read=0 records=0
stored uuids=['a1']   (file on disk now holds a2)
stored mtime_ns=1788208595309456100  actual mtime_ns=1788208595454472500  differ=True
```

The last line is the fix in one measurement: the discriminator is already in the store and already
correct, and the decision simply does not consult it.

The existing regression test, `test_a_shortened_transcript_is_re_read_without_duplicating_rows` in
[`test_observatory.py`](../tests/test_observatory.py), covers only the case where the replacement is
**shorter** than the recorded offset, which the `stat.st_size < start` reset above already handles.
Nothing reaches the equal-size case.

## Scope

**In scope:** a transcript whose stored modification marker no longer matches the file is re-read.

- Add `mtime_ns` to the `SELECT` and to the unchanged condition, so all three recorded fields have
  to agree before the cheap path is taken.
- An equal-size regression test beside `TestReplacedTranscript`, asserting on the **stored content**
  and not only on the returned counts, since a run that re-reads and stores nothing new would pass a
  counts-only assertion.
- Update the `S-005` row of
  [`agent-observatory.conformance.md`](../docs/spec/agent-observatory.conformance.md), whose
  evidence currently states the mechanism this task changes: "`ingest` skips a transcript whose
  recorded size and offset both match the file on disk."

**Out of scope:**

- A content fingerprint or any second identity signal. `mtime_ns` is already stored, already
  differs in the measurement above, and is the cheapest sufficient answer. Reach for more only if
  the test proves it is not enough on some platform, and file that separately if so.
- `corpus_fingerprint` and `LiveWatcher`. They are correct here; the watcher's separate
  observability gap is `chore-0086`.
- Amending `docs/spec/agent-observatory.md`. `S-005` says "a corpus that has not changed", which is
  the promise being restored rather than a promise being altered.
- Any change to `db.py` or the schema.

## Implementation notes

The three-field comparison makes the first run after this lands re-read every transcript whose
recorded `mtime_ns` disagrees with disk, which on the maintainer's 396 MB corpus could be a large
one-off read. That is correct rather than a regression, and it is safe: re-reading a transcript is
already an exercised path, and `apply_record`'s conflict clauses are what stop it duplicating rows,
which `test_a_shortened_transcript_is_re_read_without_duplicating_rows` exists to prove. Reverting
this commit restores the old behavior with no store surgery, so the change needs no migration.

Mirror the existing test's structure rather than inventing a second fixture shape:
`ObservatoryTestCase` already gives `write_transcript`, `record` and `counts`. The two records need
equal serialized length, which `record("a1")` and `record("a2")` give for free.

`st_mtime_ns` resolution differs by filesystem. The new test replaces the file after the first
ingest has already run, so a same-tick collision is the only failure mode; if it proves flaky on a
coarse filesystem, set the replacement's mtime explicitly with `os.utime` rather than sleeping.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] A new test replaces a transcript with different content of **identical byte length** and
      asserts the store holds the replacement's content afterwards, not the original's.
- [ ] That test fails against the current code. Confirm the failure before the fix.
- [ ] `test_a_shortened_transcript_is_re_read_without_duplicating_rows` still passes unchanged, and
      the shortened replacement still does not duplicate rows.
- [ ] `test_s005_reingesting_an_unchanged_corpus_adds_no_rows` still passes: a genuinely unchanged
      corpus must still take the cheap path, and a fix that simply always re-reads is not a fix.
- [ ] The `S-005` row of the conformance matrix names the three-field comparison and cites the new
      test.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
