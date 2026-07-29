---
id: chore-0023
title: Correct two stale claims about install.py, a closed coverage gap and a moved budget figure
type: chore
status: done
priority: P2
parent: "ROADMAP#tooling install.py"
depends_on: []
touched_files:
  - tests/test_install.py
  - docs/spec/install.conformance.md
created: 2026-07-29
---

## Problem

Two documents still describe an `install.py` that no longer exists. Both were noticed while fixing
`bug-0009`. Neither is a code defect: the code is right and the prose about it is stale, which is the
harder kind to notice because nothing fails.

**1. The test suite's docstring claims a gap that `chore-0017` closed.**
[`tests/test_install.py`](../tests/test_install.py) lines 11 to 15 read: "S-009 (an unrecognised tool
is rejected) and S-010 (the platform-dependent default mode) have no test. Both live in `main()`,
which takes no argv, so the CLI layer cannot be driven from a test." That paragraph closes by calling
the injectable entry point "a contract-backed reason" to add.

The reason was acted on. `chore-0017` gave `main()` the optional `argv` parameter, and both tests now
live in the same file as the paragraph denying they exist:
`test_an_unrecognised_tool_is_rejected_before_anything_is_placed` (line 213) and
`test_the_default_mode_suits_the_platform` (line 223). The matrix already records the closure
correctly; only the suite's own header is behind.

**2. The S-014 row's figure is eleven characters out of date.**
[`docs/spec/install.conformance.md`](../docs/spec/install.conformance.md) line 34 records "Confirmed
by execution: `core=2298`, `spine=12489`, `all=14262`". A run on 2026-07-29
(`python scripts/install.py --dry-run --home ./.tmp/zen-home`) reports `all=14273`. `core` and `spine`
are unchanged.

The drift is understood and benign: the description edits in `bug-0007`, `bug-0008`, and `chore-0022`
moved the total. `chore-0022`'s outcome note already names the eleven characters as the
`human-handoff` description edit from `bug-0008`, and records that the figure moving by 11 rather than
~250 is what proved `description_of()` stops at the new `license:` key instead of absorbing it. So the
number is evidence, and an evidence figure nobody can reproduce is worse than none.

## Scope

**In scope:** rewrite the stale docstring paragraph in `tests/test_install.py` so it records that the
gap was closed and by what; re-anchor the S-014 row's `all` figure to 14273 and date the measurement.

**Out of scope:**

- Any change to `scripts/install.py`, to any test body, or to any assertion. Both edits are prose.
- The docstring's second constraint (`MANIFEST` is module-level, so each test redirects it). Verified
  still true: `install.py` line 54 still defines it at module scope and the suite still redirects it in
  11 places. Leave that paragraph alone.
- The conformance file's test-coverage table and the notes under it, which already credit `chore-0017`
  correctly and need nothing.
- Re-measuring `core` or `spine`, which the same run confirms unchanged.

## Implementation notes

- **Rewrite the docstring paragraph, do not delete it.** The file's opening paragraphs are a short
  history of the suite (characterization under `feat-0027`, promoted by `feat-0029`), and the stale
  paragraph is the next beat in it: the contract named a gap, and the gap was closed. Deleting it loses
  the fact that the coverage was argued for on contract grounds before it was written. Recording the
  closure keeps the argument and removes the false present-tense claim.
- Name the two tests in the rewrite, so a reader who arrives at the docstring believing the old claim
  can check it in the same file.
- **Date the budget figure in the row itself**, not in a footnote. The number moves whenever a
  `description` is edited, so an undated figure invites exactly this drift again. Name the run that
  produced it, and keep the existing sentence about `description_of()` stripping the block-scalar
  indicator, which is a separate and still-correct observation.
- Prior art for the phrasing: `chore-0022`'s outcome section, which records a corrected premise rather
  than quietly replacing it.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py"

- [x] The `tests/test_install.py` docstring no longer states that S-009 and S-010 have no test, and
      credits `chore-0017` and the injectable `argv` for closing it.
- [x] The rewritten paragraph names both covering tests by their function names.
- [x] The docstring's `MANIFEST` paragraph and the `feat-0027`/`feat-0029` history are unchanged.
- [x] The S-014 row reads `all=14273` and carries the date the figure was measured.
- [x] `core=2298` and `spine=12489` are unchanged, and `python scripts/install.py --dry-run --home
      ./.tmp/zen-home` reproduces all three.
- [x] No file under `scripts/` changed, and no test assertion changed.
- [x] `python .tasks/validate.py` passes.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in the `AGENTS.md` conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.

## Outcome (2026-07-29)

Both corrections landed as prose only. `python -m unittest discover -s tests -p "test_*.py"` reports
84 tests, OK, and the dry-run reproduces `core=2298`, `spine=12489`, `all=14273` exactly as the row
now claims.

The docstring rewrite moved the paragraph into the past tense and kept the argument that produced the
fix, so the file still records that the coverage was demanded on contract grounds before it was
written. It gained one sentence the original could not have: S-010 is covered on the running
platform's branch only, pointing at the conformance report where that is explained, so a reader who
arrives at the docstring is not left believing the coverage is more complete than it is.

**Two adjacent things were checked and deliberately not changed.** The docstring's second constraint
(`MANIFEST` is module-level, so every test redirects it) is still true: `install.py` line 54 defines
it at module scope and the suite redirects it in 11 places. And `CHANGELOG.md` mentions `14,262`
twice, in the `bug-0007` and `feat-0033` entries. Those are not drift. The changelog is an
append-only ledger and both figures were correct on the day they were written, so editing them would
falsify the record of what was measured when. The number needed dating, which is what the conformance
row now carries, rather than a repo-wide find-and-replace.

The `doc-sync` obligation was satisfied by inspection rather than by a full pass: this change touches
a test docstring and a conformance report, both maintainer-facing, and grepping the figures found no
occurrence in any reader-facing document (`README.md`, `docs/CATALOG.md`, `docs/GETTING-STARTED.md`
all state no budget number).

One piece of authoring bookkeeping was corrected in passing: `.tasks/.scaffold.json` still carried
`id_high_water` from 2026-07-23 (`bug: 2, feat: 29, chore: 17`) while the backlog had reached
`bug-0009`, `feat-0034`, and this task. The next author reading it would have been handed a colliding
id. Now `{bug: 9, feat: 34, chore: 23, epic: 0}`.
