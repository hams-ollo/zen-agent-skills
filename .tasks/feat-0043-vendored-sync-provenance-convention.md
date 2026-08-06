---
id: feat-0043
title: Establish a reproducible provenance convention for material folded in from upstream sources
type: feat
status: open
priority: P2
parent: "ROADMAP Epic B #18: provenance convention for folded-in material"
depends_on: []
touched_files:
  - AGENTS.md
  - NOTICE
  - docs/CATALOG.md
  - .agents/rules/review-quality.md
  - .agents/skills/spec-quality/SKILL.md
  - .agents/skills/spec-plan-readiness/SKILL.md
  - .agents/skills/test-quality/SKILL.md
  - .agents/skills/spec-conformance/SKILL.md
  - .agents/hooks/delegation-reminder.py
  - .agents/hooks/spec-conformance-gate.py
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
- Backfill provenance for the material already folded in, which is the seven files listed below.
- Extend `NOTICE` where the backfill turns up attribution that is currently thinner than it should
  be. One gap is already known: `NOTICE` lists
  [`delegation-reminder.py`](../.agents/hooks/delegation-reminder.py) under the hooks module and
  does not list [`spec-conformance-gate.py`](../.agents/hooks/spec-conformance-gate.py).
- Update [`docs/CATALOG.md`](../docs/CATALOG.md) where it describes what the kit borrows, so a reader
  browsing the catalog learns the convention exists.

**New files**, named here rather than in `touched_files` because `validate.py --strict` requires
every declared path to exist and these do not exist yet:

- `scripts/check-provenance.py`
- `tests/test_check_provenance.py`

**The seven backfill targets**, all already declared in `touched_files`:

| File | Current state |
|---|---|
| `.agents/skills/spec-quality/SKILL.md` | one-line body note plus a `license` field naming upstream, no digest or date |
| `.agents/skills/spec-plan-readiness/SKILL.md` | same |
| `.agents/skills/test-quality/SKILL.md` | same |
| `.agents/skills/spec-conformance/SKILL.md` | same |
| `.agents/rules/review-quality.md` | prose credit to upstream's composable quality lens, no digest or date |
| `.agents/hooks/delegation-reminder.py` | docstring credit, listed in `NOTICE`, no digest or date |
| `.agents/hooks/spec-conformance-gate.py` | docstring, **not listed in `NOTICE`** |

**Out of scope:**

- **`scripts/validate-skills.py`, absolutely.** Its `ALLOWED_FRONTMATTER_KEYS` is a six-key
  allow-list (`name`, `description`, `license`, `allowed-tools`, `metadata`, `compatibility`)
  deliberately mirroring Anthropic's own schema, and a seventh key added for this convention would
  be rejected by Anthropic's `quick_validate.py` even after the local validator is widened to accept
  it. Put a skill's provenance block in a **body footer**, or inside the existing `license` or
  `metadata` key. Do not edit the validator, and do not edit its allow-list.
- Automatic syncing. Upstream's script rewrites a marked region in place; this kit adapts rather than
  vendors verbatim (every fold-in was house-styled and retargeted), so an automatic overwrite would
  destroy the adaptation. Detect drift, report it, and let a human decide. This is the one place the
  upstream design should not be copied.
- Re-auditing whether past fold-ins were adapted correctly.
- Adding the check to required CI. It needs network access, and a check that fails when GitHub is
  slow will be disabled within a week. Make it runnable on demand and decide about CI later, with
  evidence.
- Any change to a skill body beyond adding its provenance footer, and any change to the four skills'
  actual instructions.

## Implementation notes

**Fetch with `urllib` and digest with `hashlib`. Never use a web-fetching agent tool.** A tool such
as `WebFetch` returns a model-summarized markdown conversion of the page rather than the bytes, so
its digest would be a digest of a summary: stable-looking, meaningless, and impossible to reproduce.
The digest must be taken over the exact bytes a plain HTTP GET returns. Network from a plain
`urllib` call is confirmed working from this repository: a real fetch of upstream's
`sync-maintainability-review.mjs` returned 4510 bytes.

Read upstream's script at
`https://raw.githubusercontent.com/moonray/repoprompt-workflows/main/scripts/sync-maintainability-review.mjs`
for the mechanism. It is Node; this kit is standard-library Python per the conventions section of
`AGENTS.md`, so port rather than adopt.

Digest the retrieved upstream content, not the adapted local file. The local file is expected to
differ, because adaptation is the point. What the digest answers is whether the thing we adapted
*from* has changed since we looked, which is the only question a drift check can honestly answer for
adapted material.

Where the provenance block lives should follow the file type: a Python hook can carry it in its
docstring, a skill in a body footer (**not** a new frontmatter key, per the scope exclusion above),
and a rules lens in prose. Do not invent a sidecar file format for this. Pick a placement that
`check-provenance.py` can parse and that a human reads without being told to.

Note during implementation that upstream's `maintainability-review` is itself synced from
`cursor/plugins`, so a provenance chain can be more than one hop. Decide whether the block records
the immediate source or the origin, and state the choice.

**Some sources will not be locatable, and that is a result, not a failure.** The four folded-in
skills were adapted from files in a vendored folder that is gone from the tree, so the exact upstream
path for each has to be found in upstream's current repository or recorded as unlocatable. Recording
"unlocatable" honestly is required by the acceptance criteria; guessing a plausible URL and digesting
whatever it returns is the specific failure this task exists to prevent.

## Risks and rollback

Touches more than one module (`scripts/`, `AGENTS.md`, `NOTICE`, `docs/CATALOG.md`, plus the seven
backfilled files), so the rule fires.

The risk is that the backfill produces confident-looking digests for content nobody actually
re-fetched, which would be worse than no provenance at all: a wrong digest reads as verified. Every
backfilled entry must be produced by an actual fetch at backfill time, with that day's date, and the
task should not claim provenance for anything whose upstream source cannot be located. Where the
original source is genuinely gone, record that plainly instead of guessing.

A second risk: this edits `AGENTS.md`, which every agent working in this repository reads first. A
change there governs every future agent, so keep the addition to the conventions section and change
no other section.

Rollback is a revert; nothing depends on the block being present.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/validate-skills.py && python .tasks/validate.py --strict

- [ ] The provenance convention is stated in the conventions section of `AGENTS.md`.
- [ ] `scripts/check-provenance.py` exits 0 when every recorded digest matches and non-zero on
      drift, with the drifted source named in its output.
- [ ] It is standard library only and degrades cleanly (non-zero with a clear message, not a
      traceback) when the network is unavailable.
- [ ] Tests cover the match, drift, and unreachable-source paths with a stubbed fetch rather than
      live network.
- [ ] All seven backfill targets in the Scope table carry a provenance block, or are recorded as
      unlocatable with that stated in the block.
- [ ] Every backfilled entry carries a retrieval date from the day the backfill ran, and every digest
      was produced by an actual `urllib` fetch on that day.
- [ ] Any source that could not be located is recorded as unlocatable rather than omitted.
- [ ] `NOTICE` lists `spec-conformance-gate.py`, closing the known gap.
- [ ] `scripts/validate-skills.py` exits 0 with no new errors or warnings, **and its
      `ALLOWED_FRONTMATTER_KEYS` is byte-identical to its current value**.
- [ ] `docs/CATALOG.md` tells a reader the convention exists.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only
      a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`, **with its relative links re-anchored for the
      extra directory level**; one dated line added to `CHANGELOG.md` referencing this task id.
