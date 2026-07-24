---
id: chore-0001
title: Fix README workflow-spine diagram, stale installer note, and broken link
type: chore
status: done
priority: P2
parent: "Phase A2 live run: dogfood fix-batch + reconcile-worktrees"
depends_on: []
touched_files:
  - README.md
created: 2026-07-24
---

## Problem

[README.md](../README.md) has three real inaccuracies: the "workflow spine" mermaid diagram is
in the wrong order (`new-task` before `init-worktracking`, and it omits `project-bootstrap`); the
Install section still says the installer "lands in Phase 3" though `scripts/install.py` is shipped;
and line 3 has a broken placeholder link `[Zen Solutions](https://github.com/)`.

## Scope

**In scope:** edit only `README.md` to (1) correct the spine diagram to
`project-bootstrap -> init-worktracking -> new-task -> fix-batch -> reconcile-worktrees ->
pr-describe`, (2) delete the stale "(Installer lands in Phase 3 ...)" parenthetical, (3) replace
the broken `[Zen Solutions](https://github.com/)` link with plain text `Zen Solutions`.

**Out of scope:** any other file; task-tracking bookkeeping (handled centrally during reconcile).

## Acceptance criteria (mechanically verifiable)

    grep -q "reconcile-worktrees" README.md && ! grep -q "lands in Phase 3" README.md

- [ ] Spine diagram reflects the real order and includes `project-bootstrap` and `pr-describe`.
- [ ] Stale installer note removed; broken placeholder link removed.
- [ ] No em-dashes; mermaid retained for the diagram.

## Definition of done

- [ ] Acceptance command passes locally.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated `CHANGELOG.md` line referencing this id.
