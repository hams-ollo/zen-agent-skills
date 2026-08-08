---
id: bug-0020
title: The --check unknown verdict tells an adopter to re-install, which cannot fix an unrecorded lens
type: bug
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [bug-0018]
touched_files:
  - scripts/install.py
  - tests/test_install.py
  - docs/INSTALL.md
created: 2026-08-07
---

## Problem

`--check` reports `unknown` for an entry carrying no recorded digests, and every place it says so
names the same remedy: re-install. In [`install.py`](../scripts/install.py), `_check_entry()` returns
*"installed before digests were recorded, so whether it is current is unknown. Re-install to
establish a baseline."*, `check()`'s summary repeats *"Re-install to establish one."*, and
[`INSTALL.md`](../docs/INSTALL.md)'s report table carries the same sentence in its `unknown` row.

That remedy is correct for a **derived** entry and, once `bug-0018` lands, false for the **adopted**
one. `bug-0018` makes a re-install of an unrecorded rules module deliberately preserve every file and
record nothing, because with no baseline an edited file cannot be told from an untouched one and the
two errors do not cost the same. So the adopter follows the instruction, the run preserves, the entry
stays `unknown`, and `--check` prints the same instruction again. **The one route that does establish
a baseline there is `--replace-adopted`, which none of these three messages mentions.**

The failure is small and is exactly the shape this tool keeps being bitten by: an instruction that
looks actionable, produces no error, and changes nothing. `--check` exits 2 either way, so nothing
else surfaces it, and an adopter who trusts the message concludes the tool is broken rather than that
they were told the wrong move.

Measured 2026-08-07 against the base branch, before `bug-0018` lands, so these line numbers shift
when it does; the symbols are the stable reference:

| Where | Symbol | Line |
|---|---|---|
| the returned verdict | `_check_entry()`, the `if not recorded` branch | [`install.py:708`](../scripts/install.py) |
| the run summary | `check()`, the `if counts["unknown"]` print | [`install.py:790`](../scripts/install.py) |
| the module docstring | the "Staleness, and why --check exists" section | [`install.py:34`](../scripts/install.py) |
| the reader-facing table | the `unknown` row | [`INSTALL.md:70`](../docs/INSTALL.md) |

## Scope

**In scope:** make the `unknown` verdict name a remedy that works for the entry it is describing. An
adopted entry is already classified in the record by name, and `_check_entry()` already branches on
`ADOPTED_ENTRY_NAMES` further down, so the classification does not need deriving again.

**Out of scope:**

- **Exit codes.** `unknown` stays a 2. The state is still unanswerable; only the advice is wrong.
- **Making a re-install record a baseline for an unrecorded adopted module.** That is `bug-0018`'s
  decision and its reasoning is recorded there: recording the kit's digests for files the run did not
  place would claim a baseline nobody observed, and `--check` would then report `ok` for it.
- **Amending [`install.md`](../docs/spec/install.md).** `--check` reaches no scenario and no surface
  row in that contract today, which is `chore-0033`'s backlog to drain, and this task carries no
  author instruction to amend. `chore-0031` declined on exactly this ground and recorded why. If
  `chore-0033` lands first and pins `--check`'s output at contract level, read what it wrote rather
  than assuming this message is unconstrained.
- **The other two `check()` messages.** "the record is gone: re-install to establish a baseline" for
  a home with nothing recorded, and "Re-install to refresh it" for a diverged entry, are both still
  correct. Do not sweep them up.

## Implementation notes

**Prior art to mirror, in the same function.** `_check_entry()` already asks
`if entry.get("name") in ADOPTED_ENTRY_NAMES:` to decide which comparison the entry deserves. The
`unknown` branch runs *before* that check and is the only classification that ignores it. Making it
ask the same question is the smallest change that removes the wrong advice, and it keeps one place
answering "is this material adopted".

**`check()`'s summary needs to know whether any unknown entry was adopted**, and today it has only
`counts`, which is keyed by status and not by kind. It prints one line per status, so a run whose
unknown entries are all derived should still say re-install and a run with an adopted one among them
must name `--replace-adopted`. Track it in the loop rather than re-deriving it from the manifest a
second time.

**The wording is pinned in two existing assertions, and a name-scoped fix leaves both green.** That
is worth knowing before you conclude the change is unproven:
[`test_a_manifest_written_before_this_change_reports_unknown_not_current`](../tests/test_install.py)
asserts `"re-install to establish a baseline"` against the whole run output, which the derived
entries in that fixture still produce, and
[`test_an_empty_digest_map_is_no_baseline_at_all`](../tests/test_install.py) passes an entry with no
`name` key at all, so it is not adopted and its message is unchanged. Neither is a regression proof
for this bug. **A new test is therefore load-bearing**, and it has to assert on the rules entry's own
line rather than on the presence of a string anywhere in the output: the derived entries print the
old sentence in the same run, so an output-wide `assertIn` passes before and after the fix and proves
nothing. `StalenessCheckTests._status()` already exists to read one named entry's verdict out of the
report, for this reason.

**Do not delete the re-install advice from the shared text and leave the adopted case with nothing.**
An adopted entry with no baseline still has a real remedy, and a message that only says the state is
unknown is a smaller version of the same defect.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] A test asserting the rules entry's own `unknown` line names `--replace-adopted`, read per entry
      and not as a substring of the whole report, and failing against the current message.
- [ ] A test proving a derived entry with no baseline still says re-install, so the fix is scoped to
      the adopted case rather than swapping one wrong remedy for another.
- [ ] The `check()` summary line names the right remedy for the run it is summarising, covered by a
      test over a run whose unknown entries include the rules module.
- [ ] The module docstring and [`INSTALL.md`](../docs/INSTALL.md)'s `unknown` row agree with the code.
- [ ] Existing tests still pass, unchanged in intent. The two assertions named above are expected to
      stay green; if either needs editing to pass, the change has reached further than this task.
- [ ] `--check`'s exit codes are unchanged: an unknown entry is still a 2.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason.
- [ ] File moved to `.tasks/done/`, `status: done`, **with its relative links re-anchored for the
      extra directory level**; one dated line added to `CHANGELOG.md` referencing this task id.
