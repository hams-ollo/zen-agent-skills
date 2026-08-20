---
id: bug-0040
title: The lens-composition check is satisfied by a mention inside a code fence, in the one script that guards every other reference rule against exactly that
type: bug
status: done
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

`check_lenses_are_composed()` in [`validate-skills.py`](../../scripts/validate-skills.py) satisfies its
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
And it fires on nothing today: no skill body shows a lens filename inside a **fence**. **Amended at
closeout: the span half of that sentence was wrong.** Measured over the twenty shipped bodies, the
three lens filenames occur 60 times, 0 inside a fence and 27 inside an inline code span, so a span
exclusion would have fired on most of the tree. See `## Decisions`. Found by `chore-0047`'s agent
while writing `S-023`, which recorded it as an asymmetry rather
than a divergence, correctly, because the scenario says the filename appears in a `SKILL.md` and the
code does exactly that.

## Scope

**In scope:** apply the existing fence exclusion to the lens-reference test, and cover it.

**Amended at closeout (2026-08-20).** This section originally read "the existing span and fence
exclusion". The span half was struck after the work proved it wrong: `S-023` protects a prose mention
naming the file, the house style writes such a mention in backticks, and excluding spans would break
the spec-derived test `test_a_prose_mention_naming_the_file_counts_as_a_reference` and cost
`house-review` its only reference to `house-style.md`. The full argument is in `## Decisions`. The
task as originally written could not be satisfied without amending `S-023`, which it puts out of
scope; the criteria below are the amended ones.

- Reuse `fenced_block_ranges()` as it stands. It is already in this module and already
  character-identical to the copies in the other two tools, which `bug-0028` verified; do not write a
  fourth variant. `code_span_ranges()` is deliberately **not** used here, per the amendment above.
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

- [x] A skill whose only mention of a lens filename is inside a fenced block does not satisfy the
      rule, proven by `test_a_mention_only_inside_a_fenced_block_is_not_a_reference`, which fails
      against the current code (`0 != 1`). **The inline-code-span half of this criterion was not
      implemented**, and the reason is in `## Decisions` below.
- [x] A skill referencing the lens normally still satisfies it, proven in the same class by
      `test_a_real_reference_beside_a_fenced_example_still_counts` and
      `test_an_unterminated_fence_does_not_hide_the_reference_below_it`.
- [x] The fix reuses this module's existing range helpers rather than adding a fourth copy:
      `_names_file_outside_fences()` calls `fenced_block_ranges()` as it stands.
- [x] The closeout states whether `S-023`'s wording still holds unchanged, checked rather than
      assumed. **It holds.** The scenario says the filename appears in a `SKILL.md`; the guard
      changes which appearances count, not what the scenario asserts, which is the same refinement
      S-022 makes for S-009 through S-013. No amendment is owed.
- [x] Existing tests still pass, unchanged in intent. All 55 tests in `test_validate_skills.py` pass;
      the only existing test edited is `test_a_prose_mention_naming_the_file_counts_as_a_reference`,
      which gained a comment recording why its fixture pins the span decision. Its code is untouched.

## Decisions

**A premise that turned out false: the inline code span half of this task.** The task asks for "the
existing span and fence exclusion", and the acceptance criterion names a span alongside a fence. Only
the fence half is correct, and the span half contradicts three things at once. `S-023`'s "what counts
as a reference" paragraph protects a prose mention naming the file, and the house style writes such a
mention in backticks, which is an inline code span. The existing test
`test_a_prose_mention_naming_the_file_counts_as_a_reference` encodes exactly that with the fixture
"The ceiling is stated in `example.md` beside this skill.", and a span exclusion fails it, so
implementing the task as written would have broken an existing test rather than kept it passing.
And the same exclusion measured over the real tree drops 27 of the 60 lens-filename occurrences in the
twenty shipped bodies, costing `house-review` its only reference to `house-style.md`, which it names
in the span "it is swappable like `house-style.md`". Excluding spans would therefore have needed a
`S-023` amendment, which this task puts out of scope. The asymmetry with `S-022` is real and is not an
inconsistency: a link inside a span is not a link, because its brackets render as literal text and
there is nothing to follow, whereas a filename inside a span is still prose naming the file. The
argument is recorded in `_names_file_outside_fences()`'s docstring and in the conformance matrix, so
the next reader does not close the gap as an oversight.

**A seam left open deliberately: the nine pre-existing `TestLensComposition` tests keep their
`feat-0048` tags.** The three tests added here are tagged `Scenario S-023`; retagging the neighbours
is `chore-0045`'s shape of work and is recorded in the conformance matrix's test row as still open,
narrower than it was.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
