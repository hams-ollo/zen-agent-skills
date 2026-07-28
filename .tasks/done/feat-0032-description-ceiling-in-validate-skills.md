---
id: feat-0032
title: Make validate-skills.py error on a description over the harness limit, and measure it correctly
type: feat
status: done
priority: P0
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [bug-0005]
spec: docs/spec/validate-skills.md
scenarios: [S-017, S-018]
touched_files:
  - docs/spec/validate-skills.md
  - scripts/validate-skills.py
  - tests/test_validate_skills.py
  - docs/spec/validate-skills.conformance.md
created: 2026-07-28
---

## Problem

[`validate-skills.py`](../../scripts/validate-skills.py) defines `MIN_DESC_CHARS = 40` and no upper bound.
Both harnesses [`install.py`](../../scripts/install.py) targets cap `description` at 1024 characters, so
the kit-level lint whose whole job is to catch a malformed `SKILL.md` before it is distributed is blind
to the one field limit the distribution targets actually enforce. `bug-0005` found five shipped skills
over that limit, none of which produced a finding.

There is a second defect underneath, found while measuring the first, and the ceiling cannot be correct
without it. `parse_frontmatter()` matches `^(\w[\w-]*):\s*(.*)$` and folds continuation lines, which
means a YAML block scalar is captured with its indicator: a description written as

```yaml
description: >-
  Turns the current session's context into ...
```

parses as the string `">- Turns the current session's context into ..."`. Four of the five over-limit
descriptions are block scalars, so the validator reports each of them 3 characters longer than a YAML
parser would, and `init-worktracking`, whose description is a single plain line, is the only one of the
five where the validator's number and the real number agree. A ceiling built on that measurement would
reject a description the harness accepts and would report a length no other tool agrees with.

The same three-character defect ships further than this script: `build-adapters.py` has a byte-identical
parser, so every generated Cursor and VS Code adapter for those four skills carries `>- ` inside its
description. That is filed separately as `bug-0006`, because it is a divergence from a different
contract (`build-adapters.md` S-002) and fixes a different output.

## Scope

**In scope:** add `MAX_DESC_CHARS = 1024` raised as an **error** naming the harness limit; strip a
leading YAML block-scalar indicator in `parse_frontmatter()` so the measured description is the
scalar's value; amend [`docs/spec/validate-skills.md`](../../docs/spec/validate-skills.md) with the two
scenarios first; add covering tests; update the conformance matrix and its test-coverage table.

**Out of scope:** trimming any description, which is `bug-0005` and must land first. Fixing
`build-adapters.py`, which is `bug-0006`. Raising `MIN_DESC_CHARS`. Any change to the warning-versus-error
disposition of the existing checks.

## Implementation notes

- **Amend the spec first, then the code, then the tests.** This is the order `chore-0013` and
  `feat-0026` used, and the reason is that a scenario written after the code tends to restate the
  implementation rather than the condition. `S-014` is the standing evidence: it only caught a live
  divergence once it stated the condition semantically.
- The spec amendment needs the author's explicit instruction, which this task carries: the author
  directed it in the session brief on 2026-07-28. Record that in the spec's amendment note the way the
  `bug-0003` amendment did, and re-approve. `docs/spec/` is otherwise human-owned.
- Two scenarios, because they are independently observable and one can hold while the other fails:
  - **S-017**: a description over the ceiling is an **error** and exits non-zero. An error rather than
    a warning because the harness limit is not advisory, and because the existing thin-description
    warning has been in the tree for days without anyone acting on it.
  - **S-018**: the length checked is the scalar's value, exclusive of a YAML block-scalar indicator, so
    the number the validator reports is the number the harness measures.
- Put the harness limit in the message, not just the number. A message reading "1104 > 1024" tells the
  author what to do; one reading "description too long" does not.
- The block-scalar strip belongs in `parse_frontmatter()` rather than at the call site, because
  `MIN_DESC_CHARS` reads the same value and the two must not disagree about what the description is.
  Handle `>`, `>-`, `>+`, `|`, `|-`, and `|+`. A plain scalar must be untouched, which the
  `init-worktracking` case makes checkable.
- Tests: one for the ceiling firing as an error, one negative case at or just under the boundary, and
  one asserting a block-scalar description measures its value. Tag each with its scenario id, as the
  rest of that suite does.

## Risks and rollback

Required: this touches the parser every check in the script reads, not only the new one.

The failure mode to watch is a stripping rule that eats real content, for example a description
legitimately beginning with `|` or `>`. That would silently shorten a description rather than error, so
the negative test on a plain scalar is the guard, not an optional extra. Reverting is one commit; the
spec amendment reverts with it, and no persisted format or manifest is involved.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py"

- [x] `MAX_DESC_CHARS = 1024` exists and a description over it is appended to `errors`, not `warnings`.
- [x] The error message names both the measured length and the 1024 harness limit.
- [x] `parse_frontmatter()` strips a leading `>`, `>-`, `>+`, `|`, `|-`, or `|+` indicator, and leaves a plain scalar unchanged.
- [x] The four block-scalar descriptions each measure exactly 3 fewer characters than before the fix.
- [x] `docs/spec/validate-skills.md` carries S-017 and S-018, and records the amendment and its authority.
- [x] `docs/spec/validate-skills.conformance.md` has a row for each new scenario and lists both in the test-coverage table.
- [x] New tests fail against the pre-fix script, so they test the change rather than restate it.
- [x] `python scripts/validate-skills.py` exits 0 with 19 skills, 0 errors, 0 warnings.
- [x] `python -m unittest discover -s tests -p "test_*.py"` exits 0.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in the `AGENTS.md` conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.

## Outcome (2026-07-28)

`MAX_DESC_CHARS = 1024` is an error, and `parse_frontmatter()` now strips a block-scalar indicator, so
the length the validator reports is the length a harness measures. Spec first, then code, then tests, in
that order. Five tests added, all confirmed to fail against the pre-fix script before it changed.

Proven by execution rather than by inspection: a copy of the real skills tree with one description
padded past the bound exits 1 with `description is 1173 chars, over the 1024-char limit both target
harnesses enforce`. The suite went from 55 tests to 60.

**The boundary and the negative cases are where the value is.** The ceiling test pairs "over the limit
errors" with "exactly at the limit does not", because an off-by-one here would reject a legal
description and the author would have no way to tell which of the two rules was wrong. The S-018 tests
matter more: over-eager stripping would shorten a description silently instead of failing, which is a
defect with no symptom at all, so a plain scalar and prose containing angle brackets are both pinned.
The strip is anchored to the head of the field line and bounded to one substitution for that reason.

**S-018 exists because fixing S-017 alone would have shipped a wrong check.** The parser counted the
`>- ` indicator as description content, so four of the five over-limit skills measured three characters
high. That is small enough to look like rounding and large enough to reject a description at 1023. The
lesson is the one `S-014` already taught this contract: a scenario that states the condition
semantically ("measured as a harness would measure it") catches what a scenario restating the
implementation would not.

The same defect in `build-adapters.py`'s copy of this parser was filed and fixed as `bug-0006`. Both
copies now carry an identical `BLOCK_SCALAR_RE` and a comment saying so. **That is a patch, not a fix:
there are now three near-copies of this frontmatter-reading shape in `scripts/` (`install.py` gained a
narrow third one in `feat-0033`), and this defect had to be found once per copy.** Unifying them behind
one helper is a real recommendation and deliberately not done here, since `scripts/` is not shipped to
adopters so the change is safe but structural.
