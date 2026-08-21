---
id: bug-0035
title: CONTRIBUTING and the pull request template still prescribe four commands that cover four of the seven gates
type: bug
status: done
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - CONTRIBUTING.md
  - .github/PULL_REQUEST_TEMPLATE.md
created: 2026-08-18
---

## Problem

[`feat-0045`](feat-0045-committed-acceptance-command.md) made one committed command the
acceptance gate. [`AGENTS.md`](../../AGENTS.md) says so plainly: `run-checks.py` "runs every gate that
decides whether a change here is acceptable, in one command with no flags". Seven gates.

The two documents a **contributor** reads were never updated. `CONTRIBUTING.md` still opens its
"Before you open a change" section with "Run all four", and lists four commands. The pull request
template still says "Check what you ran. All four are standard-library only", and
`CONTRIBUTING.md` line 55 tells the reader that "the pull request template asks which of the four
you ran", so the two are consistent with each other and both wrong about the repository.

This is not a wording nit, because of which three are missing. The four listed are
`validate-skills.py`, the unittest suite, `.tasks/validate.py --strict`, and the doc link check.
The three a contributor never runs are **adapters dry run**, **install dry run**, and **install
cycle**, which are the gates covering the code that places this kit into somebody's home directory.
A contributor who follows `CONTRIBUTING.md` exactly, ticks the template's boxes honestly, and opens
a pull request has not exercised the installer at all, and both documents told them they were done.

The failure is quiet in the usual way: CI runs `run-checks.py` and catches it, so the contributor
learns their change was incomplete from a red build rather than from the instructions, and nothing
ever reports that the instructions were the problem.

Found 2026-08-18, from an unverified aside in `chore-0041`'s delegate report. That report only
noticed the two documents agree with each other on the number four; the drift against `AGENTS.md`
and the identity of the missing three are this task's finding.

## Scope

**In scope:** make both contributor-facing documents prescribe the acceptance command that
`AGENTS.md` defines.

- `CONTRIBUTING.md`: replace the four-command block with `python scripts/run-checks.py`, and keep
  whatever is genuinely useful about naming individual gates, for instance that a contributor
  iterating on one skill can run the lint alone while it is the acceptance command that decides.
- `.github/PULL_REQUEST_TEMPLATE.md`: replace the four-way checklist with the one command, and keep
  the exit-code meaning, since `2` outranks `1` and a contributor seeing `2` needs to know it means
  could-not-run rather than failed.
- The cross-reference at `CONTRIBUTING.md` line 55, which describes the template's shape and breaks
  when the template changes.

**Out of scope:**

- `AGENTS.md`, which is correct and is the reference for this change.
- `run-checks.py` itself, and the gates it runs.
- The `.github/ISSUE_TEMPLATE/` files, which do not carry this claim.
- Any other section of `CONTRIBUTING.md`. The skill-schema rules at line 60 also say "four", about
  frontmatter validator errors, and that four is unrelated and correct. Do not chase the number.

## Implementation notes

Check what the seven gates currently are by reading `run-checks.py` rather than copying the list
from this task file, which was written on 2026-08-18 and is exactly the kind of restatement that
produced this bug. The same applies to the exit-code meanings.

Prefer naming the one command and letting `AGENTS.md` own the gate list, rather than reproducing
seven gate names in two more documents. Three copies of a list is how this drifted from four to
seven in the first place, and `tests/test_run_checks.py` already asserts that the workflow does not
restate the gates inline, which is the same principle applied to CI.

The honest framing for the closeout is that this shipped incomplete: `feat-0045` changed the
acceptance command and updated `AGENTS.md` and the workflow, and left the two documents a human
reads. That is the gap `doc-sync`'s current-state classification exists to close, and it was not run
over these two files at that task's closeout.

## Decisions

- **Rejected: naming the seven gates in either document.** Read from `run-checks.py`, the gates are
  lint skills, test suite, backlog, adapters dry run, install dry run, install cycle, and doc links.
  Neither document now states that list or its count, because `AGENTS.md` owns it and a third and
  fourth copy is precisely what drifted from four to seven here. Both documents point at
  `AGENTS.md` instead, so the count cannot go stale again.
- **Seam left open deliberately: `CONTRIBUTING.md` still names one gate command.**
  `scripts/validate-skills.py` survives as an example of a faster inner loop while reworking a
  single skill, explicitly labelled a convenience and not a substitute, per this task's scope note.
  That is one command as an illustration, not a checklist, and it should not be read as the start of
  a new list to complete.
- **Premise partly stale: `CONTRIBUTING.md` was not entirely un-updated.** The task says the two
  contributor documents "were never updated" after `feat-0045`. In fact `CONTRIBUTING.md` already
  named `python scripts/run-checks.py` and stated its three exit codes, but as a secondary "or run
  all of them ... in one command" after the four-command block, and it still opened with "Run all
  four" and still described the template as asking "which of the four you ran". The bug and its
  scope hold; the fix was a reordering and a promotion rather than an addition. The exit-code prose
  it already carried was checked against the script and was correct, and was rewritten only to add
  the reason `2` outranks `1`.

## Risks and rollback

Touches two documents in different trees and no code, so the more-than-one-module rule does not fire.
The one way to get this wrong is to leave the two documents disagreeing with each other, since
`CONTRIBUTING.md` describes the template's shape in prose; change both in the same pass and re-read
the cross-reference afterwards.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] `CONTRIBUTING.md`'s "Before you open a change" section prescribes `python scripts/run-checks.py`
      as the acceptance command.
- [x] `.github/PULL_REQUEST_TEMPLATE.md` asks about that command rather than about four separate ones.
- [x] Neither document claims a count of gates that disagrees with `run-checks.py`, verified by
      reading the script rather than this task.
- [x] The `CONTRIBUTING.md` cross-reference describing the template matches the template as changed.
- [x] The unrelated "four" at `CONTRIBUTING.md` line 60, about frontmatter validator errors, is
      untouched.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
