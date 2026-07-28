---
id: feat-0031
title: Teach pr-describe to emit a GitHub closing reference into the PR description
type: feat
status: done
priority: P1
parent: "ROADMAP#9 tracker-links"
depends_on: ["feat-0030"]
spec: "docs/spec/tracker-links.md"
scenarios: ["S-001", "S-002", "S-003", "S-004", "S-005", "S-006", "S-009"]
external: "#1"
touched_files:
  - .agents/skills/pr-describe/SKILL.md
created: 2026-07-28
---

## Problem

`docs/spec/tracker-links.md` (approved) requires the pull request description to carry a closing
reference for every linked task, so merging the pull request closes the upstream issue without
anyone remembering to.

[`pr-describe`](../.agents/skills/pr-describe/SKILL.md) already drafts the pull request body and
already reads the `.tasks/` system to reference the work item, so it holds both halves and is the
only place this belongs. It says nothing about issue references today.

Seven scenarios are unimplemented: S-001 (emit `Closes #123`), S-002 (repeat the keyword per issue),
S-003 (emit nothing when unlinked), S-004 (drop the keyword on a non-default base and say why),
S-005 (preserve a cross-repository reference), S-006 (never in the title), S-009 (emit for a task
moved to `.tasks/done/` in the same change).

## Scope

**In scope:** the `pr-describe` skill body, so its procedure emits references correctly and refuses
to emit one that will silently fail.

**Out of scope:** the `external` field's definition and validation (`feat-0030`); creating, editing,
or closing any issue, which the skill's settled "drafts text, never touches GitHub" decision forbids
and which the spec lists as a Non-Goal; Azure Boards.

## Implementation notes

**This task's scenarios cannot be unit tested, and that is a property of the surface rather than a
shortcut.** `pr-describe` is a skill: a prose procedure an agent follows, not a script with an entry
point. There is nothing to import and call. `feat-0030`'s half is code and is tested; this half is
verified by running it on real work and recording the result, in the format `feat-0024` established
at [`docs/spec/house-review.verification.md`](../docs/spec/house-review.verification.md).

Four details are load-bearing and each maps to a documented GitHub rule, so state them in the body
rather than assuming an agent infers them:

- The reference goes in the **description**. GitHub ignores it in the title (S-006) and in comments.
- **Repeat the keyword per issue.** `Closes #1, #2, #3` closes only `#1` (S-002).
- **The default branch is the condition.** `pr-describe` already computes the merge-base against the
  default branch, so it already knows the base. When the target is not the default branch, emit the
  bare reference with no keyword and say why (S-004), because emitting an inert keyword is exactly
  the silent success this kit treats as a defect.
- **A moved task file still counts** (S-009). Look in `.tasks/done/` as well as `.tasks/`.

## Risks and rollback

Changes a shipped skill that adopters may already have installed, so a regression reaches them on
their next `install.py` run rather than at a release boundary.

The realistic failure is an over-eager emission: a `Closes` line for a task the pull request does not
actually complete, which would close someone's issue early. Prefer emitting nothing when the link
between branch and task is uncertain, and say so in the body. Rollback is reverting the one commit;
no persisted format changes.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [ ] The skill body states all four rules above, each with the behavior it produces.
- [ ] A real run against this repository produces a pull request body containing a correct `Closes`
      reference, recorded at `docs/spec/tracker-links.verification.md` with the scenarios it
      exercised and the ones it did not.
- [ ] That record names which of S-001 to S-006 and S-009 the run actually exercised, rather than
      claiming the set.
- [ ] `python scripts/validate-skills.py` exits 0 (the body stays within length and link rules).
- [ ] Existing tests still pass.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
