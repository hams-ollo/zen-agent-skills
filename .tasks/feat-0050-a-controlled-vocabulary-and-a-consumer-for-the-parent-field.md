---
id: feat-0050
title: The parent field has 41 spellings and no consumer, so the Feature altitude the work model defines is unreadable
type: feat
status: open
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: []
touched_files:
  - .tasks/validate.py
  - .tasks/_TEMPLATE.md
  - tests/test_tasks_validate.py
created: 2026-08-27
---

## Problem

`AGENTS.md` defines four altitudes, Epic to Feature to Task to acceptance, and says a task file "is the
1,000-foot decomposition of one roadmap Feature; its `parent:` links back up".
[`validate.py`](validate.py) requires `parent` to be **present** and never checks its **value**.

Measured 2026-08-27 across 161 task files:

```text
41 distinct parent strings, for five epics and three review-pass sections

  33x  "ROADMAP Epic A: broadly shareable (the public kit)"
  14x  "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
  11x  "ROADMAP Epic A: distribution tooling"      <- names no heading in ROADMAP.md
   3x  "ROADMAP Epic B: contract-driven delivery"  <- same epic, second spelling
   5x  "ROADMAP#tooling install.py"                <- abandoned format
   1x  "ROADMAP#N feature-slug"                    <- _TEMPLATE.md's own placeholder
```

`grep "distribution tooling" ROADMAP.md` returns nothing. That value has propagated by copy-paste since
at least `chore-0015`, and it was reproduced twice more during the 2026-08-27 waves by an agent copying
a neighbouring task's frontmatter rather than checking it against the roadmap. Wave 13 corrected the two
open tasks; nine closed ones still carry it.

**The deeper defect is not the typo.** Of the nine open tasks on 2026-08-27, **one** named a
Feature-level parent. The other eight named only an epic, so the 10,000-foot altitude is empty for them
and nothing can answer "which tasks build toward Feature X".

**Why this axis rotted and the sibling axis did not.** The `spec:` and `scenarios:` fields link a task
to a contract and its `S-NNN` ids, and they have not drifted, because
[`spec-plan-readiness`](../.agents/skills/spec-plan-readiness/SKILL.md) and
[`spec-conformance`](../.agents/skills/spec-conformance/SKILL.md) read them. A pointer with a consumer
gets corrected when the consumer breaks. A pointer with no consumer is prose.

## Scope

**In scope:** give `parent` a closed vocabulary, a check, and a reader.

- **A vocabulary derived from `ROADMAP.md` itself**, not a second list beside it. The headings and the
  numbered items inside them are the source of truth, and anything restating them is the drift this task
  exists to stop.
- **A `validate.py` check** that fails a `parent` naming no real epic or feature. It must resolve the two
  near-miss spellings that differ only by the words "from the", and it must be one that would have caught
  `"ROADMAP Epic A: distribution tooling"` on the day it appeared.
- **A consumer.** Without one this decays exactly as the current field did, which is the whole argument of
  the Problem section. **Decide which, and record the rejected alternative.** Two candidates: a generated
  Feature view listing each Feature with its open and done tasks, and `new-task` reading the vocabulary
  when it authors a parent. The second is closer to how the `spec:` axis stayed healthy, because its
  consumers are skills rather than reports, and a generated document nobody opens is itself a pointer with
  no consumer one level up.
- `_TEMPLATE.md`, which teaches `"ROADMAP#N feature-slug"`, a format no current task uses, so every new
  task starts from a placeholder that is already wrong.

**Out of scope:**

- **Rewriting the nine closed tasks carrying the fabricated epic.** They are historical records. Decide
  whether the check applies to `.tasks/done/` at all and say so; grandfathering is a legitimate answer and
  an unstated one is not.
- `ROADMAP.md`'s own staleness, which is
  [`chore-0066`](chore-0066-the-roadmap-has-five-verified-staleness-defects-and-no-gate.md). This task
  reads that file; it does not repair it.
- Adding an `owner`, `assignee`, or `reviewer` field. A different question, belonging with the multi-user
  work rather than here.

## Implementation notes

Prior art for reading a sibling document to answer a question: `check_lenses_are_composed` in
[`validate-skills.py`](../scripts/validate-skills.py). The `--links` machinery in `validate.py` already
resolves paths relative to the file being checked, so reading `ROADMAP.md` from `.tasks/` is a solved
shape here.

The hard part is not the parser. It is deciding **how strict to be about a Feature-level parent**.
Requiring one on every task fails eight of nine open tasks the day it lands, which is a migration rather
than a check. Warning instead of failing is the softer answer, and this repository has been burned by
warnings nobody reads. Pick one, and state the migration cost in the closeout as a number rather than a
word.

## Risks and rollback

Two modules plus a template, so this section is required.

The risk is a check that fails the whole backlog on landing. Measure the failure count against the real
tree **before** choosing strict or warn, and report both numbers.

The second risk is inventing a vocabulary that drifts from `ROADMAP.md` the first time a heading is
reworded. Derive it; do not restate it.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] `validate.py` rejects a `parent` naming no heading or numbered item in `ROADMAP.md`, proven by a test
      that fails against the current code.
- [ ] A test pins that `"ROADMAP Epic A: distribution tooling"` is rejected and that
      `"ROADMAP Epic A: broadly shareable (the public kit)"` is accepted.
- [ ] The two near-miss spellings differing only by "from the" are resolved, in whichever direction, and the
      direction is stated.
- [ ] A consumer exists and is named, with the rejected alternative recorded.
- [ ] `_TEMPLATE.md` no longer teaches a format no task uses.
- [ ] The closeout states, as a number, how many task files the check would fail if applied strictly.
- [ ] The closeout states whether the check applies to `.tasks/done/`.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
