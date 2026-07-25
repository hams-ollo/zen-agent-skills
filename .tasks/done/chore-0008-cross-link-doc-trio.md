---
id: chore-0008
title: Cross-link doc-author and doc-revise to doc-sync
type: chore
status: done
priority: P2
parent: "ROADMAP Kit hardening (2026-07-25 review pass)"
depends_on: []
touched_files:
  - .agents/skills/doc-author/SKILL.md
  - .agents/skills/doc-revise/SKILL.md
created: 2026-07-25
---

## Problem

The documentation trio only links in one direction.
[`doc-sync`](../../.agents/skills/doc-sync/SKILL.md) positions itself against both siblings and composes
`doc-revise` by reference, but neither
[`doc-author`](../../.agents/skills/doc-author/SKILL.md) nor
[`doc-revise`](../../.agents/skills/doc-revise/SKILL.md) mentions `doc-sync` at all (`grep -c doc-sync`
returns 0 for both).

Each already redirects to the other for the case it does not handle: `doc-author` says to use
`doc-revise` when the document exists, and `doc-revise` says to use `doc-author` when it does not.
Neither covers the third case, which is now built: the user does not yet know **which** document is
wrong. An agent reading `doc-revise` and asked "are our docs still accurate?" has no pointer to the
skill that answers it.

`doc-sync` also composes `doc-revise`'s editing discipline when it applies an approved correction, so
`doc-revise` is load-bearing for a skill that does not appear anywhere in its text.

## Scope

**In scope:** add a reference to `doc-sync` in both files, in each file's own voice, covering the
case each one does not handle: detecting which documents drifted. In `doc-revise`, also note that
`doc-sync` composes its editing discipline when applying an approved correction, so a future editor
knows the file has a downstream consumer.

**Out of scope:** any restructuring of either skill. Both are deliberately short (41 and 32 lines);
do not pad them or retrofit the `When to use` / `When not to use` section shape, which is a separate
open decision on the roadmap. Changing `doc-sync`.

## Implementation notes

- Follow [`doc-revise`](../../.agents/skills/doc-revise/SKILL.md) itself: smallest sufficient change,
  preserve voice. One or two sentences per file is the right size.
- `doc-author`'s natural home is its opening paragraph, which already carries the "when the document
  already exists, use `doc-revise`" redirect.
- `doc-revise`'s natural home is its opening paragraph for the redirect, and either that paragraph or
  the `Verify links after any structural change` section for the composition note.
- Use relative links in the established form the sibling skills already use, pointing at
  `../doc-sync/SKILL.md` from inside a skill directory.
- Consider whether either skill's frontmatter `description` should mention `doc-sync`, since the
  descriptions are what drive triggering. Both descriptions already name their sibling, so adding the
  third is consistent. Optional, but preferred if it fits without bloating the field.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [x] `grep -c doc-sync .agents/skills/doc-author/SKILL.md` returns at least 1.
- [x] `grep -c doc-sync .agents/skills/doc-revise/SKILL.md` returns at least 1.
- [x] `doc-revise` states that `doc-sync` composes its editing discipline.
- [x] Every relative markdown link added resolves to a file that exists.
- [x] `python scripts/validate-skills.py` exits 0 with 19 skills and no new warnings.
- [x] `python -m unittest discover -s tests -p "test_*.py"` exits 0.
- [x] Neither file grows by more than a few lines; no section is added or removed.
- [x] No em-dashes; headings sentence case.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in the `AGENTS.md` conventions section followed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
