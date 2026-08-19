---
id: chore-0044
title: The install guide's Validate changes section carries the same pre-run-checks instruction bug-0035 fixed in two other documents
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [bug-0035]
touched_files:
  - docs/INSTALL.md
created: 2026-08-18
---

## Problem

[`bug-0035`](done/bug-0035-contributing-still-prescribes-the-four-pre-run-checks-commands.md) found that
`CONTRIBUTING.md` and the pull request template still prescribed the individual commands that
`feat-0045` replaced with one acceptance command. Its delegate agent flagged, without reading them,
that other documents might carry the same instruction. Checked 2026-08-18: one does.

[`INSTALL.md`](../docs/INSTALL.md) has a `## Validate changes` section that tells a reader to "Run
the skill linter from the repository root", gives `python scripts/validate-skills.py`, then "Run the
kit's own test suite" and gives that command too. Same shape, same gap: a reader who follows it runs
two of the seven gates and is told nothing about the other five, including the three that cover the
installer, which is the very subject of the document they are reading.

`README.md` was checked and is clean. Its only mention of `validate-skills.py` is a description in
the repository layout table, which is naming a file rather than prescribing a command.

This is filed separately rather than folded into `bug-0035` because that task was already dispatched
and verified against a `touched_files` of two documents, and widening a task after its agent has
finished is how a verified change quietly becomes an unverified one.

## Scope

**In scope:** make `INSTALL.md`'s `## Validate changes` section prescribe the acceptance command,
in whatever shape `bug-0035` settled on for the other two documents, so the three read consistently.

**Out of scope:**

- `CONTRIBUTING.md` and `.github/PULL_REQUEST_TEMPLATE.md`, which are `bug-0035`'s and will already
  be correct when this runs.
- `README.md`, checked and clean.
- Every other section of `INSTALL.md`. The document's job is the installer, and only this one section
  makes a claim about how a change is validated.
- `AGENTS.md` and `run-checks.py`, which are correct and are the reference.

## Implementation notes

Read what `bug-0035` did to the other two documents first and match it, rather than deciding the
shape again. Three documents phrased three ways is how this class survives a fix, and this is the
third document in the same family.

Do not restate the gate list here. `bug-0035`'s reasoning applies unchanged: `AGENTS.md` owns the
list, and a copy in a fourth place is a fourth thing to drift.

Keep whatever the section says about running the linter alone while iterating on a skill, if
`bug-0035` kept the equivalent. The bug is that the individual commands are presented as sufficient,
not that naming them at all is wrong.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] `INSTALL.md`'s `## Validate changes` section prescribes `python scripts/run-checks.py` as the
      command that decides whether a change is acceptable.
- [ ] It does not restate the gate list or a gate count.
- [ ] Its shape matches what `bug-0035` established in `CONTRIBUTING.md`, verified by reading both.
- [ ] No other section of `INSTALL.md` is modified.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
