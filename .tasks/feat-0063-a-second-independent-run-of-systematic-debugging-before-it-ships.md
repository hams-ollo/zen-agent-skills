---
id: feat-0063
title: One independent run of systematic-debugging that survives a check, before it leaves draft
type: feat
status: open
priority: P2
parent: "ROADMAP Epic C #5 systematic-debugging"
depends_on: [feat-0062]
spec: docs/spec/systematic-debugging.md
scenarios: []
touched_files:
  - .agents/skills/
  - docs/spec/
  - ROADMAP.md
  - docs/CATALOG.md
created: 2026-08-29
---

## Problem

`feat-0062` ran [`systematic-debugging`](../.agents/skills/systematic-debugging/SKILL.md) on a real
defect and the run was worth having: it named a cause, and the procedure demonstrably changed the
answer, killing a wrong cause that reading the code alone had produced.

**It also returned a wrong root cause that passed the skill's own confirming-observation test, and
nothing in the skill caught it.** The trial it called confirming was raising a SQLite busy timeout,
which ends any wait whatever is waiting, so it was consistent with the hypothesis and did not test
it. An independent check found a different single change that fixed the same symptom at baseline
latency, and a third that showed the record's stated mechanism was not involved at all. The wrong
answer was caught by independence and by nothing else.

Five corrections went into the skill as a result, and they are the reason to run it again rather than
a reason to consider it finished. **Every one of them was written by the agent whose run they came
from**, which is the same non-independence that let the wrong cause through. The skill has now been
used exactly once, by the session that wrote it, on a defect that session chose, and corrected by
that session. That is one data point and the observer is inside it.

`feat-0062`'s own words for this state: an agent running a procedure it has just read and then
reporting that the procedure worked is the weakest possible evidence.

## Scope

**In scope:** one run that removes the author from the loop, then the draft decision again.

- **A session that did not write the skill runs it**, on a defect **it did not choose**. Both halves
  matter and the second is the one that is easy to lose: an author picking the defect picks one the
  procedure suits.
- **The diagnosis is checked by a third party**, not by the running session and not by the author.
  Rule A7 of the autonomy rules module, applied to the check as well as to the run.
- **Report what the five corrections were worth.** They were written against one run's failures and
  have never been exercised. Say which fired, which did not come up, and which got in the way. A
  correction that never fires on a second run is a correction written for a single incident.
- **Then the draft decision.** Promote means removing `metadata: status: draft`, choosing the
  profiles, and giving `docs/CATALOG.md` a row, which is [`chore-0079`](chore-0079-the-catalog-has-no-slot-for-a-skill-that-is-built-but-not-blessed.md)'s
  question. Keeping it a draft again means naming what the second run showed and filing the next
  task, and at that point the skill's design rather than its wording is the thing to look at.

**Out of scope:**

- **Fixing whatever the run diagnoses.** The contract refuses repair and this inherits it, for the
  same reason `feat-0062` did: a run that ends in a diff has measured the diff and not the procedure.
- Widening the contract. [`chore-0080`](chore-0080-the-diagnosis-record-has-nowhere-to-put-a-defect-found-on-the-way.md)
  holds the one contract question this run raised, and it is a separate decision.
- The observatory defect `feat-0062` diagnosed. It is a real bug with a named cause and a corrected
  record, and it wants its own task rather than being folded in here.

## Implementation notes

**Do not hand the runner this task file's problem statement.** It names the failure mode, which tells
the runner what to avoid and makes the run a test of the warning rather than of the skill. Hand it
the skill, a defect, and the record shape.

The strongest available target is a defect nobody in this repository has diagnosed yet. If one is not
to hand, the second-strongest is a defect whose cause is recorded in a closed task file that the
running session is not given, so the recorded cause becomes an answer key the check can use.

**The bar this task exists to clear, stated so it can be checked:** a diagnosis produced by a session
that did not write the skill, over a defect that session did not choose, which survives a check by an
agent that produced neither. Anything less leaves the skill where it is now, which is one
self-observed run.

## Risks and rollback

- **The likeliest outcome is another keep-it-a-draft**, and that is not a failure. Two runs with
  findings is a skill being iterated on, which is what the contribution bar in the contribution-bar
  section of `AGENTS.md` asks for. The failure mode is a run that reports success and adds nothing,
  which the reporting requirement above is meant to make visible.
- Promotion is the risky half, exactly as `feat-0062` recorded: it moves the skill into profiles,
  changes the description budget two tests read, and puts it in front of adopters.
- Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] A diagnosis record exists from a session that did not write the skill, over a defect that
      session did not choose, and the record says which defect and who chose it.
- [ ] The diagnosis was checked by an agent that produced neither the diagnosis nor the skill, and
      the check's verdict is recorded whichever way it went.
- [ ] Each of the five corrections `feat-0062` made is reported as fired, not applicable, or an
      obstacle. `none` is stated explicitly rather than reached by silence.
- [ ] The draft decision is recorded either way. If promoted, `install.py --dry-run` shows the skill
      placed in its profiles, the description budget still passes, and `docs/CATALOG.md` carries it.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
