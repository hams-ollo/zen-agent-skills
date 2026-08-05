---
id: feat-0043
title: Establish a reproducible provenance convention for material folded in from upstream sources
type: feat
status: open
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: []
touched_files:
  - AGENTS.md
  - NOTICE
  - docs/CATALOG.md
created: 2026-08-05
---

## Problem

A meaningful share of this kit came from somewhere else. Four skills were folded in from Balarama
Bosch's [repoprompt-workflows](https://github.com/moonray/repoprompt-workflows) (MIT), the review
lens derives from it, and the hooks module in `feat-0038` and `feat-0039` adds more. The kit records
that in prose: a ROADMAP line says "folded in from `repoprompt-workflows`, house-styled", and
`NOTICE` carries the license. What it does not record is *which version* of upstream anything came
from, or whether upstream has changed since.

That gap has already produced a wrong claim in this repository's own history. The ROADMAP line for
`doc-sync` originally credited an upstream `document` workflow. It had to be corrected, because no
such skill was ever vendored here, and the only surviving trace of the contract was a single
instruction at `repoprompt-workflows-main/.agents/workflows/Loop.md:194`. The vendored folder was
gitignored and is now gone from the working tree entirely, so that citation can no longer be checked
against anything local. Attribution decayed into folklore in under two weeks.

Upstream solves this for its own vendored lens with `scripts/sync-maintainability-review.mjs`, which
records a SHA256 digest of the upstream content, a `retrieved:` date, delimits the synced region with
do-not-edit markers, and exits non-zero when upstream has drifted from the recorded digest. The
mechanism is small and it makes three questions answerable that are currently guesses: where did this
come from, what exactly did we take, and has it changed.

## Scope

**In scope:**

- Define a provenance block for any file or region adapted from an external source: source URL,
  license, author, retrieval date, and a SHA256 digest of the retrieved content.
- Write the convention into the conventions section of `AGENTS.md`, so it binds future fold-ins
  rather than only documenting past ones.
- Add a `scripts/check-provenance.py` that re-fetches each recorded source, compares the digest, and
  exits non-zero on drift, so upstream movement is a check result rather than a discovery.
- Backfill provenance for the material already folded in: the four Phase 1 lenses, the review lens,
  and whatever the hooks tasks land.
- Extend `NOTICE` where the backfill turns up attribution that is currently thinner than it should
  be.

New file: `scripts/check-provenance.py`.

**Out of scope:**

- Automatic syncing. Upstream's script rewrites a marked region in place; this kit adapts rather than
  vendors verbatim (every fold-in was house-styled and retargeted), so an automatic overwrite would
  destroy the adaptation. Detect drift, report it, and let a human decide. This is the one place the
  upstream design should not be copied.
- Re-auditing whether past fold-ins were adapted correctly.
- Adding the check to required CI. It needs network access, and a check that fails when GitHub is
  slow will be disabled within a week. Make it runnable on demand and decide about CI later, with
  evidence.

## Implementation notes

Read upstream's script at
`https://raw.githubusercontent.com/moonray/repoprompt-workflows/main/scripts/sync-maintainability-review.mjs`
for the mechanism. It is Node; this kit is standard-library Python per the conventions section of
`AGENTS.md`, so port rather than adopt.

Digest the retrieved upstream content, not the adapted local file. The local file is expected to
differ, because adaptation is the point. What the digest answers is whether the thing we adapted
*from* has changed since we looked, which is the only question a drift check can honestly answer for
adapted material.

Where the provenance block lives should follow the file type: a Python hook can carry it in its
docstring, a skill in its frontmatter or a footer, and a rules lens in prose. Do not invent a
sidecar file format for this. Pick a placement that `check-provenance.py` can parse and that a human
reads without being told to.

Note during implementation that upstream's `maintainability-review` is itself synced from
`cursor/plugins`, so a provenance chain can be more than one hop. Decide whether the block records
the immediate source or the origin, and state the choice.

## Risks and rollback

Touches more than one module (`scripts/`, `AGENTS.md`, `NOTICE`, plus the backfilled files), so the
rule fires.

The risk is that the backfill produces confident-looking digests for content nobody actually
re-fetched, which would be worse than no provenance at all: a wrong digest reads as verified. Every
backfilled entry must be produced by an actual fetch at backfill time, with that day's date, and the
task should not claim provenance for anything whose upstream source cannot be located. Where the
original source is genuinely gone, record that plainly instead of guessing.

Rollback is a revert; nothing depends on the block being present.

## Acceptance criteria (mechanically verifiable)

    python scripts/check-provenance.py && python -m unittest discover -s tests -p "test_*.py" -v && python .tasks/validate.py --strict

- [ ] The provenance convention is stated in the conventions section of `AGENTS.md`.
- [ ] `scripts/check-provenance.py` exits 0 when every recorded digest matches and non-zero on
      drift, with the drifted source named in its output.
- [ ] It is standard library only and degrades cleanly (non-zero with a clear message, not a
      traceback) when the network is unavailable.
- [ ] Tests cover the match, drift, and unreachable-source paths with a stubbed fetch rather than
      live network.
- [ ] Every backfilled entry carries a retrieval date from the day the backfill ran.
- [ ] Any source that could not be located is recorded as unlocatable rather than omitted.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
