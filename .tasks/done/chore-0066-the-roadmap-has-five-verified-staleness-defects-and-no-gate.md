---
id: chore-0066
title: ROADMAP.md carries five verified staleness defects, including an acceptance bar whose proof target is already spent
type: chore
status: done
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: []
touched_files:
  - ROADMAP.md
created: 2026-08-27
---

## Problem

[`validate.py`](../validate.py) checks every task file. The `doc links` gate checks 45 documents.
**Nothing checks whether [`ROADMAP.md`](../../ROADMAP.md) still describes reality**, and `AGENTS.md` calls
that file authoritative for what happens next.

Five defects, each verified against the files on 2026-08-27:

| Where | What it says | What is true |
|---|---|---|
| Header | `Last updated: 2026-08-07` | Content runs to 2026-08-21. |
| Kit hardening intro | "Ready to dispatch" over an eight-task wave table | All eight are in `.tasks/done/`. |
| Kit coherence hardening | Four findings read as open | `bug-0029`, `feat-0048`, `bug-0030` and `chore-0040` are done. |
| Epic C item 5 | The `systematic-debugging` contract is "at `status: draft` pending the author's approval" | [`systematic-debugging.md`](../../docs/spec/systematic-debugging.md) reads `status: approved`. |
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
  [`feat-0050`](../feat-0050-a-controlled-vocabulary-and-a-consumer-for-the-parent-field.md).
- The epic drafted into the file on 2026-08-27, which is current and needs no correction.

## Implementation notes

Read the file's own conventions before editing. Struck-through items carry the crediting task id, and the
three hardening sections use a different idiom from the epics. Match what is there rather than importing
a new one.

The `Last updated` field is the one correction that goes stale again the same week. Consider whether the
honest fix is a new date or removing a field nothing maintains, and say which you chose and why.

## Decisions

- **Premise that turned out false, and it is the whole crux.** This task asked for a *new* proof
  target for Epic E item 2, on the reading that the bar names a spent one. The bar had already been
  repointed and already been met. `chore-0051` amended `docs/spec/cloud-executable.md` on 2026-08-20
  to name `bug-0020` instead of `bug-0018`, chosen against the item's own criterion and not a
  weakened one, and `bug-0020` then landed that same day through an unattended cloud session:
  branch `claude/bug-0020-unknown-remedy-lcqb52`, draft pull request #41, nine-field report,
  `run-checks.py` verbatim at exit 0, and two tests reproduced failing before and passing after by a
  second session. `cloud-executable.conformance.md` records `S-017`, `S-018` and the
  unattended-branch surface row as **Conformed** on that run. So choosing a target would have
  reopened a satisfied bar and contradicted the contract. The correction is to record what happened,
  with its honest bound: `S-019` stays `Not-built` because the run's gates exited 0 and the failure
  path was never entered, and `S-008` stays unobserved in a real session because the run was staged
  on a base 99 files behind `developer`.
- **Rejected alternative: re-dating the `Last updated` header rather than removing it.** Removed.
  It had read 2026-08-07 for twenty days over content running to 2026-08-27 with nothing checking
  it, and re-dating buys one week and re-arms the same defect. Every substantive claim in the file
  already carries its own date, which is the date a reader can check against the thing it describes,
  and `git log -1 ROADMAP.md` answers the whole-file question without being able to drift.
- **Rejected alternative: discharging the two `feat-0048` holds and striking Epic E item 2 through.**
  Declined on all three. The gates are recorded as met (Epic B item 20, Epic E item 3) and item 2's
  acceptance is recorded as satisfied, in the file's own idiom and dated. Whether a fourth lens is
  now wanted, whether `autonomy.md` is blessed, and whether item 2 is complete are judgments the
  author makes, and this task's own scope says item completion is not a bookkeeping side effect.
- **Premise that turned out false, twice on counts.** The task asserts five defects and that content
  runs to 2026-08-21. Content runs to 2026-08-27, and the same-class sweep found seven, not five:
  the two extras are `chore-0042` and `chore-0043` reading as "filed rather than fixed" when both
  closed 2026-08-19, and Epic E's preamble measuring "`git ls-files .claude` returns nothing" when
  that command returns `.claude/settings.json`, committed 2026-08-07 by item 2(b) of the same epic.
  Two further present-tense claims were corrected as the same class, for nine in total.
- **Seam left open deliberately: `feat-0051` and `feat-0052` are not written into Epic E items 6 and
  7.** Both were created 2026-08-27 by a concurrent wave and name those Features as their `parent`,
  so `ROADMAP.md` naming them would follow the file's own idiom. Left alone anyway. `feat-0052`
  argues for turning telemetry capture on *before* the bounds that item 7 holds behind item 5, so
  recording it would read as discharging that hold, which is the line this task draws elsewhere; and
  writing ids from an unreconciled wave into a shared file risks recording ids that move. Reported
  as a finding instead.

## Risks and rollback

One file, prose only.

The risk is correcting the visible five and leaving a sixth. **Enumerate every task id this file names and
check each against `.tasks/` and `.tasks/done/`** rather than fixing only the five above, and report the
count checked beside the count corrected.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] All five defects are corrected.
- [x] Every task id `ROADMAP.md` names is checked against `.tasks/` and `.tasks/done/`, and the closeout
      states both the number checked and the number corrected.
- [x] Epic E item 2 carries a new proof target chosen against the stated criterion, or an explicit
      statement that no current backlog item qualifies.
- [x] Epic B item 20's and Epic E item 3's holds are re-checked against `feat-0048` and the verdict is
      recorded.
- [x] No Feature is struck through by this task.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
