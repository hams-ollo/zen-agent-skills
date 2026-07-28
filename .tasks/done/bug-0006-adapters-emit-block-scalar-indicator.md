---
id: bug-0006
title: Stop generated adapters emitting the YAML block-scalar indicator inside the description
type: bug
status: done
priority: P1
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
spec: docs/spec/build-adapters.md
scenarios: [S-002]
touched_files:
  - scripts/build-adapters.py
  - tests/test_build_adapters.py
  - docs/spec/build-adapters.conformance.md
created: 2026-07-28
---

## Problem

`split_frontmatter()` in [`build-adapters.py`](../../scripts/build-adapters.py) matches
`^(\w[\w-]*):\s*(.*)$` and folds continuation lines, so a YAML block scalar is captured with its
indicator still attached. Four shipped skills write their description as `description: >-`, and for
each of them every generated adapter emits:

```
description: ">- Turns the current session's context into a self-contained, ..."
```

The four affected skills are `agent-handoff`, `doc-author`, `doc-revise`, and `human-handoff`. Each
generates two adapters, so eight of the 38 files a full run produces carry it.

This diverges from [`build-adapters.md`](../../docs/spec/build-adapters.md) S-002, which says the adapter
opens with the skill's `description`. `">- Turns ..."` is the scalar's serialisation, not its value, so
no spec amendment is needed: the contract already says what should happen.

The reason it survived is worth recording. `bug-0001` already fixed a defect in this exact field, making
the description JSON-serialised so a colon or quote could not break the adapter's own frontmatter. That
fix made the output *well-formed*, which is what both the tests and the eye check, and it made this
defect harder to see rather than easier: `">- Turns ..."` is valid YAML holding wrong content. Neither
`build-adapters.py --dry-run` nor `validate-skills.py` reports anything, because nothing is malformed.

`feat-0032` fixes the same three-character defect in `validate-skills.py`'s copy of this parser. The two
are filed separately because they diverge from different contracts and produce different wrong outputs,
but they share a root cause: two hand-maintained copies of the same frontmatter parser, which is the
duplication the kit has been bitten by twice before.

## Scope

**In scope:** strip a leading block-scalar indicator in `split_frontmatter()` so the emitted description
is the scalar's value; add a covering test; record the fix in the conformance matrix's S-002 row.

**Out of scope:** amending `build-adapters.md`, which already specifies the correct behavior. Unifying
the two parsers into a shared module, which is a real question (see below) but a larger change than a
bug fix should carry. Any change to the JSON serialisation `bug-0001` introduced, which is correct and
independent.

## Implementation notes

- Match `feat-0032`'s handling exactly, including which indicators are recognised (`>`, `>-`, `>+`, `|`,
  `|-`, `|+`) and the rule that a plain scalar is untouched. Two copies that differ are worse than two
  copies that agree, and the next person to touch either needs to see they are the same fix.
- **Do not unify the two parsers in this task, but state the finding.** Each script's parser is a
  deliberately small local helper and the kit has no shared module for them, so introducing one is a
  structural change with its own trade-offs. The observation to carry forward is that this defect
  existed in two places at once and had to be found twice, which is the same shape as the rules-module
  defect. Worth a roadmap entry, not a drive-by refactor.
- The test's oracle is the emitted adapter content, not the parser's return value. A unit test on
  `split_frontmatter()` would pass on the value while the file on disk still carried the indicator if
  an emitter ever changed; asserting on what is written is what the scenario is about.
- Use a fixture skill whose description is a block scalar. Confirm the test fails against the current
  script before fixing it, since a test written after the fix proves only that the code runs.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py"

- [x] A block-scalar description emits with no `>-` prefix in either adapter.
- [x] A plain-scalar description is emitted unchanged.
- [x] The new test fails against the pre-fix `split_frontmatter()`.
- [x] `docs/spec/build-adapters.conformance.md`'s S-002 row records the divergence and its fix.
- [x] `python scripts/build-adapters.py --dry-run` exits 0 with 38 adapter files for 19 skills.
- [x] `python -m unittest discover -s tests -p "test_*.py"` exits 0.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in the `AGENTS.md` conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.

## Outcome (2026-07-28)

`split_frontmatter()` now strips the indicator, so the eight affected adapter files (four skills, two
targets each) carry the description's text instead of `">- Turns the current session's ..."`. Three tests
added, all confirmed to fail against the pre-fix script. No spec amendment: S-002 already said the
adapter opens with the skill's `description`, and the indicator was never part of that value.

**The oracle was chosen against how this hid.** The pre-existing S-002 test asserted that
`description:` appeared in each adapter, which is true of the broken output too, so the new test asserts
what follows the colon in the file that gets written. That is also why it targets the emitted file
rather than the parser's return value: the parser is now correct, and an emitter change could
reintroduce the symptom without the unit test noticing.

Worth recording for whoever reads the two conformance matrices together: `bug-0001` had already fixed a
defect in this same field, JSON-serialising the description so a colon or quote could not break the
adapter's own frontmatter. That fix made the output well-formed, and well-formed is what both the tests
and a reader check, so the remaining defect became valid YAML carrying the wrong value. A fix that
removes the visible failure mode can make the neighbouring one harder to see.

The unification of the now three near-copies of this parser in `scripts/` is recommended and out of
scope here, as the task said. The finding this closes is the argument for it: one defect, two
independent discoveries, and a third copy added the same day.
