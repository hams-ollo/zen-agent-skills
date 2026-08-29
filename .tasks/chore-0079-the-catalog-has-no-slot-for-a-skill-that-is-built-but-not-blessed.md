---
id: chore-0079
title: The reader-facing catalog has no slot for a skill that is built but not blessed, and two are now in it
type: chore
status: open
priority: P2
parent: "ROADMAP Epic C: semi-scalable (teams and clients)"
depends_on: []
touched_files:
  - docs/CATALOG.md
created: 2026-08-29
---

## Problem

[`docs/CATALOG.md`](../docs/CATALOG.md) states its own rule in its opening: a skill is listed as
**shipped** once it lives under `.agents/skills/` and has been used and iterated on for real, and
"everything else is **planned**, and stays planned until it has earned its place."

That is a binary over a set that now has three states. **Two skills are built, sit under
`.agents/skills/`, carry a `metadata: status: draft` marker, and are placed by no profile**:
`agent-observatory`, a draft since 2026-08-29, and `systematic-debugging`, added the same day by
`feat-0061`. Neither appears in the catalog at all, in either status, because neither is true:
`shipped` would be false, and `planned` would be false in the other direction, since the skill is
written, tested, and audited against its contract.

So the reader-facing inventory of the kit is silently missing two of its twenty-two skills, and the
document that says it lists "every skill Zen Agent Skills ships, plus what is planned" lists neither
category they belong to. A reader counting the catalog gets twenty. `docs/OBSERVATORY.md` names both
in its never-used list, so the two documents disagree about what exists.

Found by the `doc-sync` step at `feat-0061`'s closeout, and **dismissed there rather than fixed**,
because inventing a third status in a reader-facing document is a documentation decision rather than
a knock-on of adding a skill. Filed so it is a decision somebody makes rather than a gap nobody
revisits, which is the state `agent-observatory` has been in since it was drafted.

## Scope

**In scope:** decide how the catalog names a built-but-unblessed skill, and apply it to both.

- **The decision itself.** At least three shapes work and they are not equivalent to a reader: a
  third status word (`draft`) in the existing `Status` column; a separate short section listing
  drafts with the contribution bar stated once; or a deliberate decision that drafts stay out, in
  which case the catalog's opening sentence is wrong as written and should say so, because "every
  skill this kit ships" is not the same set as "every skill under `.agents/skills/`".
- **Both skills, whichever shape wins.** A rule applied to one of the two leaves the same
  inconsistency with a smaller denominator.
- **The opening rule reworded to match**, so the document does not state a binary it no longer
  follows.

**Out of scope:**

- **Promoting either skill.** `feat-0062` decides `systematic-debugging`'s draft status and
  `agent-observatory` has no promotion task, which is itself worth noticing and is not this task.
- Any change to `install.py`'s draft handling. The distribution behavior is correct and contracted
  by `S-015` of [`docs/spec/install.md`](../docs/spec/install.md); this is about what a reader is
  told, not about what is placed.
- `ROADMAP.md`, which already records both as drafts in prose and is builder-facing rather than
  reader-facing.

## Implementation notes

The catalog is prose for people browsing the kit, so the test is what a reader concludes rather than
what is technically true. A skill listed with no qualifier reads as available; one omitted reads as
absent. Both readings are wrong for a draft, which is why the omission is not a safe default.

Whichever shape is chosen, state the contribution bar next to it once rather than per row. The rule
that a skill ships only after real use is the interesting thing about this category, and repeating
it per skill buries it.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] Every skill directory under `.agents/skills/` is accounted for in `docs/CATALOG.md`, or the
      document states the exclusion rule it is actually following.
- [ ] `agent-observatory` and `systematic-debugging` are both handled the same way.
- [ ] The catalog's opening rule matches what the document does.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
