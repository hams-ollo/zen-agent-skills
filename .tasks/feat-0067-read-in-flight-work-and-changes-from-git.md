---
id: feat-0067
title: Read in-flight work and what changed since a revision from git, not from task status
type: feat
status: open
priority: P2
parent: "ROADMAP Epic E #7d: project board"
depends_on: [feat-0066]
spec: docs/spec/sitrep.md
scenarios: [S-008, S-009, S-011, S-039]
touched_files:
  - .agents/skills/
  - tests/
  - docs/spec/sitrep.md
created: 2026-09-11
---

## Problem

The hts-app prototype reported nothing in progress while a worktree held uncommitted work, because it
read `status: in_progress` and no task file in any of the author's repositories sets it. The spec
takes in-flight work from git instead, and summarises what changed since a revision the same way.

## Scope

**In scope:** worktrees with uncommitted changes and the number of changed paths (Purple), branches
holding commits the integration branch does not contain, integration-branch resolution with the
`no integration branch` notice, and the changed-since summary: commit count, tasks closed, tasks
updated.

This task extends `.agents/skills/sitrep/scripts/sitrep.py` and creates `tests/test_sitrep_git.py`.

**Out of scope:** where the base revision comes from (`feat-0069` owns the watermark; here it is a
parameter), reading `integration_branch` from `.sitrep.json` (`feat-0068` wires it; here it is a
parameter defaulting to none), and any rendering.

## Implementation notes

- Worktrees from `git worktree list --porcelain`, skipping any whose directory is gone; changed paths
  are the lines of `git -C <worktree> status --porcelain`.
- Branches from `git for-each-ref refs/heads`, each counted with `git rev-list --count
  <integration>..<branch>`, the integration branch itself excluded and branches with nothing unmerged
  omitted. Order: worktrees first, then branches by most recent commit.
- Integration branch, per the spec's surface: the declared value, else the default branch of remote
  `origin`, else `main`; if none resolves, no branches are listed and the notice is raised, but
  worktrees still are (S-039).
- Changed since: `git diff --name-status -M <base> HEAD -- .tasks`. A task id newly present under
  `.tasks/done/` in the range is closed; a task file modified in place outside `done/` is updated.
- Scenario layer: integration, against throwaway repositories with real worktrees and branches, since
  every behaviour here is a fact about git state.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_sitrep_git.py" -v
    python scripts/run-checks.py

- [ ] Every scenario in `scenarios` has a test whose docstring names its id, and each passes.
- [ ] `docs/spec/sitrep.conformance.md` classifies these scenarios.
- [ ] Existing tests still pass.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed, including no co-author trailer.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
