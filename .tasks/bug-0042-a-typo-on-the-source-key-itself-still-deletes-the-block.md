---
id: bug-0042
title: A typo on the source key itself still deletes the whole block, and so does a provenance fence carrying no source line
type: bug
status: open
priority: P2
parent: "ROADMAP Epic B #18: provenance convention for folded-in material"
depends_on: [bug-0041]
touched_files:
  - scripts/check-provenance.py
  - tests/test_check_provenance.py
created: 2026-08-20
---

## Problem

[`bug-0041`](done/bug-0041-a-typo-after-source-drops-a-whole-provenance-block.md) closed the case
where the field **after** `source:` is misspelled. Two siblings survive it, both reported by its agent
and both confirmed against the fixed code:

```text
a block whose own key is misspelled (sorce:)      -> 0 records, exit 0
a provenance-tagged fence with no source: line    -> 0 records, exit 0
```

The cause is one line of control flow rather than two defects. `parse_records()` only ever begins a
run at a line whose key is exactly `source`, so a block that never produces that token is not
examined at all, whatever placement it sits in.

**This is the fourth and fifth instance of one signature in a single file**, after `bug-0016`,
`bug-0019`, and `bug-0041`. The shape each time: the tool examines fewer records than it claims and
says nothing. The consequence is the one that makes this file worth hardening at all, a folded-in file
whose upstream is never re-fetched while the run prints a clean summary.

What makes this cheap now is that `bug-0041` added `declared_lines()`, which already marks every line
inside a placement the convention names. The question "is there a provenance placement here that
produced no record" is answerable from that machinery and was not answerable before.

## Scope

**In scope:** a declared provenance placement that yields no record is reported, rather than being
indistinguishable from a file carrying no provenance at all.

- Drive detection from the placement rather than from the `source` token, reusing `declared_lines()`
  as `bug-0041` left it. Do not add a second scanner.
- Both shapes in one fix, since they are one cause: a misspelled `source` key, and a placement with no
  `source:` line at all.
- Decide and record what the run should say when a placement contains a key that is close to `source`
  as against one that is nothing like it, since the first is a typo and the second may be a placement
  opened by mistake.

**Out of scope:**

- Replacing the block format with YAML or JSON, held out by `bug-0041` for the reasons recorded there
  and unchanged by this.
- The non-provenance `source:` line in `review-depth/SKILL.md`, which is correctly ignored and must
  stay ignored. It is the regression fixture, not a target.
- Network behaviour. This is a parse-time defect and the fix must not require a fetch to detect.
- The provenance convention in `AGENTS.md`, amended at `bug-0041`'s closeout and correct as it stands.

## Implementation notes

Read `bug-0041`'s change first, specifically `declared_lines()` and the reason placement was chosen
over near-miss detection. That decision is recorded in its `## Decisions` section and this task is
downstream of it: reversing it here would leave two disagreeing rules in one parser.

The trap to check explicitly is the empty placement. A skill that opens a provenance fence and writes
nothing in it yet is plausibly work in progress rather than a defect, and a rule that fails the run on
it may be wrong. Decide which, and say so, rather than taking the strict reading by default.

## Risks and rollback

Two files in one module, so the more-than-one-module rule does not fire.

The failure direction reverses, as it did in `bug-0041`: a placement that is silently ignored today
starts stopping the run. Record the record count before and after, because a change in that count is
the finding rather than a side effect. `bug-0041` measured 8 records and 0 malformed at closeout, so
that is the number this task starts from.

Reversible by reverting one commit. This tool is deliberately outside required CI because it needs
network, so nothing else depends on its exit code.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [ ] A block whose own key is misspelled (`sorce:`) inside a declared placement is named in the
      output and changes the exit code, proven by a test that fails against the current code.
- [ ] A declared placement carrying no `source:` line is handled per the decision recorded above,
      proven by a test either way.
- [ ] `review-depth/SKILL.md`'s non-provenance `source:` line still contributes no record, proven
      against the real file rather than a fixture alone.
- [ ] The fix reuses `declared_lines()` rather than adding a second scanner.
- [ ] The closeout states the record count before and after.
- [ ] No network request is made by any test.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
