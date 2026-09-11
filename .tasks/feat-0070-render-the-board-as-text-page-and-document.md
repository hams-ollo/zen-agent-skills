---
id: feat-0070
title: Render the board as the text sitrep, the page, and the versioned document
type: feat
status: open
priority: P2
parent: "ROADMAP Epic E #7d: project board"
depends_on: [feat-0069]
spec: docs/spec/sitrep.md
scenarios: [S-028, S-033, S-034, S-035, S-036, S-037, S-038]
touched_files:
  - .agents/skills/
  - tests/
  - docs/spec/sitrep.md
created: 2026-09-11
---

## Problem

Everything before this task builds a board nobody can see. This task gives it the three forms the
spec's command table names, and holds the properties that make the board safe to run anywhere: it
changes nothing in the repository and needs no network.

## Scope

**In scope:** the command `sitrep` and its flags `--json`, `--html <path>` and `--since <rev>`; the
text sitrep with its sections in the spec's order and a display limit of five with a "how many more"
line; the page, on two colour axes that never share a role, with every figure showing its value, tier
name and colour, and provenance; exactly one file written, at the named path; nothing in the working
tree, index, refs or history changed; no network connection opened; the JSON document with
`schema_version: 1` and every field of the spec's surface table, carrying the same content the page
shows.

This task extends `.agents/skills/sitrep/scripts/sitrep.py` and `.agents/skills/sitrep/SKILL.md`, and
creates `tests/test_sitrep_outputs.py`.

**Out of scope:** the session-start mode and the reporting rules (`feat-0071`).

## Implementation notes

- The tier colours follow the gear-rarity ladder in both light and dark themes, and the status colours
  are a separate set. A test asserts the two sets are disjoint, so a status can never be drawn in a tier
  colour.
- The page is one self-contained HTML file with inline CSS, and fetches nothing at render or view time.
- S-037 is tested by replacing `socket.socket` with a function that raises, then generating a board in
  every form.
- S-036 compares `git status --porcelain`, `git for-each-ref`, and the index's bytes before and after.
- Scenario layers: text truncation and the colour sets are unit tests; the page, the document, read-only
  and offline run the command against a throwaway repository.

## Risks and rollback

Required: the board document is a format a later cross-project view will read, which makes it a
protocol.

- **What could go wrong.** A field renamed after a consumer exists breaks that consumer silently.
  Mitigation: `schema_version` starts at 1, and the fields are exactly the spec's surface table.
- **Rollback.** Revert the one commit. Nothing consumes the document yet.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_sitrep_outputs.py" -v
    python scripts/run-checks.py

- [ ] Every scenario in `scenarios` has a test whose docstring names its id, and each passes.
- [ ] `--since` reaches `feat-0069`'s override, and the stored watermark is unchanged after it.
- [ ] `docs/spec/sitrep.conformance.md` classifies these scenarios.
- [ ] Existing tests still pass.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed, including no co-author trailer.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
