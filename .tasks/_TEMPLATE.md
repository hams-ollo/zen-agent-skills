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

## Acceptance criteria (mechanically verifiable)

    <exact command that must pass, e.g. the project's test command scoped to this area>

- [ ] New/updated test proving the fix or feature.
- [ ] Existing tests still pass.
- [ ] (add concrete, checkable criteria specific to this task)

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
