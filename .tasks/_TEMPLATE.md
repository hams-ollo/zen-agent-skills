---
id: TYPE-NNNN
title: One-line imperative summary of the work
type: bug
status: open
priority: P1
parent: "ROADMAP#N feature-slug"
depends_on: []
# Optional, for a task decomposed from an approved spec. Omit both when there is
# no spec. A readiness gate reads them to map this task back to its contract.
spec: ""
scenarios: []
# Optional. The upstream issue this task serves, in GitHub's own syntax: "#123"
# for this repository, "owner/repo#123" for another. `pr-describe` emits a
# closing reference for it, so merging the pull request closes the issue. A bare
# number is rejected; see docs/spec/tracker-links.md.
external: ""
touched_files:
  - path/to/file/the/task/will/change
  - path/to/its/test
created: YYYY-MM-DD
---

## Problem

What is wrong or missing, and why it matters. Point at the exact code, function, or behavior (with a relative link). Enough that an agent understands the intent without reading the roadmap.

## Scope

**In scope:** the specific change to make.

**Out of scope:** adjacent things a well-meaning agent might touch but should not, so the change stays atomic.

## Implementation notes

Any known constraints, the intended approach, edge cases, or prior art in the codebase to mirror. Optional if the Problem + Scope are unambiguous.

## Risks and rollback

Optional, and **required** when any of these hold, because a readiness gate checks for it:

- the task touches more than one module;
- it changes a persisted data format or protocol; or
- it cannot be safely reversed by reverting one commit.

When required, state what could go wrong and how to undo it. When none of the three hold, delete this
section rather than leaving it empty: a heading every task carries and most leave blank teaches
authors to skip it.

## Acceptance criteria (mechanically verifiable)

    <exact command that must pass, e.g. the project's test command scoped to this area>

- [ ] New/updated test proving the fix or feature.
- [ ] Existing tests still pass.
- [ ] (add concrete, checkable criteria specific to this task)

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
