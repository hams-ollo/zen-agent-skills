---
id: bug-0040
title: The lens-composition check is satisfied by a mention inside a code fence, in the one script that guards every other reference rule against exactly that
type: bug
status: open
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: [chore-0047]
spec: "docs/spec/validate-skills.md"
scenarios: ["S-023"]
touched_files:
  - scripts/validate-skills.py
  - tests/test_validate_skills.py
created: 2026-08-20
---

## Problem

`check_lenses_are_composed()` in [`validate-skills.py`](../scripts/validate-skills.py) satisfies its
rule with a plain substring test over the whole body:

```python
if any(rules_file.name in skill_text for skill_text in skill_texts.values()):
    continue
```

So a skill that merely **shows** `autonomy.md` inside a fenced block or an inline code span, as an
example of what a reference looks like, counts as composing it. The lens would be reported as wired
while no reader has any way to reach it, which is the exact failure the rule exists to catch.

The same script guards every other reference rule against this. `code_span_ranges()` and
`fenced_block_ranges()` appear seven times in it, and `S-022` was added to the contract on 2026-08-19
to describe precisely that guard for the link rules. This one check does not use it.

Three prior instances of the identical class are closed: `bug-0023` in `.tasks/validate.py`,
`bug-0027` in this script's link checker, and `bug-0028` in `build-adapters.py`. This is the fourth,
and the first to arrive in code written *after* the other three landed, which is the argument for
fixing it rather than filing it as a curiosity.

Two properties bound how urgent it is, and both belong in the record. It is a **false-negative**
direction: the rule becomes too easy to satisfy, so it under-reports rather than blocking good work.
And it fires on nothing today: no skill body currently shows a lens filename inside a span or a
fence. Found by `chore-0047`'s agent while writing `S-023`, which recorded it as an asymmetry rather
than a divergence, correctly, because the scenario says the filename appears in a `SKILL.md` and the
code does exactly that.

## Scope

**In scope:** apply the existing span and fence exclusion to the lens-reference test, and cover it.

- Reuse `code_span_ranges()` and `fenced_block_ranges()` as they stand. They are already in this
  module and already character-identical to the copies in the other two tools, which `bug-0028`
  verified; do not write a fourth variant.
- A test in both directions: a skill referencing the lens only inside a fence must fail the check, and
  a skill referencing it normally must pass.

**Out of scope:**

- The three other copies of the range helpers. Deduplicating them is a standing recommendation with a
  portability cost, since the tracker validator ships standalone into an adopter's repository, and
  `bug-0028` recorded it as a deliberate seam.
- `LENS_DECLARATION_RE` matching the bare word `lens` in a rules file's opening lines, which
  `chore-0047` also noted. Contrived, bounded by its own test, and the contract deliberately describes
  the declaration qualitatively so tuning it is not an amendment.
- Any change to `S-023`. Its wording, that the filename appears in a `SKILL.md`, stays true after this
  fix; what changes is which appearances count, and that is the same refinement `S-022` makes for the
  link rules. Confirm that at closeout rather than assuming it, and if the contract does need a word,
  that is an amendment task and not this one.

## Implementation notes

**Sequence this before the author re-approves `validate-skills.md`.** `chore-0047` left that spec
carrying a pending amendment, and its agent's recommendation was explicit: fixing this after
re-approval means amending the same contract twice for one behaviour. That is why this task depends
on `chore-0047` rather than running beside it.

The fix is small and the test is the point. Build the fixture skill body deliberately, with the lens
filename appearing **only** inside a fence, since a body that also mentions it normally would pass
either way and prove nothing. That is the same trap `bug-0028`'s agent avoided by constructing its
`__pycache__` fixture rather than observing a real tree.

## Risks and rollback

Two files in one module, so the more-than-one-module rule does not fire.

The failure direction reverses with this change: today the rule is too easy to satisfy, and afterwards
a skill that references a lens only from inside a fence starts failing the build. That is correct, and
it fires on nothing in the kit today, so the change is inert here and becomes load-bearing for an
adopter. Say so in the closeout rather than reporting it as a fix with observable effect.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [ ] A skill whose only mention of a lens filename is inside a fenced block or an inline code span
      does not satisfy the rule, proven by a test that fails against the current code.
- [ ] A skill referencing the lens normally still satisfies it, proven in the same test.
- [ ] The fix reuses this module's existing range helpers rather than adding a fourth copy.
- [ ] The closeout states whether `S-023`'s wording still holds unchanged, checked rather than assumed.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
