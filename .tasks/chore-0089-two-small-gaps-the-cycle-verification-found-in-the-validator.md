---
id: chore-0089
title: Two small gaps the cycle verification found in the validator, one unpinned behavior and one unnormalised field
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [bug-0061]
touched_files:
  - .tasks/validate.py
  - .agents/skills/init-worktracking/templates/validate.py
  - tests/test_tasks_validate.py
created: 2026-08-31
---

## Problem

Two items, both raised by the independent verification of
[`bug-0061`](done/bug-0061-the-strict-backlog-gate-accepts-a-dependency-cycle.md) and both deliberately
left out of it. Neither is a defect in that change; they are filed together because they touch the
same three files and neither is worth a task alone.

**1. A ring running through a completed task is unpinned.** `bug-0061`'s scope note says a
dependency **into** `.tasks/done/` is satisfied and not a cycle, which is correct and is tested. It
says nothing about a ring in which a member *lives* in `done/`. The observed behavior is to report
it:

```text
ERROR .tasks/done/chore-0001-x.md: depends_on cycle: chore-0001 -> feat-0001 -> chore-0001
```

That is the right answer, since a done task naming an open task that names it back is a genuine
ring and a real backlog defect. It is not the answer any test asserts, so nothing stops a later
change from silently making a done member terminate the search, which would hide exactly that
defect. `git grep -n "done=True" tests/test_tasks_validate.py` returns two lines, neither in a cycle
test.

**2. `depends_on` is not normalised from a scalar, while `scenarios` is.** In
[`validate.py`](validate.py), `main` iterates `fm.get("depends_on", []) or []` directly, four lines
above where `scenarios` gets scalar-to-list normalisation. A scalar `depends_on: feat-0001` is
therefore walked character by character.

**This is pre-existing and cannot currently manufacture a false cycle**, because a single character
is never a known id, so no edge is recorded and the only symptom is a run of `depends_on
unresolved` errors naming single letters. It is filed rather than fixed silently because the
asymmetry with the field four lines below reads as an oversight to every future reader, and because
`bug-0061` now builds a graph from that same loop, which raises the cost of the asymmetry from
confusing to load-bearing.

## Scope

**In scope:**

- A test pinning that a ring with a member in `.tasks/done/` is reported, in both validator copies
  through the existing paired fixture.
- Normalise a scalar `depends_on` to a single-element list, matching what `scenarios` already does,
  in both copies.
- A test for the scalar case, asserting the diagnostic names the whole id rather than a letter.

**Out of scope:**

- Any change to the cycle search itself. It is correct, and was verified exhaustively over every
  directed graph on five nodes against Kahn's algorithm plus 40,000 random graphs, with zero
  mismatches.
- Deciding whether a ring through `done/` should instead be a warning. It is an error today, that is
  the right answer, and this task pins the behavior rather than reopening it.
- Normalising any other frontmatter field, or introducing a general coercion helper. Two fields is
  not yet a pattern.

## Implementation notes

Both changes land in both copies, in the same commit, for the reason `bug-0026` and `bug-0061` both
record. `ValidatorCopiesAgreeTests` compares the executable code with docstrings excluded, so it
will catch a copy that drifts.

The scalar normalisation must not accept a dict or an int as if it were an id. Mirror whatever
`scenarios` does rather than inventing a second shape, so the two stay comparable.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] A ring with a member in `.tasks/done/` is reported as an error under `--strict`, in both
      copies through the paired fixture.
- [ ] A scalar `depends_on` produces a diagnostic naming the whole id, not one naming single
      characters, in both copies.
- [ ] Both tests fail against the current code. Confirm the failures before the fix.
- [ ] `ValidatorCopiesAgreeTests` still passes, so the two copies did not drift.
- [ ] The real `.tasks/` tree still reports zero cycles at unchanged error and warning counts.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
