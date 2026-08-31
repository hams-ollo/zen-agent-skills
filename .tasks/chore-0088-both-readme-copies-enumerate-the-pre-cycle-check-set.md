---
id: chore-0088
title: Both README copies enumerate the validator's checks and omit cycle detection, so a scaffolded adopter gets the check with nothing explaining it
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [bug-0061]
touched_files:
  - .tasks/README.md
  - .agents/skills/init-worktracking/templates/tasks-README.md.tmpl
created: 2026-08-31
---

## Problem

[`bug-0061`](done/bug-0061-the-strict-backlog-gate-accepts-a-dependency-cycle.md) adds cycle detection to
both copies of the validator. One sentence describes what that validator checks, and it exists
verbatim and identically in two files, [`.tasks/README.md`](README.md) line 25 and
[`tasks-README.md.tmpl`](../.agents/skills/init-worktracking/templates/tasks-README.md.tmpl) line
25:

> It verifies frontmatter schema, id uniqueness, that every `depends_on` resolves to a real task,
> that every relative markdown link resolves from the directory the file is actually in, and (with
> `--strict`) that every `touched_files` path exists.

After `bug-0061` that enumeration is incomplete in both copies.

**This is the `bug-0026` shape, one layer out.** `bug-0061` exists because a check landed in one
copy of a two-copy tool and not the other. The residual is the same asymmetry between the check and
the thing explaining it: an adopter scaffolded by `init-worktracking` receives a validator that
fails their backlog on a dependency cycle, and a README that does not mention cycles at all, so the
first time it fires the message arrives with no documentation behind it.

Both files are outside `bug-0061`'s `touched_files`, so its agent correctly recorded the finding
rather than reaching for it, per `A2`. This task is that finding filed, because a finding recorded
only inside a task file about to move to `.tasks/done/` is a note in an archive rather than a
follow-up.

## Scope

**In scope:** both sentences describe what the validator actually checks.

- Extend the enumeration in both copies to include the cycle check.
- Keep the two sentences saying the same thing. They are deliberate near-duplicates for the same
  reason the validators are: a scaffolded repository cannot read this one.
- Check the surrounding paragraph in each file while you are there, since the template's is written
  for a scaffolded repository and this one's is written for this repository, and the retargeting has
  to survive the edit.

**Out of scope:**

- Any code. Both validators are correct as of `bug-0061`; this is documentation catching up.
- The module docstrings in either validator, which `bug-0061` already updated in both copies.
- Rewriting either README more broadly, or reconciling any other difference between the two.
- Building a mechanism that keeps the prose and the checks in sync automatically. That is the
  drift-sensor question at `ROADMAP.md` Epic B item 19 and it is much larger than this.

## Implementation notes

Compose `doc-revise` rather than rewriting: the instruction is to change one clause in a sentence
and leave the voice alone, which is exactly what that skill is for.

`.tasks/README.md` links resolve from `.tasks/`, and the template's resolve from wherever
`init-worktracking` places it. Do not copy a link from one into the other.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] `git grep -n "id uniqueness" -- .tasks/README.md .agents/skills/init-worktracking/templates/`
      returns two lines, and both now name the cycle check.
- [ ] The two sentences still say the same thing as each other, confirmed by reading them side by
      side, with only the deliberate this-repository versus scaffolded-repository retargeting
      differing.
- [ ] The `doc links` gate passes, so no link was broken by the edit.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
