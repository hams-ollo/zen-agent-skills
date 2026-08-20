---
id: bug-0041
title: A typo on the field after source drops the whole provenance block silently, the third instance of that signature in one file
type: bug
status: done
priority: P2
parent: "ROADMAP Epic B #18: provenance convention for folded-in material"
depends_on: [bug-0019]
touched_files:
  - scripts/check-provenance.py
  - tests/test_check_provenance.py
created: 2026-08-20
---

## Problem

`parse_records()` in [`check-provenance.py`](../../scripts/check-provenance.py) drops an entire
provenance block when the field immediately after `source:` is misspelled. The record simply does not
exist as far as the run is concerned, and the run reports success.

Left explicitly out of scope by [`bug-0019`](bug-0019-provenance-check-drops-unreadable-files-silently.md)
and reported by its agent as worth its own file, which is what this is.

**It is the third instance of one signature in a single file**, and that is the argument for taking it
rather than the defect's own size. `bug-0016` closed one, `bug-0019` closed a second on 2026-08-19,
and `bug-0019`'s agent found a fourth variant while fixing the second: with every file unreadable,
`main()` returned 0 printing "No provenance records found", the exact output of a repository with
nothing folded in, so a check reported a correct-looking empty state while its entire input was
invisible. That one is now covered. This one is not.

The shape each time: the tool examines fewer records than it claims and says nothing. What makes this
file keep producing them is that it parses a hand-written block format with no schema, so every field
is optional to the parser and a mistake looks identical to an absence. The provenance convention in
`AGENTS.md` names five required keys, and nothing enforces that count at parse time.

The consequence is specific to what this tool is for. A dropped record is a folded-in file whose
upstream is never re-fetched, never digested, and never compared, so drift in adapted material goes
unreported while `--check` prints a clean summary. That is the only thing standing between the kit and
a silent divergence from the upstream it credits.

## Scope

**In scope:** make a malformed block a reported error rather than an invisible absence.

- A block that opens with `source:` and then fails to parse into a complete record is named, with its
  file and enough of the block to find it, and the run's exit code reflects it.
- Decide and record what "complete" means against the five required keys the provenance convention in
  `AGENTS.md` states (`source`, `author`, `license`, `retrieved`, `sha256`), and the documented
  `status: unlocatable` substitution that replaces two of them.

**Out of scope:**

- Replacing the block format with YAML or JSON. The format is deliberate, it is human-written and
  human-read inside a markdown file, and changing it would touch every skill carrying a provenance
  block. If parsing keeps producing this class after this fix, that is the argument to reopen, and it
  belongs in a task that can weigh it properly.
- The unreadable-file and empty-input paths, both closed by `bug-0019`.
- Network behaviour. This is a parse-time defect and the fix must not require a fetch to detect.
- `AGENTS.md`'s statement of the convention, which is correct and is the reference for what a complete
  record is.

## Implementation notes

Read `bug-0019`'s change before starting. It added an `unreadable` return value and an exit-2 path,
and the natural shape here is to reuse that reporting channel rather than invent a second one: both
are "the tool could not see part of its input", which is exactly the distinction exit 2 already
carries against exit 1.

The test that matters is the one that fails today: a fixture with a block whose second field is
misspelled must change the run's outcome. A test that only asserts a well-formed block still parses
proves nothing, since that already works.

Check the `status: unlocatable` case explicitly. It legitimately omits `retrieved` and `sha256`, so a
naive required-keys check would report every unlocatable record as malformed, which would be a new
instance of the same family in the opposite direction.

## Risks and rollback

Two files in one module, so the more-than-one-module rule does not fire.

The failure direction reverses: today a malformed block is invisible, afterwards it stops the run. If
any block currently in the tree is malformed and has been silently dropped this whole time, this fix
surfaces it as a failure on first run. That is the point, and the closeout should say how many
records the tool sees before and after, because a change in that count is the finding.

Reversible by reverting one commit. This tool is deliberately outside required CI because it needs
network, so nothing else depends on its exit code.

## Decisions

- **"Complete" is decided by placement, not by the field names.** A run whose `source:` line sits
  inside a placement the convention names, a fence tagged `provenance` or an underlined `Provenance`
  docstring section, is a record whatever it collected, and validate() then reports its shortfall
  against the five required keys (or the `status: unlocatable` substitution, unchanged). Outside
  those placements the old content rule stands: at least one other recognised key. That split is
  what lets a mistyped block be reported without `review-depth`'s `source: detected | user` being
  reported with it.
- **Rejected: near-miss detection on the key name.** A mistyped key is one a small edit distance from
  a recognised one; an unrelated field is not. It would have worked on `authr` for `author`, and it
  fails in both directions on cases this tree already contains or invites: `hash:` for `sha256:` is
  a typo no distance threshold calls one, and a template's own `notes:` field is one edit from
  `note:` and is not a typo at all. The threshold would have had nothing behind it, where placement
  is a question `AGENTS.md` already answers.
- **Seam left open: a typo on `source` itself.** `sorce:` inside a `provenance` fence still produces
  no record, because the scan only ever starts at a `source:` line. Same family, same file, and
  deliberately not fixed here: this task scopes to "a block that opens with `source:`". A fence
  tagged `provenance` that contains no `source:` line at all is detectable with the placement
  machinery this change adds, and is the natural next task.
- **Premise checked and left alone: `AGENTS.md` line 155.** It says "the parser requires at least one
  other field". After this change that holds outside a declared placement and not inside one, where a
  lone `source:` line now yields a record reported as missing four fields. The task puts `AGENTS.md`
  out of scope, so the sentence is reported as a finding rather than edited.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [x] A block whose field after `source:` is misspelled is named in the output and changes the exit
      code, proven by a test that fails against the current code.
- [x] A record using `status: unlocatable` still parses and is not reported as malformed, proven by a
      test.
- [x] The closeout states the record count before and after the change, so a previously-dropped block
      is reported as a finding rather than absorbed.
- [x] No network request is made by any test.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
