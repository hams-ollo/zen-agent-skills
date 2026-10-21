---
id: chore-0092
title: The roadmap's description-budget figures are stale and the collision cluster they name is measurably not the worst one
type: chore
status: open
priority: P2
parent: "ROADMAP Epic E #6: fixture-based skill evaluation suite"
depends_on: []
touched_files:
  - ROADMAP.md
created: 2026-09-01
---

## Problem

Two lines of [`ROADMAP.md`](../ROADMAP.md), in Epic E item 6 and in "Out of scope by design", carry
the same figure and the same claim:

```text
with twenty skills whose descriptions average 759 characters and overlap heavily in vocabulary
(`spec-author` / `spec-quality` / `spec-plan-readiness` / `spec-conformance`, `doc-author` /
`doc-revise` / `doc-sync`, `test-author` / `test-quality`), the likeliest failure is not a skill
behaving wrongly but the wrong skill being selected
```

Both halves have drifted, and the second matters more than the first.

**The counts.** Measured 2026-09-01 through `install.description_of`, the reader the installer itself
uses, so this and the installer's own budget report cannot disagree:

```text
skills discovered: 22 | drafts: ['agent-observatory', 'systematic-debugging'] | shipped: 20
  all 22   total=17197  mean=782
  20 shipped total=15317  mean=766
  profile core   skills=  3 budget=  2298
  profile spine  skills= 18 budget= 13533
  profile all    skills= 20 budget= 15317
```

So neither "twenty skills" nor "759 characters" is current under either reading of the set. This is
the case the writing section of [`house-style.md`](../.agents/rules/house-style.md) forbids by name, a
count written in prose beside the thing it counts, and it is the same failure mode as the four
instances that rule already lists: the sentence looked permanently true and stopped being true the
moment a skill was added, which nobody thinks of as touching the roadmap.

**The cluster, which is the part worth fixing.** Jaccard similarity over content words in the
descriptions, stop words removed, measured the same day:

```text
mean pairwise Jaccard across all pairs: 0.0461
  0.236  agent-handoff / human-handoff
  0.231  doc-author / doc-revise
  0.196  test-author / verifier-agent
  0.180  fix-batch / reconcile-worktrees
  0.162  init-worktracking / new-task
  0.139  spec-author / spec-quality
```

The `spec-*` family, named first as the worst case, is well separated except for one pair. The two
families named second and third are the real collisions. And the pair ranked third,
`test-author` against `verifier-agent`, is not named at all.

That matters because this sentence is not commentary. It is the stated design input for an unbuilt
roadmap item: Epic E item 6 names trigger disambiguation as the half no external precedent covers, and
a fixture suite built to these priorities would spend its budget on the cluster that needs it least.

Found by the 2026-09-01 review, recorded as finding 4 in
[`docs/reviews/2026-09-01-optimization-and-gap-review.md`](../docs/reviews/2026-09-01-optimization-and-gap-review.md).

## Scope

**In scope:** correcting both occurrences in `ROADMAP.md` so the figures carry their measurement date
and the cluster list matches what was measured.

Three properties the correction has to hold:

1. Every figure is dated, per the roadmap's own per-entry dating rule, so a later reader can tell what
   the number was measured against rather than assuming it is current.
2. The set the figure describes is named, since 22 discovered and 20 shipped are different numbers and
   the current sentence does not say which it means.
3. The cluster list matches the table above, including the pair the current sentence omits.

**Out of scope:**

- Building `check-triggers.py`, or any gate that recomputes these figures. That is a proposal in the
  review report and a Feature in its own right, and adding a gate inside a prose correction would
  presuppose the artifact Epic E item 6 leaves open.
- Any change to a skill description. Six pairs overlapping is a finding about the descriptions, not a
  licence to rewrite them, and rewriting one to lower a number without an evaluation to check it
  against is the failure Epic E item 6 exists to avoid.
- Epic B item 19 and the sensor question. Related, separate.
- The other numeric claims in `ROADMAP.md`. Only these two were measured in this pass, and correcting
  unmeasured ones would put a fresh unverified number where an old one was.

## Implementation notes

Prefer naming the measurement and its date over restating a bare number, which is what the roadmap
already does elsewhere and what makes a figure survive contact with the next skill: something of the
form "measured 2026-09-01 at N skills and M characters" rather than "N skills averaging M characters".

The two occurrences are the same claim in two places, so correct them together. Consider whether the
second occurrence needs the figure at all, since its argument is about kit size rather than about
trigger collision, and a claim stated once is a claim that can only go stale once.

The measurements are reproducible without new tooling. Both were taken by importing
`scripts/install.py` and calling `discover_skills`, `partition_drafts`, `description_of` and
`resolve_profile`; the similarity table is Jaccard over lowercased content words of four or more
characters with a stop list. Reproduce them at the time of the edit rather than copying the numbers
above, since two more skills may have landed by then and copying a figure into a document is exactly
the move this task is correcting.

## Decisions

- **Rewriting the colliding descriptions was considered and rejected as out of scope.** The overlap is
  real, but lowering a similarity number with no evaluation to check the change against optimises the
  measurement rather than the behaviour, which is the failure Epic E item 6 already names.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] `grep -c "759 characters" ROADMAP.md` returns 0.
- [ ] `grep -c "twenty skills whose descriptions" ROADMAP.md` returns 0.
- [ ] Every remaining figure in the two corrected passages carries the date it was measured.
- [ ] The corrected cluster list names the pairs measured highest, including
      `test-author` / `verifier-agent`, which the current sentence omits.
- [ ] No file outside `ROADMAP.md` is modified.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason.
- [ ] File moved to `.tasks/done/`, `status: done`, with its relative links re-anchored for the extra
      directory level; one dated line added to `CHANGELOG.md` referencing this task id.
