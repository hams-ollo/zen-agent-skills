---
id: chore-0048
title: Two spine edges are asserted by only one of the two skills they connect, which is the condition that let a wrong edge survive a correction pass
type: chore
status: done
priority: P2
parent: "ROADMAP Kit coherence hardening (2026-08-18 review pass)"
depends_on: [bug-0039]
touched_files:
  - .agents/skills/init-worktracking/SKILL.md
  - .agents/skills/reconcile-worktrees/SKILL.md
created: 2026-08-20
---

## Problem

[`bug-0039`](bug-0039-readme-spine-diagram-gates-the-decomposition-before-it-exists.md) re-derived all
eleven edges of the README spine diagram against the skills they connect. Nine are asserted by both
skills. Two are asserted by one:

```text
init-worktracking -> spec-author       grep -c 'spec-author' init-worktracking/SKILL.md  ->  0
reconcile-worktrees -> doc-sync        grep -c 'doc-sync'  reconcile-worktrees/SKILL.md  ->  0
```

Both edges are carried entirely by the other end: `project-bootstrap`'s Notes for the first,
`pr-describe`'s Notes for the second. Neither is wrong. Both are unverifiable from the skill a reader
would be holding when they need them.

**This is the condition that let a wrong edge survive a correction pass, which is the argument for
fixing it rather than noting it.** `chore-0040` was dispatched on 2026-08-19 specifically to make the
spine statements agree, and it checked each statement against the README diagram. That method cannot
catch a one-sided edge, because there is nothing on the other side to disagree with. The edge
`bug-0039` found genuinely wrong, `spec-plan-readiness` before `new-task`, was caught only because
both skills asserted it and both contradicted the diagram. Where only one skill speaks, a wrong
diagram and a silent skill agree by default.

It also falsifies a claim `project-bootstrap` makes about the kit. Its Notes state the invariant that
every skill along the spine names just its own neighbours, which is the design `chore-0040` adopted
deliberately, because a full chain restated in four places is what drifted in the first place. Two
skills do not hold up their end of it.

## Scope

**In scope:** give each of the two skills the neighbour statement its counterpart already has.

- `init-worktracking` names `spec-author` as the contract-driven path out of it. Its Step 8 currently
  offers `new-task` and mentions no spec, which is correct for the non-contract path and incomplete
  for the other.
- `reconcile-worktrees` names `doc-sync` as what follows it.
- Both in the immediate-neighbour form `chore-0040` established, not a restated chain.

**Out of scope:**

- The nine two-sided edges, which are correct and asserted from both ends.
- The README diagram, corrected by `bug-0039` and the reference here.
- Adding a spine statement to any skill that has no place in the chain. This closes two gaps in an
  existing invariant; it does not extend the invariant to skills it never covered.
- `new-task`'s Step 7 phrasing, which `bug-0039` reported can now be stated positively since the
  reference it was written to route around is fixed. Real, separate, and one sentence.

## Implementation notes

Write each statement from the skill's own point of view, naming what it hands to and what hands to
it, rather than copying the counterpart's sentence. The counterpart's phrasing is written from the
other direction and reads oddly transplanted.

`init-worktracking` is the harder of the two, because it has two legitimate downstreams. A repository
that adopts the spec spine goes to `spec-author`; one that does not goes to `new-task`. Say both,
briefly, rather than replacing one with the other, since Step 8's existing offer is not wrong.

Do not add a link where a mention will do. A relative link to a sibling `SKILL.md` is a profile edge
in `install.py`, which `bug-0038` documented on 2026-08-20, so a link written for readability changes
what the installer places. `init-worktracking` and `reconcile-worktrees` are both in `spine`, and
`spec-author` and `doc-sync` are too, so a link here is very likely free; check rather than assume,
and use the backtick form if it is not.

## Decisions

**A premise that turned out false: a link from `init-worktracking` to `spec-author` is not free, it
is the largest profile move available in this repository.** The implementation notes reason that all
four skills are in `spine`, so a markdown link costs nothing. `init-worktracking` is also one of the
three seeds of `core`, and `spec-author` is not in `core` at all. Resolved with `install.py`'s own
`resolve_profile` over a hypothetical seed carrying that link, `core` goes from 3 skills to 18, which
is `spine` exactly: one readable link would have collapsed the two profiles into one. Both statements
therefore use the backtick form, which is also what both counterparts already use, since
`project-bootstrap` and `pr-describe` write their spine chains in backticks rather than links.
Measured membership before and after the change is identical: `core` 3, `spine` 18, `all` 20, same
names in each.

**A premise that turned out false in `reconcile-worktrees`, found while writing its statement:** the
skill calls itself "the closing step of the kit spine" in both its body and its frontmatter
description, and `pr-describe` calls itself "the closing bookend" of the same spine two edges later.
Adding the `doc-sync` statement to a skill that claims to be last would have created a fresh
self-contradiction inside one file, so both instances now read "landing step", which is what the
skill does and leaves the closing claim to the skill that holds it. This is a phrase in the touched
file rather than new scope, and it is exactly the class of error a one-sided edge hides: nothing
disagreed with the claim because nothing downstream spoke.

**A seam left open deliberately: `new-task`'s Step 7 still states its gate negatively.** Line 124
reads "the next step is not `fix-batch`: it is `spec-plan-readiness` over the spec plus this task
set", the phrasing written to route around the README defect `bug-0039` has since fixed. Confirmed
still present, named out of scope by this task, and left as found.

**A seam left open deliberately: the invariant is closed, not extended.** `init-worktracking` gained
a Notes bullet in the counterparts' form as well as the Step 8 offer, because Step 8 can only say
what the skill hands to, and the invariant `project-bootstrap` asserts is about naming both
neighbours. No skill outside the existing chain gained a spine statement.

## Risks and rollback

Two skill bodies, prose only, so the more-than-one-module rule does not fire. The link-versus-backtick
point above is the one way a prose edit here reaches beyond prose, and `bug-0038`'s new membership
assertions will name any skill that moves.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] `grep -c 'spec-author' .agents/skills/init-worktracking/SKILL.md` is non-zero, and the mention
      is a neighbour statement rather than an aside.
- [x] `grep -c 'doc-sync' .agents/skills/reconcile-worktrees/SKILL.md` is non-zero, likewise.
- [x] `init-worktracking` names both downstream paths, the spec spine and the direct one.
- [x] Profile membership is unchanged, or the change is stated and deliberate, checked against
      `bug-0038`'s assertions rather than assumed.
- [x] No other skill body is modified, and the README is untouched.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
