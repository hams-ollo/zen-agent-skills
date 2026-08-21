---
id: bug-0031
title: doc-sync prescribes a link check that cannot see the documents doc-sync edits, so it passes having checked nothing
type: bug
status: done
priority: P2
parent: "ROADMAP Kit coherence hardening (2026-08-18 review pass)"
depends_on: []
touched_files:
  - .agents/skills/doc-sync/SKILL.md
created: 2026-08-18
---

## Problem

[`doc-sync`](../../.agents/skills/doc-sync/SKILL.md) closes by telling the agent to "run the repository's
own link checker over the edited document (in this kit, `python .tasks/validate.py --strict`, which
resolves every relative ...)".

That command cannot see the edited document. The default mode of
[`validate.py`](../validate.py) walks `.tasks/` and nothing else:

```python
def markdown_files():
    """Every Markdown file under .tasks/, not only the task files.
    ...
    """
    return sorted(TASKS_DIR.rglob("*.md"))
```

The documents `doc-sync` classifies as current-state and therefore edits are `README.md` and
`docs/*.md`. So the prescribed command walks a directory `doc-sync` did not touch, reports clean, and
says nothing about the file that just changed. The correct invocation is the `--links <patterns>` mode
that `chore-0029` added for exactly this purpose, and which the CI gate already uses.

The same sentence carries a second, smaller error: it attributes link resolution to `--strict`. The
module docstring says links are always checked and `--strict` only adds `touched_files` existence.

This is the failure signature this kit names as its own enemy, and it is worse here than elsewhere
because of where it sits. `doc-sync`'s whole purpose is to catch documentation that stopped matching
reality, and its final verification step is itself a check that passes without checking. A broken link
introduced by a `doc-sync` edit is exactly what this step exists to catch and exactly what it cannot
see.

## Scope

**In scope:** correct the prescribed command to the `--links` form with the edited document's path, and
correct the `--strict` attribution.

**Out of scope:**

- `validate.py`. Both modes work as documented; only the instruction naming them is wrong. The related
  `--links` guard defect is [`chore-0032`](../chore-0032-links-guard-fires-per-run-not-per-pattern.md) and
  is independent.
- Any other step in `doc-sync`.
- Making `doc-sync` run the checker itself. It reports and, with per-finding approval, edits; the
  instruction shape is right.

## Implementation notes

Write the invocation so it survives being read in a repository that is not this one. The sentence's
"(in this kit, ...)" parenthetical is the established shape for that and should stay: the general
instruction is to run the repository's link checker over the edited path, and this kit's spelling is
the example. Give the example with a path placeholder rather than a literal file, so it cannot be
copied verbatim into a run that edited something else.

`chore-0032` is open against the `--links` guard, and this task should not wait for it: an instruction
naming the right mode is strictly better than one naming a mode that cannot work, even while that mode
has its own bug.

## Decisions

- **Rejected: restating in the skill what `--strict` actually does.** Correcting the misattribution
  could have been done by saying `--strict` adds the `touched_files` existence check rather than the
  link check. That imports one repository's validator semantics into a portable skill body, so the
  sentence drops `--strict` entirely and keeps a general clause (this checker's other modes walk the
  tracker directory only) that carries the lesson without the local detail.
- **Seam left open: the newly prescribed mode has its own open bug.** `doc-sync` now names `--links`
  while [`chore-0032`](../chore-0032-links-guard-fires-per-run-not-per-pattern.md) is open against that
  mode's no-match guard. Deliberate per this task's scope, not an oversight for the next agent to
  close here.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] `doc-sync` names `python .tasks/validate.py --links <path>` (or the repository's equivalent) over
      the edited document, with a placeholder rather than a literal path.
- [x] The sentence no longer attributes relative-link resolution to `--strict`.
- [x] The prescribed command, run against a document `doc-sync` would edit, reports on that document:
      demonstrated by running it against `README.md` and confirming a non-zero document count.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
