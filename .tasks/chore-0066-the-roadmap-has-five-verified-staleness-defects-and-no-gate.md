---
id: chore-0066
title: ROADMAP.md carries five verified staleness defects, including an acceptance bar whose proof target is already spent
type: chore
status: open
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: []
touched_files:
  - ROADMAP.md
created: 2026-08-27
---

## Problem

[`validate.py`](validate.py) checks every task file. The `doc links` gate checks 45 documents.
**Nothing checks whether [`ROADMAP.md`](../ROADMAP.md) still describes reality**, and `AGENTS.md` calls
that file authoritative for what happens next.

Five defects, each verified against the files on 2026-08-27:

| Where | What it says | What is true |
|---|---|---|
| Header | `Last updated: 2026-08-07` | Content runs to 2026-08-21. |
| Kit hardening intro | "Ready to dispatch" over an eight-task wave table | All eight are in `.tasks/done/`. |
| Kit coherence hardening | Four findings read as open | `bug-0029`, `feat-0048`, `bug-0030` and `chore-0040` are done. |
| Epic C item 5 | The `systematic-debugging` contract is "at `status: draft` pending the author's approval" | [`systematic-debugging.md`](../docs/spec/systematic-debugging.md) reads `status: approved`. |
| Epic E item 2 | Acceptance names `bug-0018` landing via a cloud session | `bug-0018` is in `.tasks/done/`, landed conventionally. |

**The last is not cosmetic.** An acceptance bar naming a spent proof target cannot be satisfied as
written, so the Feature it gates is unfinishable until a new target is chosen.

And `feat-0048` reading as open matters twice over: **Epic B item 20 and Epic E item 3 both name it as
their gate**, so at least one hold in this file may already be dischargeable and no reader can tell.

## Scope

**In scope:** correct the five, and check the rest of the file for the same class.

- Each correction states what changed and when, in the file's existing idiom.
- **Choose a new proof target for Epic E item 2** against the criterion the original was chosen against:
  a defect whose acceptance requires a regression test failing before the change and passing after, so a
  session cannot fake it. That item states the criterion; do not invent a new one. If no current backlog
  item meets it, **say so and leave the bar unsatisfiable rather than weakening it**, because that item's
  own words are that a proof run whose check cannot distinguish real work from plausible work does not
  prove the thing the Feature exists to establish.
- Re-check Epic B item 20's and Epic E item 3's holds against `feat-0048` being done, and record the
  verdict either way. Discharging a hold is a judgment; recording that its gate is met is not.

**Out of scope:**

- **Building a gate for `ROADMAP.md`.** That class is what Epic B item 19 already holds, and answering it
  inside a correction pass would presuppose the artifact that item deliberately declines to presuppose.
  **If this work suggests what that gate should be, that is a finding to report**, and it is the most
  valuable thing this task could produce beyond the corrections themselves.
- Striking any Feature through. Item completion is the author's call, not a bookkeeping side effect.
- The nine closed tasks carrying a fabricated `parent`, which is
  [`feat-0050`](feat-0050-a-controlled-vocabulary-and-a-consumer-for-the-parent-field.md).
- The epic drafted into the file on 2026-08-27, which is current and needs no correction.

## Implementation notes

Read the file's own conventions before editing. Struck-through items carry the crediting task id, and the
three hardening sections use a different idiom from the epics. Match what is there rather than importing
a new one.

The `Last updated` field is the one correction that goes stale again the same week. Consider whether the
honest fix is a new date or removing a field nothing maintains, and say which you chose and why.

## Risks and rollback

One file, prose only.

The risk is correcting the visible five and leaving a sixth. **Enumerate every task id this file names and
check each against `.tasks/` and `.tasks/done/`** rather than fixing only the five above, and report the
count checked beside the count corrected.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] All five defects are corrected.
- [ ] Every task id `ROADMAP.md` names is checked against `.tasks/` and `.tasks/done/`, and the closeout
      states both the number checked and the number corrected.
- [ ] Epic E item 2 carries a new proof target chosen against the stated criterion, or an explicit
      statement that no current backlog item qualifies.
- [ ] Epic B item 20's and Epic E item 3's holds are re-checked against `feat-0048` and the verdict is
      recorded.
- [ ] No Feature is struck through by this task.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
