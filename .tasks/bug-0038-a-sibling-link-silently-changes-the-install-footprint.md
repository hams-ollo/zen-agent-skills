---
id: bug-0038
title: Writing a markdown link to a sibling skill silently changes which skills a profile installs, and nothing warns the author
type: bug
status: open
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

`SIBLING_REF_RE` in [`install.py`](../scripts/install.py) is

```python
SIBLING_REF_RE = re.compile(r"\]\(\.\./([^/)]+)/SKILL\.md")
```

and the profile resolver expands a profile over the sibling closure of its seed. So **the markdown
link syntax inside a skill body is load-bearing for what the installer places.** A relative link is a
profile edge; the same skill named in backticks is not.

Nobody writing a skill body knows this. Discovered 2026-08-20 by `chore-0040`'s agent, which was
correcting a spine statement and wrote `pr-describe`'s new neighbour as
`[doc-sync](../doc-sync/SKILL.md)`, the obvious and readable form. Three `test_install.ProfileTests`
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

- [ ] The conventions section of `AGENTS.md` states that a relative link to a sibling `SKILL.md` is a
      profile edge, and names the backtick form for stating chain position without creating one.
- [ ] `tests/test_install.py` asserts resolved profile membership by name, and a test proves that
      adding a sibling link to a skill outside a profile's closure changes that profile's membership.
- [ ] That test fails against the current code only in the sense of not existing; adding a link in a
      fixture must produce a named-set difference rather than a size difference.
- [ ] The existing character-budget and ordering assertions still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
