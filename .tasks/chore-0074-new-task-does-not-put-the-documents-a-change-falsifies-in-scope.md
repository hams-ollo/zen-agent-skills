---
id: chore-0074
title: Four tasks in one session scoped an edit without the conformance matrix or contract that quotes it, and the authoring bar says nothing about it
type: chore
status: open
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: []
touched_files:
  - .agents/skills/new-task/SKILL.md
created: 2026-08-28
---

## Problem

`new-task` sets the bar for a task file: honest `touched_files`, a real `parent`, resolved
`depends_on`, a mechanically-verifiable acceptance command. **It says nothing about the documents a
change falsifies**, and on 2026-08-27 and 2026-08-28 that gap produced four tasks in one session, each
scoped to edit something a conformance matrix quotes or a contract pins, with that document absent
from `touched_files`.

| Task | What it scoped | What it falsified and did not declare |
|---|---|---|
| `chore-0065` | A scenario and the `Output` surface element | An observation in `cloud-executable.conformance.md` that its Scope named but its frontmatter did not |
| `chore-0045` | Retagging two test docstrings | The `S-018` and `S-022` matrix rows that quote those docstrings, one of which names `chore-0045` as the follow-up that would |
| `chore-0073` | Retagging three more, and a count in one row | The `S-023` row's "the gap is still open", which the retag makes false |
| `chore-0049` | Adding an eighth gate | The `Gate set` surface element pinning "the seven currently in `checks.yml`", enumerated by name, in an **approved** contract |

Three were caught at dispatch by a dispatcher who happened to check. The fourth was not: its agent
found the contract itself, mid-run, and stopped. That is the honest-blocker instruction working, and
it is the expensive way to learn something a task file could have carried from the start.

**The gap is invisible to every existing check.** `validate.py --strict` verifies that a declared path
exists, not that a scoped edit is declared, so a task that will falsify a document it never names
passes validation and reads as complete. The failure surfaces at reconciliation, or in CI, or in a
matrix that quietly asserts a state the same commit removed.

**The class is one this repository already understands from the other end.** `bug-0037` moved
conformance citations off line numbers because a pointer that encodes position drifts; `chore-0068`
repointed seven citations naming a function that was renamed. Both are the pointer going stale
because the target moved. This is the same failure a step earlier: the person moving the target does
not know a pointer exists.

## Scope

**In scope:** state the rule in [`new-task`](../.agents/skills/new-task/SKILL.md).

- **The rule, in the authoring bar beside honest `touched_files`**: when a task edits code, prose, or a
  docstring that a conformance matrix quotes or an approved contract pins, those documents are part of
  its `touched_files` by construction, and reconciling them is part of its scope rather than a
  follow-up.
- **Say how to find them**, because the rule is useless without it. Grep the matrices for the symbol,
  the test class, or the quoted phrase the change touches, before writing `touched_files`. That is one
  command and it is the whole technique.
- **Carry the disposition the kit already settled**: re-derive the row's verdict before moving its
  citation, per `chore-0062`, `chore-0068` and `chore-0045`. A citation repaired without re-deriving
  what it supports asserts a freshness the repair did not establish.
- **Name the counter-rule too.** A dated measurement is a record, not a claim, and must not be
  rewritten when the thing it measured changes. Getting this wrong in the other direction falsifies
  history, which is worse than a stale pointer.

**Out of scope:**

- **Building a check for it.** Whether a task's `touched_files` covers what its edits falsify is not
  decidable before the edit exists, and the nearest decidable thing, the citation checker, is
  [`chore-0049`](done/chore-0049-a-checker-for-conformance-matrix-citations.md). This task writes a rule
  into an authoring skill; it does not add a gate.
- `AGENTS.md`'s task lifecycle, which was considered and declined: the rule is about authoring a task
  rather than closing one, and two open tasks already contend for that file. If it belongs there as
  well, that is a finding to report.
- The four tasks in the table. Three are closed with their scopes corrected and `chore-0049` was
  corrected at dispatch; this task does not reopen them.
- `init-worktracking`'s scaffolded template, which does not carry the authoring bar.

## Implementation notes

`new-task` is a workflow skill, so the rule belongs in its procedure where `touched_files` is
authored, not in a new section appended to the end. Read how the existing bar states its other
requirements and match that shape.

Keep it short. The skill is 500 lines at the ceiling `validate-skills.py` enforces, so check the
current length before adding, and if the rule does not fit, that is itself worth reporting rather
than silently pushing a body over the bar.

The four rows above are the citation. Do not restate the whole table in the skill; one sentence naming
the class and one naming the technique is what an author needs at the moment they are writing
`touched_files`.

## Risks and rollback

One skill body, prose only, so this section is short.

The risk is a rule stated so broadly that every task declares every matrix, which would make
`touched_files` meaningless in the other direction. The guard: the rule is about documents that quote
or pin **the thing being edited**, and the grep is what decides it, so the test is mechanical rather
than a judgment about relevance.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] `new-task`'s authoring bar states the rule, names the grep that finds the affected documents,
      and names the re-derive disposition and the dated-measurement counter-rule.
- [ ] The rule sits where `touched_files` is authored rather than in an appended section.
- [ ] `new-task/SKILL.md` is still under the enforced body-length ceiling, and the closeout states the
      line count before and after.
- [ ] No file under `scripts/`, `tests/`, or `docs/spec/` is modified.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
