---
id: bug-0046
title: The provenance scan matches file suffixes case-sensitively, so a file named .MD drops every record it carries and the run says nothing
type: bug
status: done
priority: P2
parent: "ROADMAP Epic B #18: provenance convention for folded-in material"
depends_on: []
touched_files:
  - scripts/check-provenance.py
  - tests/test_check_provenance.py
created: 2026-08-22
---

## Problem

`iter_provenance_files()` selects what to scan with an exact suffix test:

```python
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix in SCAN_SUFFIXES:
                yield path
```

`SCAN_SUFFIXES = (".md", ".py")`. A file whose name an author typed as `.MD` or `.PY` is not
selected, is not read, carries every provenance record it holds out of the run, and is named
nowhere.

Demonstrated against a clean clone of `developer` at `f8e304b`, renaming one file and changing
nothing else:

```text
$ python scripts/check-provenance.py --list | tail -1
8 record(s).

$ mv .agents/rules/review-quality.md .agents/rules/review-quality.MD
$ python scripts/check-provenance.py --list | tail -1
6 record(s).
```

Exit 0 both times. Two records vanished, no line named the file, and the second run reads exactly
like a repository with six fold-ins instead of eight. That is the class this script has now been
fixed for four times:
[bug-0016](bug-0016-provenance-block-blank-line-silent-skip.md),
[bug-0019](bug-0019-provenance-check-drops-unreadable-files-silently.md),
[bug-0041](bug-0041-a-typo-after-source-drops-a-whole-provenance-block.md), and
[bug-0042](bug-0042-a-typo-on-the-source-key-itself-still-deletes-the-block.md). Each of those
four fixed a layer inside a file that was read. This is the layer above them: which files get read
at all, which no task has looked at.

The script states the property it is failing in its own words, in `unsourced_placements()`: the
point of that family of fixes is "that the tool never passes over part of its input without saying
so".

The same defect was closed one directory over on 2026-08-21.
[chore-0055](chore-0055-tmpl-matching-is-case-sensitive-while-markdown-matching-is-not.md)
made `validate-skills.py`'s two suffix tests case-insensitive, and its argument transfers verbatim:
"the case an author typed is not a fact about where a file's links resolve". The case an author
typed is not a fact about whether a file carries a fold-in either. The consequence here is worse
than it was there: in `validate-skills.py` the mismatch moved a file from one reported skipped
count into another, and both counts were printed. Here it removes a file from the run entirely and
no count records it.

Reachability is honestly low. Every file in scope today ends in a lowercase suffix, the four in
`.agents/rules/` and `.agents/skills/` were authored by hand, and no tool in the kit writes an
uppercase suffix. The argument for fixing it is not that it is likely: it is that the identical
rule already exists in the sibling script with the reasoning written out, and that this script's
whole design commitment is to name what it did not read.

## Scope

**In scope:** select scanned files by a case-insensitive suffix comparison, and prove it with a
test.

- Lower the suffix before the membership test, matching `classify_supporting_file()` in
  `validate-skills.py`, which lowers both sides.
- Keep `SCAN_SUFFIXES` written lowercase, and say in a comment that the constant is compared
  against a lowered value, so the next reader does not add `.MD` to the tuple.

**Out of scope:**

- `SCAN_DIRS`. A directory in that tuple that does not exist is skipped silently by the same
  function, and that is a documented policy over two directories that cannot go missing without
  every other gate failing first. Leave it alone; if it is worth a signal, that is its own task.
- Widening `SCAN_SUFFIXES` to any new file kind. That is a scope decision about what counts as
  shipped adapted material, not a case bug.
- The reporting shape. This run already names unreadable files and empty placements; a file simply
  not selected by suffix is not a new bucket, it is a file that should have been selected.

## Implementation notes

The one-line change is `path.suffix.lower() in SCAN_SUFFIXES`. The work is the test, because a test
that renames a real repository file is not available: `collect()` and `iter_provenance_files()` take
a `root`, and `tests/test_check_provenance.py` already builds fixture trees under a temporary root.
Mirror whatever that file already does rather than reaching for the real tree.

Widening the match can only move a file into the scanned set, never out of it, since a name ending
in `.md` in any case has `.md` as its lowered suffix. So the current 8 records are a floor: if the
count changes on the real tree after the fix, a file was being skipped and that is a finding to
report.

## Decisions

**Chosen: case-insensitive, agreeing with `chore-0055`. Rejected: case-sensitive, and rejected
making a case-variant suffix a loud error.** `chore-0055`'s argument transfers without modification
and its rejected alternative fails harder here than it did there: a case-sensitive rule leaves
`review-quality.MD` unscanned exactly as today, so the symptom survives the fix that was supposed to
make it loud. Making a case-variant suffix an explicit error would be loud, but it is a new rule
rather than an agreement between two existing ones, and `bug-0028`'s deliberate-seam rule points at
agreeing with the sibling script rather than inventing a third convention one file away.

**Seam left open deliberately: `_SECTION_RE` still matches `Provenance` case-sensitively, while the
markdown fence info string beside it is lowered before comparison.** So a Python docstring headed
`provenance` is not recognised as a declared placement. That is the same disagreement one layer in,
but closing it would change **which blocks qualify** rather than which files are read, which this
task's bounds exclude. Recorded as a finding for the batch owner rather than fixed here.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] A test builds a fixture tree holding one provenance record in a file whose suffix is
      uppercase, and asserts the record is collected.
- [x] That test fails against the current `iter_provenance_files()`, proven by running it before
      the fix and recording the verbatim output in the closeout.
- [x] `python scripts/check-provenance.py --list` over the real tree still reports 8 records, and
      that output is recorded, so the widening is shown to have changed nothing here.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
