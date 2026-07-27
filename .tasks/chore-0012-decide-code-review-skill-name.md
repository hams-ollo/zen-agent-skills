---
id: chore-0012
title: Decide whether the code-review skill keeps a name that collides with Claude Code's built-in
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A #8: kit-wide skill evaluation"
depends_on: []
spec: ""
scenarios: []
touched_files:
  - .agents/skills/code-review/SKILL.md
  - docs/CATALOG.md
  - README.md
created: 2026-07-27
---

## Problem

The kit's review skill is named `code-review`, and [`scripts/install.py`](../scripts/install.py)
places it at `~/.claude/skills/code-review/`. Claude Code already ships a built-in `/code-review`
command. The skill body currently resolves the collision by asserting it three times in prose:

> Distinct from Claude Code's built-in `/code-review` command.

A skill body cannot resolve a namespace collision by describing it. A user who types `/code-review`
gets whichever the harness resolves first, and the kit has no say in that. This is the kit's most
visible review surface, so an ambiguous invocation is a poor first impression for an adopter.

This is filed rather than fixed because renaming is a judgment the kit owner makes, not a mechanical
correction. It changes an installed skill name the author already has muscle memory for, and it
touches the reader-facing catalog.

## Scope

**In scope:** decide between the three options below, then apply the decision consistently across
the skill directory name, its `name:` frontmatter, and every reference to it in the docs.

- **Keep `code-review`** and accept the ambiguity, deleting the three "distinct from" assertions
  since they do not accomplish anything.
- **Rename** to something unambiguous (`house-review` and `zen-review` are the obvious candidates,
  and the first travels better for an adopter who is not Zen Solutions).
- **Rename and add an alias note** so existing muscle memory still finds it.

**Out of scope:** the review rubric itself, the `review-quality` lens, and the deferred multi-lens
`deep-review` direction noted in the skill. Any other skill's name.

## Implementation notes

If the decision is to rename, the sibling-link check in
[`scripts/validate-skills.py`](../scripts/validate-skills.py) catches stale
`../code-review/SKILL.md` references automatically, so the acceptance command below covers most of
the rename's blast radius. It does not cover prose mentions that are not links; grep for those.

Note that `~/.claude/skills/code-review/` may already exist from a previous install. A rename means
the old directory is left behind by `install.py`, since the manifest keys on the target path. Run
`python scripts/install.py --uninstall` before re-installing under the new name.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py && python -m unittest discover -s tests -p "test_*.py"

- [ ] A decision is recorded in the skill body or in `ROADMAP.md`, with its reason.
- [ ] If renamed: directory name, `name:` frontmatter, and every doc reference agree.
- [ ] If kept: the three "distinct from the built-in" assertions are removed as ineffective.
- [ ] `docs/CATALOG.md` and `README.md` name the skill the same way the directory does.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
