---
id: chore-0091
title: The .tasks/README.md frontmatter table omits the title row, which 21 of 22 open task files use
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - .tasks/README.md
created: 2026-09-01
---

## Problem

[`.tasks/README.md`](README.md) documents the task frontmatter with a field table. That table has no row
for `title`, and `title` is not an optional extra:

- Both task templates seed it. [`_TEMPLATE.md`](_TEMPLATE.md) line 3 and
  [`_TEMPLATE.md.tmpl`](../.agents/skills/init-worktracking/templates/_TEMPLATE.md.tmpl) line 3 both
  read `title: One-line imperative summary of the work`.
- 21 of the 22 open task files in this tree carry a `title:` row.
- The scaffold's own README copy,
  [`tasks-README.md.tmpl`](../.agents/skills/init-worktracking/templates/tasks-README.md.tmpl),
  **does** carry the row. So the two copies disagree, and this repository's is the one that is
  wrong.

So a reader of this repository's own tracker documentation sees a field table that omits a field
every task actually uses, while an adopter scaffolded by `init-worktracking` sees the complete one.

**Found by the independent verification of**
[`chore-0088`](done/chore-0088-both-readme-copies-enumerate-the-pre-cycle-check-set.md), which
compared the two README copies and separated genuine retargeting from drift. That task recorded all
four divergences as deliberate retargeting; the verifier established that three are and this one is
not, and the correction is recorded in that task's `## Decisions`. Filed here rather than left in an
archived task file, on the rule that a finding recorded only inside a closed task is a note in an
archive rather than a follow-up.

## Scope

**In scope:** the frontmatter table in `.tasks/README.md` documents `title`.

- Add the row, matching what the scaffold template's copy already says, so the two agree.
- Check the surrounding prose while you are there: if it enumerates the required fields anywhere
  else in the file, that enumeration has the same gap.

**Out of scope:**

- The scaffold template's copy. It is already correct, and the point of this task is that this
  repository's copy should match it rather than the reverse.
- The three genuine retargeting divergences between the two READMEs, which `chore-0088` names and
  which are deliberate.
- `validate.py`, which does not require `title` and is not being asked to. Whether it should is a
  separate question and nothing has asked it.
- Any other field, and any restructuring of the table.

## Implementation notes

Compose `doc-revise`: this is one row in one table, and the file's voice should not move.

The two README copies are deliberate near-duplicates that diverge on purpose in three named places.
Adding this row reduces the divergence to those three; do not treat the remaining three as a
to-do list while you are in the file.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] `.tasks/README.md`'s frontmatter table has a `title` row.
- [ ] `git grep -c "^| \`title\`" .tasks/README.md .agents/skills/init-worktracking/templates/tasks-README.md.tmpl`
      returns the same count for both files.
- [ ] The `doc links` gate passes, so no link was broken by the edit.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
