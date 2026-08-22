---
id: bug-0047
title: The two provenance placement detectors disagree about case, so a docstring headed provenance loses the malformed-block safety net
type: bug
status: open
priority: P2
parent: "ROADMAP Epic B #18: provenance convention for folded-in material"
depends_on: [bug-0046]
touched_files:
  - scripts/check-provenance.py
  - tests/test_check_provenance.py
created: 2026-08-22
---

## Problem

`check-provenance.py` recognises two placements, and they disagree about case:

```python
_SECTION_RE = re.compile(r"^[ \t]*Provenance[ \t]*$")        # docstring heading, case-SENSITIVE
fence = fence_match.group(1).lower() if fence is None else None   # fence info string, LOWERED
```

A Python module docstring headed `provenance` or `PROVENANCE` is therefore **not** a declared
placement, while a fenced block tagged ` ```Provenance ` is. The two detectors for the same concept
answer differently on the same input.

**The consequence is not cosmetic, and it is the reason this is a bug rather than a chore.** Placement
is what `bug-0041` and `bug-0042` made load-bearing: a run inside a declared placement gets the
malformed-block safety net, so a typo on the field after `source:`, a typo on the `source` key itself,
and a placement carrying no `source:` line at all are all reported rather than silently dropped.
A docstring whose heading is cased differently falls outside that net entirely and returns to the
pre-`bug-0041` behaviour, silently, at exit 0.

Found by `bug-0046`'s agent while fixing the file-scan half of the same class. It **correctly declined
to fix it**, because the dispatch bounded it to changing which *files* are scanned rather than which
*blocks qualify*, and this changes the latter. Recorded as a deliberate seam in that task's
`## Decisions`.

**This is the third member of one class in three days**, which is the argument for taking it now
rather than filing it as a curiosity: `chore-0055` made the `.tmpl` marker case-insensitive in
`validate-skills.py`, `bug-0046` made `SCAN_SUFFIXES` case-insensitive in this same file, and this is
the same disagreement one layer further in. Each was found only because someone went looking after
the previous one landed.

No file in the kit triggers it today: every provenance docstring heading is currently `Provenance`.

## Scope

**In scope:** make the two placement detectors agree about case, and cover the disagreement.

- Decide which way they agree and record the rejected alternative. `bug-0046` and `chore-0055` both
  chose case-insensitive after argument, and agreeing with them is the least-invention answer under
  `bug-0028`'s deliberate-seam rule. Say so rather than assuming it.
- A test pinning both detectors, failing against the current code in at least one direction.

**Out of scope:**

- Which keys a record needs, the five required fields, and the `status: unlocatable` substitution.
  This changes only whether a region counts as a placement.
- `SCAN_SUFFIXES` and the file scan, closed by `bug-0046`.
- `_KEY_RE`'s `[a-z0-9_]+` restriction, which `bug-0046` also reported. Its consequence is loud (a
  capitalised `Author:` terminates the run and the record is reported as missing a required key)
  rather than silent, and `AGENTS.md` names the keys lowercase, so it is probably correct as it
  stands. If this work shows otherwise, that is a finding to report and a separate task.
- `AGENTS.md`'s statement of the convention, which names the placements qualitatively and stays true
  under either answer. **Confirm that against the text rather than assuming it.**

## Implementation notes

Read `bug-0046`'s `## Decisions` first, and `chore-0055`'s before that. Both weighed the same
question and both recorded why case-insensitive won. A third convention one layer inside the same
file would be the thing to avoid.

The regression to guard against is the mirror of `bug-0046`'s: widening the docstring detector must
not turn some other `Provenance`-looking heading into a placement. Check what a widened match would
newly capture across the real tree before and after, and report the count both ways rather than
asserting no change.

## Risks and rollback

Two files in one module, so the more-than-one-module rule does not fire.

The failure direction reverses, as it did in `bug-0041`, `bug-0042`, and `bug-0046`: a heading that is
silently ignored today starts being parsed, and a malformed block inside it starts stopping the run.
That is the point. Record the record count before and after; `bug-0046` measured 8 records and 0
malformed at its closeout, so that is the number this task starts from.

Reversible by reverting one commit. This tool is deliberately outside required CI because it needs
network, so nothing else depends on its exit code.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [ ] A module docstring headed with a case variant of `Provenance` is treated the same as the exact
      spelling, proven by a test that fails against the current code.
- [ ] A malformed block inside such a docstring is reported rather than dropped, which is the
      behaviour the disagreement currently costs.
- [ ] The fenced-block detector's behaviour is unchanged, proven rather than asserted.
- [ ] The closeout states the record count before and after, and what a widened match newly captures
      across the real tree.
- [ ] No network request is made by any test.
- [ ] The closeout states whether `AGENTS.md`'s provenance convention still reads true unchanged.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
