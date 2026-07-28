---
id: bug-0007
title: Eight skill descriptions are not valid YAML and are rejected by any real parser
type: bug
status: open
priority: P0
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - .agents/skills/fix-batch/SKILL.md
  - .agents/skills/house-review/SKILL.md
  - .agents/skills/init-worktracking/SKILL.md
  - .agents/skills/new-task/SKILL.md
  - .agents/skills/project-bootstrap/SKILL.md
  - .agents/skills/reconcile-worktrees/SKILL.md
  - .agents/skills/spec-quality/SKILL.md
  - .agents/skills/test-quality/SKILL.md
  - scripts/validate-skills.py
  - tests/test_validate_skills.py
created: 2026-07-28
---

## Problem

Eight of the nineteen `SKILL.md` files have frontmatter that **no real YAML parser can read**. Their
`description` is a plain unquoted scalar containing a colon followed by a space, which YAML parses as
the start of a nested mapping:

```yaml
description: Scaffold a portable, agent-optimized spec-driven work-tracking system into the current repository: AGENTS.md (global rules ...
```

Every affected file fails identically at line 2, column 14:

    YAML parse error: Nested mappings are not allowed in compact mappings

The eight: `fix-batch`, `house-review`, `init-worktracking`, `new-task`, `project-bootstrap`,
`reconcile-worktrees`, `spec-quality`, `test-quality`.

**Found by running `npx skills` (vercel-labs/skills, `skills@1.5.20`) against this repository on
2026-07-28**, where all eight were skipped with that error and only eleven skills were discovered. The
rule was then verified mechanically against all nineteen: a plain scalar containing `": "` is rejected,
a block scalar (`>-`) is not, and that single rule explains every one of the nineteen outcomes with no
exceptions.

This is invisible to every gate the kit has, and the reason is the same one that produced `bug-0006`:
both `validate-skills.py` and `build-adapters.py` read frontmatter with a small regex parser that is
happy with anything of the shape `key: value`. The kit has therefore never once parsed its own
frontmatter the way a consumer does.

The blast radius is wider than one installer. Any harness or registry that reads `SKILL.md` with a real
YAML library sees eight malformed skills, and the failure is a skip, not a crash: the skill is simply
absent, with no signal to the person who installed it. `house-review` being among the eight is the
sharpest illustration, since it is also the skill that most depends on material it cannot carry.

## Scope

**In scope:** make all eight descriptions valid YAML, preserving their text exactly; add a check to
[`validate-skills.py`](../scripts/validate-skills.py) that fails on frontmatter no YAML parser would
accept, so this cannot recur; add covering tests.

**Out of scope:** rewording any description, which is `bug-0005`'s territory and already done. The
dangling-lens problem that the same investigation found, which is a separate and harder question (see
`chore-0020` and `feat-0034`). Adding a YAML dependency, which the standard-library-only constraint
forbids.

## Implementation notes

- **Two ways to fix the eight, and the choice matters.** Quoting the value (`description: "..."`) is
  the smaller diff. Converting to a block scalar (`description: >-` with the text indented below) is
  what the four already-valid multi-line descriptions do, keeps the line length readable, and cannot
  break again on a future edit that introduces a colon, a quote, or an apostrophe. Prefer the block
  scalar for consistency with the existing four, and because a quoted one-line description over 900
  characters is a single unreadable line that the next editor will fight.
- Note that `parse_frontmatter()` already strips the block-scalar indicator as of `feat-0032`, so
  converting a description to `>-` does not change what either script measures. That fix is a
  precondition for this one being safe.
- **The validator check is the point, not the eight fixes.** Without it this recurs the next time
  anyone writes a description containing `": "`, which is a natural thing to write. The constraint is
  that the kit is standard-library only, so it cannot import `yaml`. Two honest options:
  - Detect the specific construct: a plain (unquoted, non-block) scalar whose value contains `": "`.
    This is narrow, has no dependency, and covers the entire observed bug population. It will not
    catch every possible YAML error, and the check's message should say so rather than claim it
    validates YAML.
  - Require every multi-line-worthy field to be a block scalar or quoted, which is a house rule rather
    than a validity check.
  Prefer the first. Name it for what it is: a check for the one malformed-frontmatter construct that
  has actually shipped, not a YAML validator.
- **This needs a spec amendment, so it needs the author's explicit instruction before implementing.**
  A new check is a new scenario in [`docs/spec/validate-skills.md`](../docs/spec/validate-skills.md)
  (`S-019` is next), and that contract is human-owned. The eight description fixes do not need one.
- Re-run `npx skills add <this repo> --list` after fixing and confirm it discovers nineteen skills and
  skips none. That is the acceptance evidence no unit test can give, because the oracle is a third
  party's parser.

## Risks and rollback

Required: this touches eight shipped skills plus the validator.

The risk is a mechanical one. Converting a one-line scalar to a block scalar changes indentation, and
an under-indented continuation line silently truncates the description at the first line rather than
failing, which the length check would not catch because the result is still over `MIN_DESC_CHARS`.
Verify each converted description round-trips to the same string it had before, character for
character, rather than eyeballing the diff. Reverting is one commit.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [ ] All nineteen descriptions parse under a real YAML parser, proven by `npx skills add <repo> --list` discovering nineteen and skipping none.
- [ ] Each of the eight descriptions is character-for-character identical to its value before the change.
- [ ] `validate-skills.py` fails on a plain-scalar description containing `": "`, with a message that says what it checks and does not claim to validate YAML.
- [ ] The new test fails against the pre-fix validator.
- [ ] `python scripts/validate-skills.py` exits 0 with 19 skills, 0 errors, 0 warnings.
- [ ] `python -m unittest discover -s tests -p "test_*.py"` exits 0.
- [ ] `python scripts/build-adapters.py --dry-run` exits 0 with 38 adapter files.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in the `AGENTS.md` conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
