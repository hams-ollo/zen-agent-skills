---
id: bug-0016
title: A blank line inside a provenance block makes the record vanish, and the run still exits 0
type: bug
status: done
priority: P2
parent: "ROADMAP Epic B #18: provenance convention for folded-in material"
depends_on: []
touched_files:
  - scripts/check-provenance.py
  - tests/test_check_provenance.py
created: 2026-08-06
---

## Problem

`parse_records()` in [`check-provenance.py`](../../scripts/check-provenance.py) ends a record at the
first blank line, and a record that ends before it has collected its required fields is discarded by
the qualifying test rather than reported. So a provenance block whose `source:` is separated from its
remaining fields by one blank line is **skipped entirely and silently**.

Measured 2026-08-06 during `feat-0043`'s reconciliation, against a probe file carrying one otherwise
valid block with a blank line after `source:`:

```
No provenance records found. Nothing folded in is recorded, which is
either correct or a sign a fold-in skipped the convention in AGENTS.md.
exit=0
```

Removing the blank line and changing nothing else gives `1 up to date, 0 drifted, 0 unlocatable, 0
error(s).` and exit 0. So one blank line is the difference between a source being checked and a
source being invisible, and both outcomes report success.

**This contradicts the script's own stated design.** Its docstring says the grammar requires at least
one recognized field beyond `source:` "so a typo cannot hide a fold-in from the check", and a record
missing only `author:` is correctly reported as malformed with exit 2. The blank-line case takes the
opposite branch and reports nothing.

**Why it matters more than its size suggests.** The whole point of the check is that upstream
movement becomes a check result rather than a discovery. A fold-in that silently drops out of the
record set is worse than one that was never recorded, because the run keeps reporting a clean count
that a reader has no reason to doubt. This is the same failure shape as the over-skipping risk
`bug-0015` guarded against: a check that switches part of itself off and still exits 0.

**Not currently hiding anything.** All eight records in the tree today are contiguous, confirmed by
`--list` reporting 8 records across 7 files, so this is latent rather than live.

## Scope

**In scope:** make a blank line inside a block either not terminate the record, or terminate it in a
way that is **reported** rather than discarded; a test for the blank-line case; a test that whatever
rule is chosen still reports a genuinely malformed record rather than skipping it.

**Out of scope:** the block format itself, which is settled and documented in the conventions section
of `AGENTS.md` and backfilled into seven files; re-fetching or re-digesting anything; adding the
check to CI, which `feat-0043` deliberately left out because it needs the network.

## Implementation notes

The fence gives a natural answer: inside a ` ```provenance ` fence the terminator is the closing
fence, not a blank line, so a fenced block can simply read to its fence. The hook docstrings and the
rules lens do not have a fence, so they still need a rule, and the two placements should not diverge
into two grammars.

**Prefer reporting over guessing.** `feat-0043`'s decision log already chose to report a partial
record as malformed rather than infer intent, and this should match: a block that looks like a
provenance record but does not parse is a finding, not a non-event. The exit code for that case is
already 2 and does not need a new one.

Whatever rule is chosen, state it in the `AGENTS.md` convention only if it changes what an author
must write. If the fix is purely that the parser tolerates a blank line, the convention is unchanged
and should not be edited, since every future fold-in reads it.

## Decisions

- **Rejected: reporting the blank-terminated run as malformed instead of tolerating the blank.** The
  only run a blank line can leave partial is a `source:`-only run, because a run carrying any second
  recognised field already qualifies and is already reported. **This was a judgment call, not a
  forced hand, and an earlier draft of this entry overstated it.** Reporting `source:`-only runs *in
  general* is the `review-depth` collision (`source: detected | user`), but reporting only the
  blank-terminated ones is not: that line is terminated by `changeset:`, a non-blank field, so a
  blank-terminated rule never sees it. Measured during verification, the rejected alternative fires
  zero false positives on the real tree. Tolerating still wins on the merits, because it actually
  fetches and digests the block where reporting would only flag it, and it leaves what an author must
  write unchanged, so the `AGENTS.md` convention was deliberately not edited.
- **Rejected: making the closing fence the terminator for fenced blocks.** It reads naturally for a
  skill's ` ```provenance ` footer but gives the unfenced placements (hook module docstrings, the
  rules lens) a second rule. Blank-line transparency covers all three placements with one grammar.
- **Seam left open: a block whose fields are all misspelled is still silently dropped.** Qualifying
  on "at least one other recognised key" is what keeps `review-depth` out, so a block of
  `source:` plus `autor:` plus `licence:` still collects nothing. Closing it needs a different
  discriminator (the `provenance` fence tag is the obvious candidate) and that reintroduces the
  two-grammar split rejected above. Left as a known bound, not an oversight.

## Risks and rollback

The risk is over-widening: a grammar that reads to end of file looking for missing fields would start
pulling unrelated `source:`-shaped lines into records, which is the collision `feat-0043` already hit
against `review-depth`'s output template, where `source: detected | user` is an unrelated field. Pin
that case as a test before changing the terminator, since it is the reason the current grammar is
tight.

Rollback is one revert; the block format on disk does not change.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/validate-skills.py && python .tasks/validate.py --strict

- [x] A test pinning a block with a blank line between `source:` and its remaining fields, failing
      against the current parser.
- [x] That block is either parsed as a record or reported as malformed with a non-zero exit; it is
      not silently absent.
- [x] A test proving `review-depth`'s `source: detected | user` line is still **not** collected,
      so the fix does not reopen the collision that motivated the current grammar.
- [x] A test proving a record missing a required field is still reported rather than skipped.
- [x] `python scripts/check-provenance.py --list` still reports 8 records across 7 files on the
      unmodified tree.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason.
- [x] File moved to `.tasks/done/`, `status: done`, **with its relative links re-anchored for the
      extra directory level**; one dated line added to `CHANGELOG.md` referencing this task id.
