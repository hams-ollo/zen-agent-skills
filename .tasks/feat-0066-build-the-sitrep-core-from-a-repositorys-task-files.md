---
id: feat-0066
title: Build the sitrep core, what waits on the person and what is blocked, from a repository's task files
type: feat
status: open
priority: P2
parent: "ROADMAP Epic E #7d: project board"
depends_on: []
spec: docs/spec/sitrep.md
scenarios: [S-001, S-002, S-003, S-004, S-005, S-006, S-007, S-010, S-014]
touched_files:
  - .agents/skills/
  - tests/
  - docs/spec/sitrep.md
created: 2026-09-11
---

## Problem

[`docs/spec/sitrep.md`](../docs/spec/sitrep.md) is approved and nothing implements it. This task
builds the layer every other scenario sits on: reading a repository's tracked task files and deciding
which tasks wait on the person, which are blocked, and in what order they are listed.

## Scope

**In scope:** the waiting-on-you rules (an open question with no decision below it, a decision above a
newer question, a decision below a question, work held for a human eye, a closed task never waiting),
priority ordering, blocked tasks, the `no task tracking` notice, and Green task entries naming their
file.

Files this task creates, with their exact paths:

- `.agents/skills/sitrep/SKILL.md`: the skill, carrying `metadata.status: draft` from its first
  commit, referencing both universal lenses, and describing only what this task delivers.
- `.agents/skills/sitrep/scripts/sitrep.py`: the board, standard library only.
- `tests/test_sitrep_board.py`: one test per scenario above, its `S-NNN` id in the docstring.

**Out of scope:** git-derived in-flight work and changes (`feat-0067`), declared figures and every
tier other than Green (`feat-0068`), the watermark (`feat-0069`), the text, page and document
renderings (`feat-0070`), and the session-start hook (`feat-0071`).

## Implementation notes

- Read only files `git ls-files .tasks` reports, so an untracked task file is not state.
- Parse frontmatter by regex, as `.tasks/validate.py` does, since this root has no YAML parser.
- Heading rules are the spec's Proposed Surface verbatim: a level-two heading whose text begins
  `Open question` or `Decision`, compared by position in the body; any heading containing `held open
  for a human eye`, in any case. A task under `.tasks/done/` is closed whatever its body says.
- Priority orders P1 first; a missing or unrecognised priority sorts after every known one; ties go by
  id.
- Tests build throwaway git repositories under a temporary directory and import the script by path
  with `importlib.util.spec_from_file_location`, the pattern `tests/test_hooks.py` uses for
  `install.py`.
- Scenario layers: the heading and ordering rules are unit tests over task text; S-005, S-007 and
  S-010 run against a temporary repository, because tracked-ness and `.tasks/done/` are repository
  facts.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_sitrep_board.py" -v
    python scripts/run-checks.py

- [ ] Every scenario in `scenarios` has a test whose docstring names its id, and each passes.
- [ ] `validate-skills.py` accepts the new skill with its draft marker, and the install dry run
      places it under no profile.
- [ ] `docs/spec/sitrep.conformance.md` is created, classifying this task's scenarios and recording
      the rest as not built.
- [ ] Existing tests still pass.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed, including no co-author trailer.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
