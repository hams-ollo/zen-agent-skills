---
id: chore-0089
title: Two small gaps the cycle verification found in the validator, one unpinned behavior and one unnormalised field
type: chore
status: done
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
[`bug-0061`](bug-0061-the-strict-backlog-gate-accepts-a-dependency-cycle.md) and both deliberately
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
[`validate.py`](../validate.py), `main` iterates `fm.get("depends_on", []) or []` directly, four lines
above where `scenarios` gets scalar-to-list normalisation. A scalar `depends_on: feat-0001` is
therefore walked character by character.

**This is pre-existing, and the direction stated here was wrong.** It cannot manufacture a *false*
cycle, because a single character is never a known id, so no edge is recorded. That is exactly why
it **suppresses a true one**: a ring whose members write `depends_on` as a scalar contributes no
edges at all, so `bug-0061`'s cycle search never sees it. Measured at `648a140` on a two-node ring
written that way: exit 1, **zero** cycle lines, eighteen single-character unresolved errors. After
the normalisation: exit 1, one correct cycle line, no unresolved errors. The run failed either way,
which is what hid it, but it failed reading as two broken files rather than as a ring. Corrected at
reconciliation after independent verification found it; pinned by
`test_a_ring_written_with_scalar_depends_on_is_still_reported`, which was added in the same pass and
confirmed failing against the base in both validator copies.

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

## Decisions

- **A premise that turned out false.** The acceptance criterion "Both tests fail against the current
  code" holds for the scalar test and not for the done-ring one. The task's own Problem section says
  the ring behaviour is already correct and merely unasserted, so a test that pins it passes on the
  unmodified validator by construction; the two statements cannot both be true. Confirmed by running
  it before any edit: `ok` in both copies. Its non-vacuity was shown instead by the mutation the task
  names, adding `and not in_done` to the edge-recording branch, which drops the run from exit 1 with
  one cycle line to exit 0 with none.
- **A rejected alternative: a second paired test class.** Both cases went into `DependencyCycleTests`,
  which `TemplateDependencyCycleTests` already inherits, rather than into a new
  `ScalarDependsOnTests` pair. The scalar case is input handling rather than graph search, so the fit
  is imperfect, but `bug-0061` builds the graph out of that same loop, and a second fixture for two
  cases is the duplication `bug-0026` records the cost of.
- **A rejected alternative: coercing anything that is not a string.** The guard wraps a `str` and
  leaves every other type alone, which is exactly what `scenarios` does four lines below. Wrapping a
  non-string would let a value that is not an id be reported as one, and the asymmetry with
  `scenarios` is what this task exists to remove.
- **A seam left open deliberately.** A `dict` reaching this loop has its keys iterated rather than
  being wrapped, and an `int` raises `TypeError`. Neither is reachable: `parse_frontmatter` returns
  only `str` or `list[str]`, an indented mapping under `depends_on:` is skipped by its key regex and
  yields `[]`, and a bare `depends_on: 42` arrives as the string `'42'` and is reported whole. This
  matches `scenarios` exactly and is left rather than hardened, per the out-of-scope note against a
  general coercion helper.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] A ring with a member in `.tasks/done/` is reported as an error under `--strict`, in both
      copies through the paired fixture.
- [x] A scalar `depends_on` produces a diagnostic naming the whole id, not one naming single
      characters, in both copies.
- [ ] ~~Both tests fail against the current code.~~ **Not satisfiable as written, and not ticked.** The Problem section above states the ring-through-`done/` behaviour is already correct, so a test pinning it passes before the fix by construction. The scalar test did fail pre-fix; the done-ring test was instead shown non-vacuous by mutation. Authoring defect, recorded rather than satisfied.
- [x] `ValidatorCopiesAgreeTests` still passes, so the two copies did not drift.
- [x] The real `.tasks/` tree still reports zero cycles at unchanged error and warning counts.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
