---
id: bug-0047
title: The two provenance placement detectors disagree about case, so a docstring headed provenance loses the malformed-block safety net
type: bug
status: done
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

## Decisions

**Chosen: case-insensitive for both markers, agreeing with `bug-0046` and `chore-0055`. Rejected:
narrowing the fenced detector so both agree case-sensitively.** The rejected alternative was taken
seriously, and it does not survive being written out for this file specifically. Its appeal is that a
convention accepting one spelling is easier to check, but it buys no loudness at all: a mis-cased
marker would still be *skipped* under it, not *reported*, so the silence this bug is filed for
survives the fix meant to end it, and it spreads. Narrowing the fence removes coverage that exists
today, because a malformed block inside a ```Provenance fence is reported now and would go back to
being dropped at exit 0. Every bug in this file's history (`bug-0016`, `bug-0019`, `bug-0041`,
`bug-0042`, `bug-0046`) is one silent drop, and each fix widened what the scanner can see. This is the
first one where the strict answer would have moved the other way, which is the argument against it.
Note that `AGENTS.md` genuinely does not settle it: it names the docstring section `Provenance` and
the fence tag `provenance`, so under a case-sensitive-both answer the two markers would still be
spelled differently and would still not "agree".

**Premise checked, held, and found incomplete in a load-bearing way.** Every factual claim in the
task file is true: the two detectors do disagree only about case, `--list` reports 8 records with 0
malformed before and after, and every provenance docstring heading in the tree is `Provenance`
exactly. But the two-line excerpt in `## Problem` shows only `_SECTION_RE`, and a docstring placement
is not the heading: it is an *underlined* heading that is not inside an open fence. The underline is
what bounds this widening, and it is a stronger guarantee than the measurement. Widening the heading
cannot promote prose that merely says the word, and cannot reach into a fenced documentation example,
because the fence branch runs first. `test_a_heading_with_no_underline_opens_nothing_in_any_case` and
`test_a_mis_cased_heading_inside_someone_elses_fence_is_still_ignored` hold both bounds.

**Seam left open deliberately: `_KEY_RE` stays case-sensitive, and this work confirmed it should.**
After this change the file is case-insensitive about file suffixes and about both placement markers,
and still case-sensitive about field keys, which looks like the same class one layer further in. It
is not. A capitalised `Author:` exits 2 with `missing required field(s): author, license, retrieved,
sha256`, so its consequence is loud where every member of this family is silent. It is worth noting
that the message names the shortfall rather than the capitalised key that caused it, so the
diagnostic is worse than `bug-0041`'s, but a loud wrong-sounding error is still a different class
from a clean exit 0. Widening it would be a new rule rather than an agreement between two existing
ones.

**Seam left open deliberately: `AGENTS.md` never says the docstring heading needs an underline.** Its
sentence reads true unchanged after this fix, which is what this task asked, but it says "a
`Provenance` section of its module docstring" and the underline is only implicit in the word
"section". An author who follows those words literally and omits the underline gets this same family's
silent failure, at the exact spelling. Left alone because this task scopes `AGENTS.md` out and the
document is a contract; reported as a finding for a separate task.

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

- [x] A module docstring headed with a case variant of `Provenance` is treated the same as the exact
      spelling, proven by a test that fails against the current code.
- [x] A malformed block inside such a docstring is reported rather than dropped, which is the
      behaviour the disagreement currently costs.
- [x] The fenced-block detector's behaviour is unchanged, proven rather than asserted.
- [x] The closeout states the record count before and after, and what a widened match newly captures
      across the real tree.
- [x] No network request is made by any test.
- [x] The closeout states whether `AGENTS.md`'s provenance convention still reads true unchanged.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
