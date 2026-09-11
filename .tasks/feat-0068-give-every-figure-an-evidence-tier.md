---
id: feat-0068
title: Give every figure an evidence tier, and read declared figures from .sitrep.json
type: feat
status: open
priority: P2
parent: "ROADMAP Epic E #7d: project board"
depends_on: [feat-0067]
spec: docs/spec/sitrep.md
scenarios: [S-012, S-013, S-015, S-016, S-017, S-018, S-019, S-020]
touched_files:
  - .agents/skills/
  - tests/
  - docs/spec/sitrep.md
created: 2026-09-11
---

## Problem

The tier is the point of the board: a figure whose provenance is not shown reads as solid whatever it
rests on. The spec derives each tier mechanically from where a figure came from, and lets a repository
declare its own figures in a committed `.sitrep.json`.

## Scope

**In scope:** loading `.sitrep.json` with the four fields of the spec's surface; the `select` path with
its optional `[field=value]` filter; `count` (Purple) and `value` (Blue) over tracked JSON files; White
and the `untracked` label for anything untracked, pins included; Gold only when a tracked test file
contains the pinned name, and a downgrade plus notice when none does; hand-entered values as White with
their source; the lowest-tier rule for counts of entries; a notice, and no value, for a figure that
cannot be read. Wires `integration_branch` into `feat-0067`'s resolution.

This task extends `.agents/skills/sitrep/scripts/sitrep.py` and creates
`tests/test_sitrep_figures.py`.

**Out of scope:** YAML or any non-JSON source, which the spec excludes by naming JSON; rendering tiers
as colours (`feat-0070`).

## Implementation notes

- A tracked file is read at the current revision with `git show HEAD:<path>`, so an uncommitted edit
  does not change a Purple or Blue figure. An untracked file is read from the working tree and is
  White whatever it is declared as.
- A tracked test file is one the spec's term defines: a tracked file whose name starts with `test_` or
  contains `.test.` or `_test.`.
- The tier ranks White < Green < Blue < Purple < Gold, and a count of entries takes the minimum.
- Scenario layers: the selection, tier and count rules are unit tests; S-012, S-013, S-015, S-016 and
  S-017 run against a throwaway repository, because tracked-ness is a repository fact.

## Risks and rollback

Required: this introduces a persisted format, `.sitrep.json`, that repositories will commit.

- **What could go wrong.** A field shape chosen here and changed later breaks every repository that
  carries a configuration. Mitigation: the shape is the spec's surface table, field for field, and no
  field is added that the spec does not name.
- **Rollback.** Revert the one commit. No repository carries a `.sitrep.json` yet, so nothing depends on
  the format until the first one is committed.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_sitrep_figures.py" -v
    python scripts/run-checks.py

- [ ] Every scenario in `scenarios` has a test whose docstring names its id, and each passes.
- [ ] `docs/spec/sitrep.conformance.md` classifies these scenarios.
- [ ] Existing tests still pass.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed, including no co-author trailer.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
