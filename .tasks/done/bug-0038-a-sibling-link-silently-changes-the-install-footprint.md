---
id: bug-0038
title: Writing a markdown link to a sibling skill silently changes which skills a profile installs, and nothing warns the author
type: bug
status: done
priority: P1
parent: "ROADMAP Epic A: distribution tooling"
depends_on: [chore-0040]
spec: "docs/spec/install.md"
touched_files:
  - AGENTS.md
  - scripts/install.py
  - tests/test_install.py
created: 2026-08-20
---

## Problem

`SIBLING_REF_RE` in [`install.py`](../../scripts/install.py) is

```python
SIBLING_REF_RE = re.compile(r"\]\(\.\./([^/)]+)/SKILL\.md")
```

and the profile resolver expands a profile over the sibling closure of its seed. So **the markdown
link syntax inside a skill body is load-bearing for what the installer places.** A relative link is a
profile edge; the same skill named in backticks is not.

Nobody writing a skill body knows this. Discovered 2026-08-20 by `chore-0040`'s agent, which was
correcting a spine statement and wrote `pr-describe`'s new neighbour as
`[doc-sync](../../doc-sync/SKILL.md)`, the obvious and readable form. Three `test_install.ProfileTests`
cases failed. The `core` seed is exactly `project-bootstrap`, `init-worktracking`, `pr-describe`;
`doc-sync` sits in the fourteen-skill strongly connected component, so one link pulled that whole
component into `core` and collapsed it into `spine`, both at 13501 characters, breaking the
`core < spine` invariant.

The agent diagnosed it, wrote the reference in backticks instead, and reported it. **That is the only
reason it surfaced.** The failure it produced was loud, but the class is not: a link added to a skill
already inside a profile's closure changes nothing and passes, so the same edit is sometimes free and
sometimes silently doubles a profile, with no way for the author to tell which.

The tests that caught it are pinned on character budgets and an ordering invariant. They caught this
instance because the collapse was large. A smaller pull, one skill into `core`, would satisfy
`core < spine` and land unnoticed.

## Scope

**In scope:** make the coupling visible to the person who can trip it, and make an unintended profile
change fail loudly rather than by budget arithmetic.

