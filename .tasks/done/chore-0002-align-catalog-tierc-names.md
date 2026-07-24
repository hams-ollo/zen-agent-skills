---
id: chore-0002
title: Align docs/CATALOG.md Tier C Content OS names with ROADMAP Epic C
type: chore
status: done
priority: P2
parent: "Phase A2 live run: dogfood fix-batch + reconcile-worktrees"
depends_on: []
touched_files:
  - docs/CATALOG.md
created: 2026-07-24
---

## Problem

[docs/CATALOG.md](../docs/CATALOG.md) Tier C lists the Content OS pipeline skills as
`produce, cut, clips, edit, brief, idea-discovery`, which disagrees with the canonical list in
[ROADMAP.md](../ROADMAP.md) Epic C (`produce, clip-machine, repurpose, video-editing,
video-cutting, episode-brief, youtube-transcript, idea-discovery`). The two documents should agree.

## Scope

**In scope:** edit only `docs/CATALOG.md`; replace the Tier C skill-name list with the canonical
eight names from ROADMAP Epic C, each in backticks, keeping the surrounding sentence intact.

**Out of scope:** any other file; ROADMAP itself (it is canonical); task-tracking bookkeeping.

## Acceptance criteria (mechanically verifiable)

    grep -q "clip-machine" docs/CATALOG.md && grep -q "youtube-transcript" docs/CATALOG.md

- [ ] Tier C list matches ROADMAP Epic C exactly (eight names, backticked).
- [ ] No em-dashes; surrounding prose intact.

## Definition of done

- [ ] Acceptance command passes locally.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated `CHANGELOG.md` line referencing this id.
