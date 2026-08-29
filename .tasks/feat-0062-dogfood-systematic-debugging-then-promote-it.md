---
id: feat-0062
title: Use systematic-debugging on a real defect, then promote it out of draft or record why not
type: feat
status: open
priority: P2
parent: "ROADMAP Epic C #5 systematic-debugging"
depends_on: [feat-0061]
spec: docs/spec/systematic-debugging.md
scenarios: []
# Directories rather than exact paths for everything `feat-0061` creates: this file is
# validated now and those paths do not exist until that task has run.
touched_files:
  - .agents/skills/
  - tests/
  - docs/spec/
  - ROADMAP.md
created: 2026-08-29
---

## Problem

`feat-0061` ships the skill as a draft, placed by no profile. That is deliberate: the contribution
bar in the contribution-bar section of `AGENTS.md` is that **no skill ships cold**, and a skill whose
only evidence is that its own structural tests pass has proven that its prose contains certain words.

The bound `feat-0061` states in as many words is that a skill body is instructions to a model, so its
tests can assert an instruction is present and cannot assert a model obeyed it. **This task is the
only thing that closes that gap**, and it closes it the one way available: run the skill against a
defect whose cause nobody knows yet, and see whether the procedure produced the answer or whether the
answer arrived some other way and the procedure was narrated over it afterwards.

There is precedent for the draft state outliving its usefulness. `agent-observatory` has been a draft
since 2026-08-29 for the same reason and has no promotion task, which is how a draft becomes
permanent by inattention rather than by decision.

## Scope

**In scope:** one real diagnosis, then a decision about the draft status.

- **Run the skill on a defect whose cause is genuinely unknown.** The recommended target is the
  `sqlite3.OperationalError: database is locked` that takes `scripts/observatory/serve.py`'s routes
  down while a concurrent session's ingester holds the store. It was observed live twice, on
  2026-08-28 and again on 2026-08-29 during reconciliation, and it is a good target for three
  reasons the contract cares about: it is **intermittent**, which is `S-012`; it **crosses
  components**, ingester and server, which is `S-008`; and its proximate cause is known while the
  right fix is not, which is exactly the gap between a symptom and a named cause.
- **Record the diagnosis the contract's own record shape**, at whatever verdict it reaches.
  `not_reproducible` and `architectural` are results, not failures, and a run that reaches one of
  them is still evidence about the skill.
- **Report what the skill got wrong**, which is the actual deliverable. A dogfood that reports only
  that it worked has measured nothing. Name every place the procedure was unclear, produced a step
  that could not be followed, or was silently departed from.
- **Then decide the draft status**, and record the decision either way:
  - Promote: remove `metadata: status: draft`, and place it in the profiles it belongs to.
  - Keep it a draft: state what the run showed that the skill has to answer first, and file the task
    for it. A draft kept deliberately is a different thing from a draft nobody revisited.
- Any correction to the skill or its tests that the run's findings justify.

**Out of scope:**

- **Fixing the defect diagnosed.** The contract refuses repair, and this task inherits that. The
  diagnosis feeds `new-task`, which is the point of `S-006`. A fix here would also make the dogfood
  worthless, because the skill's value is the named cause and not the diff.
- Widening the contract. If the run reveals the contract is wrong, that is a finding and an
  amendment task, following `chore-0061`'s discipline; it is not an edit to make while holding a
  diagnosis.
- Promoting `agent-observatory` out of draft. Its dogfood is its own task and is not this one.

## Implementation notes

**The honest failure mode is a dogfood that confirms.** An agent running a procedure it has just read
and then reporting that the procedure worked is the weakest possible evidence, and it is what this
task will produce by default. Two things make it worth more:

- **Write down the answer's arrival time.** If the cause was obvious three minutes in and the record
  was filled out afterwards, that is the finding, and it means the skill added ceremony rather than
  method. Say so.
- **Have the diagnosis checked by someone who did not produce it.** The independence rule in the
  autonomy lens applies to a claim about a cause exactly as it applies to a claim about a test.

The second candidate target, if the first turns out to be already understood, is `bug-0050`, the
committed hook that has exited 49 on every session start since 2026-08-07. It is weaker on purpose:
its cause is known, so it exercises the record shape and not the investigation. Prefer it only as a
fallback and say which was used.

## Risks and rollback

Touches the skill tree and the documentation set, and promotion changes what `install.py` places.

- **Promotion is the risky half, not the diagnosis.** Removing `draft` moves the skill into profiles,
  which changes the description budget every profile is measured against and puts the skill in front
  of adopters. `feat-0060` recorded that the budget is printed over the shipped set rather than the
  discovered set, so a promotion moves a figure two tests read.
- Reversible by reverting one commit. Re-adding the `draft` block returns the skill to being placed
  by no profile, and nothing outside the repository has changed.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] A diagnosis record exists for a real defect, carrying every field its verdict requires.
- [ ] The record names which defect was used, and why, if it was not the recommended target.
- [ ] The findings against the skill are recorded, and `none` is stated explicitly rather than
      reached by silence.
- [ ] The diagnosis was checked by an agent that did not produce it.
- [ ] The draft decision is recorded either way. If promoted, `install.py --dry-run` shows the skill
      placed in its profiles and the description budget still passes. If kept, the reason is stated
      and the task that would change it is filed.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