- Write the rule where a skill author reads: the conventions section of `AGENTS.md` already governs
  what a skill body may link to (the portability contract's three legal link classes), and this is the
  same sentence's business. State that a relative link to a sibling `SKILL.md` is a profile edge, and
  that naming a sibling in backticks is the form for stating chain position without creating one.
- Make the invariant explicit in `tests/test_install.py`: assert profile membership directly, so a
  changed closure names the skill that moved rather than surfacing as two equal character counts.

**Out of scope:**

- Changing how profiles resolve. The sibling closure is deliberate and correct: a profile that
  installs a skill without what that skill links to ships a broken tree, which is the defect the
  closure exists to prevent. This task makes the mechanism legible, it does not redesign it.
- The profile seeds. Whether `core` should be three skills is a product question, not this one.
- `docs/spec/install.md`. The contract describes profiles and their budgets; whether it should also
  state that link syntax defines the edges is worth asking at closeout, and amending it here would
  collide with `chore-0033`, which is already queued against that file.
- `build-adapters.py`'s own link rewriting, which is a different consumer of the same syntax.

## Implementation notes

The `AGENTS.md` sentence is the durable half and should be short. The portability contract already
tells an author which links are legal; this adds what one of them *does*. Resist explaining the
closure algorithm, which belongs in `install.py`'s own comments where it already is.

For the test, prefer asserting the resolved set for each profile over asserting its size. A set
comparison names the skill that appeared, which is the information an author needs; a size comparison
tells them a number changed. `chore-0040`'s failure took real diagnosis precisely because the symptom
was two equal character counts.

Worth knowing while testing: the two links `chore-0040` added to `fix-batch`, to `test-author` and
`verifier-agent`, were free, because both already appeared elsewhere in that body. So a fixture that
adds a link to an already-linked skill will not reproduce the bug.

## Risks and rollback

Touches a rules document, the installer, and its tests, so the more-than-one-module rule fires.

The risk is over-tightening: an assertion pinning exact profile membership fails on every legitimate
profile change, which is a maintenance cost paid on real work. Pin the property that matters, that a
profile's membership is what the seed and its closure say and nothing more, and let the expected sets
live in one place a legitimate change updates once.

Reversible by reverting one commit. No installed tree changes until someone re-runs the installer.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [x] The conventions section of `AGENTS.md` states that a relative link to a sibling `SKILL.md` is a
      profile edge, and names the backtick form for stating chain position without creating one.
- [x] `tests/test_install.py` asserts resolved profile membership by name, and a test proves that
      adding a sibling link to a skill outside a profile's closure changes that profile's membership.
- [x] That test fails against the current code only in the sense of not existing; adding a link in a
      fixture must produce a named-set difference rather than a size difference.
- [x] The existing character-budget and ordering assertions still pass, unchanged in intent.

## Decisions

- **The rule lives in the portability contract (section 5), with a pointer from the conventions
  section (section 6).** The acceptance criterion names "the conventions section", and its own
  parenthetical identifies the text it means as "the portability contract's three legal link
  classes", which is section 5's link bullet. Those are two different headings in the current
  `AGENTS.md`. The substance went next to the three legal link classes, because that is the bullet an
  author reads when deciding how to write a link and the new rule is the same sentence's business.
  Section 6 gets one line saying the link is load-bearing and pointing up, so a reader who arrives at
  "relative markdown links" as a formatting convention is told it is not only formatting. No
  substance is duplicated.

- **`install.py` gains a comment above `SIBLING_REF_RE` and nothing else.** The task's implementation
  notes forbid explaining the closure algorithm again, and `resolve_profile` already does. The
  comment states only what the regex means for a skill author, and points at `AGENTS.md` as the place
  that rule is written for the person who can trip it.

- **Profile membership is pinned as a named constant, `EXPECTED_PROFILE_MEMBERSHIP`, not as a size.**
  This is the "one place a legitimate change updates once" the risk section asks for. `core` and
  `spine` are listed by name; `all` is deliberately not, because its seed is `None` and a literal
  list would have to be edited by every new skill, so it is asserted as the property (every shipped
  skill) instead.

- **A second test guards the constant itself.** `test_each_pinned_profile_holds_its_seed_and_is_closed_over_it`
  re-derives the two properties the pinned sets are a snapshot of (the seed survives resolution, and
  no member links outside the set). Without it, a future agent could silence a real regression by
  pasting the new set into the constant, which is exactly the failure mode a pinned list invites.

- **The reproduction fixture links to a skill outside the closure, and a sibling test covers the
  trap.** `test_a_link_to_a_skill_outside_the_closure_moves_it_into_the_profile` adds `omega` (which
  itself reaches `zeta`) and asserts the named difference `{omega, zeta}`, plus the on-disk placed
  set. `test_a_link_to_a_skill_already_in_the_closure_changes_nothing` pins the free case that made
  two of `chore-0040`'s links invisible, so the fixture records that the same edit is sometimes free.
  A third test pins that the backtick form creates no edge, which is the escape hatch `AGENTS.md` now
  tells authors to use.

- **Verified the new assertion catches the real defect, then reverted the probe.** Appending
  `[doc-sync](../../doc-sync/SKILL.md)` to `pr-describe/SKILL.md` made the new test fail naming all
  fifteen skills that moved into `core`. Appending `[human-handoff](../../human-handoff/SKILL.md)`
  instead made it fail naming `human-handoff` and `agent-handoff`, a two-skill pull. Both probes were
  reverted with `git checkout --`; no skill body is changed by this task.

- **Nothing was changed in how profiles resolve, and `docs/spec/install.md` was not touched**, per the
  task's out-of-scope list and `chore-0033` being queued against that file.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
