---
title: tracker-links verification
spec: docs/spec/tracker-links.md
task: .tasks/done/feat-0031-pr-describe-emits-closing-references.md
verified: 2026-07-28
verdict: pass
---

# tracker-links verification record

Evaluation record for the scenarios of [`tracker-links.md`](tracker-links.md) that live in a skill
body rather than in code. `pr-describe` is a prose procedure an agent follows, not a script with an
entry point, so there is nothing to import and call: S-001 to S-006 and S-009 carry no unit tests by
nature, and this record is their evidence instead. S-007 and S-008 are code and are covered by
[`tests/test_tasks_validate.py`](../../tests/test_tasks_validate.py).

Format follows the record `feat-0024` established at
[`house-review.verification.md`](house-review.verification.md).

## The run

A real one, not a staged one. Issue [#1](https://github.com/hams-ollo/zen-agent-skills/issues/1) was
opened for the work `feat-0031` describes, the task file was given `external: "#1"`, and pull request
[#2](https://github.com/hams-ollo/zen-agent-skills/pull/2) was drafted following the procedure this
very change added to `pr-describe`.

| Step | Outcome |
|---|---|
| Reference emitted | `Closes #1`, in the pull request description |
| GitHub registered it | `closingIssuesReferences` on PR #2 returned `#1` before merge |
| Title checked | Contains no issue reference |
| Base branch | `main`, the repository default |
| CI | 6/6 green (Linux, macOS, Windows on Python 3.11 and 3.14) |
| Merge | Squash-merged 2026-07-28 |
| Issue afterwards | `state: CLOSED`, `stateReason: COMPLETED`, closed at 19:55:23Z |

Nobody closed issue #1 by hand. The merge closed it, which is the whole behavior under test.

## Scenario coverage, honestly

**Exercised, with evidence:**

| Scenario | Evidence |
|---|---|
| S-001 | `Closes #1` appeared in the description and GitHub resolved it to issue #1 before merge, then closed it on merge |
| S-006 | The pull request title was queried directly and contains no reference |

**Not exercised by this run**, and deliberately not claimed:

| Scenario | Why not, and what would exercise it |
|---|---|
| S-002 | Only one issue was linked. Needs a branch completing two or more linked tasks, to prove each reference gets its own keyword rather than sharing one |
| S-003 | Every task in the branch was linked. Needs a pull request whose tasks carry no `external` value |
| S-004 | The pull request targeted `main`. Needs one targeting a non-default branch, to prove the keyword is dropped and the reason stated |
| S-005 | The reference was same-repository. Needs an `owner/repo#123` value, which this repository has no natural occasion for yet |
| S-009 | `feat-0031` was still in `.tasks/` when the body was drafted, and moved to `.tasks/done/` only at closeout. Needs a branch that moves the file and drafts the body afterwards |

Two of seven exercised. The record says so rather than inferring the rest from one success, which is
the same discipline `feat-0024` applied: a branch that has never fired on real work is unexercised no
matter how confident the prose reads.

## What the run found

**One real defect, caught by the linter rather than by review.** The first draft of the skill body
linked to `../../../docs/spec/tracker-links.md`. That escapes the shipped skill tree, so it resolves
in this repository and dangles the moment the skill is installed anywhere else. `validate-skills.py`
failed the run and named it. This is the exact defect class that once shipped `house-review` with no
rubric at all, and it was reintroduced by an author who had read the rule earlier the same day, which
is the argument for the check existing rather than the rule being written down.

**One observation worth carrying.** S-009 could not be exercised because of ordering: the task file
moves to `.tasks/done/` during closeout, which happens after the pull request body is drafted. That
is not a flaw in the scenario, it is a property of the workflow, and it means S-009 will only ever be
exercised by a change that closes a *previous* task rather than its own. Worth remembering before
anyone reads its absence here as an oversight.
