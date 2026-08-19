---
id: bug-0033
title: Three documents say touched_files may name a file the task will create, and the validator every repo runs rejects it
type: bug
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [chore-0040]
touched_files:
  - .agents/skills/new-task/SKILL.md
  - .tasks/README.md
  - .agents/skills/init-worktracking/templates/tasks-README.md.tmpl
  - .tasks/validate.py
  - .agents/skills/init-worktracking/templates/validate.py
  - tests/test_tasks_validate.py
created: 2026-08-18
---

## Problem

The `touched_files` contract is stated three times and contradicted by the code that enforces it.
Found 2026-08-18 while authoring [`feat-0049`](feat-0049-install-currency-reminder.md) with
`new-task`, which produced a task file that failed the repository's own acceptance command.

What the documents say:

| Where | Says |
|---|---|
| [`new-task`](../.agents/skills/new-task/SKILL.md) Step 3 | "If a test file does not exist yet, include the path it should be created at." |
| [`.tasks/README.md`](README.md) field table | "Every file the task expects to **create** or modify." |
| [`tasks-README.md.tmpl`](../.agents/skills/init-worktracking/templates/tasks-README.md.tmpl) field table | "Every file the task expects to **create** or modify." |

What [`validate.py`](validate.py) does, for any task not in `done/`:

```python
if not (REPO_ROOT / path).exists():
    warn(rel, f"touched_files path does not exist: {path}")
```

`warn` is a warning in the default mode and an **error** under `--strict`, and `--strict` is what the
`backlog` gate in [`run-checks.py`](../scripts/run-checks.py) runs. So in this repository, and in any
adopter's repository that wires the validator into CI the way the kit's own documentation
recommends, following the instruction in `new-task` produces a task file that fails the build.

The third row is the one that makes this worth fixing rather than shrugging at: that wording ships
into every repository `init-worktracking` scaffolds, alongside the validator that contradicts it.

The actual practice is the opposite of all three documents and nobody wrote it down.
[`feat-0046`](done/feat-0046-session-start-reachability-hook.md) created a hook and a test module and
listed neither in `touched_files`; [`feat-0045`](done/feat-0045-committed-acceptance-command.md)
created `scripts/run-checks.py` and listed only the two files it edited. Both passed. The convention
is real, it is load-bearing, and it exists only as a pattern in closed tasks.

## Scope

This task decides a question before it changes anything, and the decision is the deliverable as much
as the edit. **It was considered for [`chore-0040`](chore-0040-four-coherence-corrections-across-skill-bodies.md)
and kept separate on purpose**, because that task's stated premise is that none of its items carries a
design question and none changes behaviour. This one carries both.

**In scope:** decide which side is right, then make all four artefacts agree.

- If **the documents are right**, relax the existence check so a path that does not exist is not an
  error under `--strict`, in both validator copies, and keep some signal that catches a typo. The cost
  is that `--strict` stops distinguishing "I will create this" from "I misspelled this", which is the
  value the check currently has.
- If **the validator is right**, correct all three documents to say that `touched_files` carries paths
  that already exist, and say where a file the task will create belongs instead, which today is the
  Scope section. The cost is that an agent loses the one field that told it where to put a new file.

**Out of scope:**

- The `done/` exemption. The comment above the check explains why a closed task's paths are not
  verified, that reasoning is sound, and nothing here disturbs it.
- Any other `touched_files` rule. Emptiness, ordering, and the read/write-surface meaning are all
  unaffected.
- Adding a second frontmatter field for files to be created. That is a schema change, and this
  contradiction does not justify one.

## Implementation notes

Whichever way it goes, **both validator copies move together**. This is the exact drift class
[`bug-0026`](bug-0026-scaffolded-validator-lost-the-external-check.md) is filed against, and that task
asks for an assertion keeping the two copies' executable code in step. If `bug-0026` lands first, that
assertion should catch a one-sided change here; if this lands first, do not let it be the change that
proves the assertion was needed.

The prose branch is three edits and the two README field tables are the same sentence, so fix them as
one. Do not fix only `new-task`: its Step 3 line is the instruction an agent follows, but the field
tables are what a human reads, and leaving those saying "create" reproduces the confusion for the next
author.

A note on the evidence, in case it is tempting to treat the closed-task pattern as decisive: it shows
what authors did under a validator that punished the alternative, which is not the same as showing
what they wanted. Weigh the two costs above on their merits.

## Risks and rollback

Touches two skill-adjacent documents, a shipped template, both validator copies and a test module, so
the more-than-one-module rule fires.

The validator branch is where this can go wrong quietly. Relaxing an existence check makes the
validator pass in more cases, and a validator that stops catching something looks identical to one
that had nothing to catch. If that branch is taken, add a test that a genuinely misspelled path is
still reported by some means, and state in the closeout what signal replaced the one that was removed.

The prose branch cannot fail silently: the documents either say the right thing or they do not.

Reversible by reverting one commit. Nothing already scaffolded changes until its owner re-runs
`init-worktracking`.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [ ] The choice is recorded in this task's decisions section with the reason and the cost accepted.
- [ ] All four artefacts agree: `new-task` Step 3, both field tables, and the validator's behaviour.
- [ ] Both validator copies carry the same rule, proven by a test rather than by inspection.
- [ ] If the validator was relaxed: a misspelled `touched_files` path is still reported, proven by a
      test, and the closeout names the signal that replaced the removed one.
- [ ] If the documents were corrected: they name where a file the task will create should be recorded
      instead, and a task file naming only existing paths still passes `--strict`.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
