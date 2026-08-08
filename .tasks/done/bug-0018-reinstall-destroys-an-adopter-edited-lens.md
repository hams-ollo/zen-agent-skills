---
id: bug-0018
title: A re-install silently destroys an adopter's edited rules module
type: bug
status: done
priority: P1
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - scripts/install.py
  - tests/test_install.py
  - docs/spec/install.md
  - docs/spec/README.md
  - docs/spec/install.conformance.md
  - docs/INSTALL.md
created: 2026-08-06
---

## Problem

[`install.py`](../../scripts/install.py) places `.agents/rules/` alongside the installed skills. In copy
mode, `_place()` at [`install.py:531`](../../scripts/install.py) sees a managed target that already
exists, calls `_rm(target)` and then `_copy(src, target)`, and returns `"updated"`. For the rules
module that target is a **directory**, so the adopter's copy is removed wholesale and replaced with
the kit's. **Any edit they made to their own lens is gone, with no warning and exit 0.**

Reproduced 2026-08-06 during `chore-0031`'s reconciliation, against a throwaway home:

```
install --home <tmp> --profile core --mode copy   -> exit 0
append "MY OWN HOUSE RULE" to <tmp>/.agents/rules/house-style.md
install --home <tmp> --profile core --mode copy   -> exit 0
grep -c "MY OWN HOUSE RULE" <tmp>/.agents/rules/house-style.md   -> 0
```

**This destroys the property the rules module exists for.** `.agents/rules/` is the swappable lens:
`AGENTS.md` describes it as the module an adopter may replace with their own voice, and
[`house-style.md`](../../.agents/rules/house-style.md) opens by inviting exactly that ("keep this file,
empty it, or rewrite it"). The kit invites the edit and then reverts it on the next install.

**The other distribution path already gets this right, which is what makes this a defect rather than
a design choice.** [`build-adapters.md`](../../docs/spec/build-adapters.md) `S-010` says a rules file
already present in the target project is never overwritten, and `S-014` states the reason as a
contrast: skill supporting files are **derived** and are refreshed, the rules module is **adopted**
and is preserved. `build-adapters.py` implements it with a `dest.exists()` guard. `install.py`, the
other half of the same distribution story, does the opposite.

`chore-0031` landed a `--check` that deliberately never faults an adopter's edited lens, for this
same adopted-versus-derived reason. So the kit now has one tool that refuses to *report* the edit and
another that silently *deletes* it.

**Severity is `P1` because this is data loss in shipped code**, it is silent, and it strikes the one
file the kit specifically asks adopters to make their own. Everything else in the backlog is a wrong
report; this destroys work.

## Scope

**In scope:** stop `install.py` overwriting an adopter-modified rules file. Detect that the installed
copy differs from the kit's and leave it alone, reporting the divergence rather than resolving it.
The digest recorded by `chore-0031` makes this answerable: a file matching its recorded digest is
untouched and may be refreshed, a file that does not is the adopter's.

**Also in scope: amend [`install.md`](../../docs/spec/install.md) for the new behaviour. This task
carries the author's explicit instruction to amend, given 2026-08-07.** That instruction is recorded
here because every amendment in that file records one (lines 13, 19, 27), and `chore-0031` correctly
declined to amend without it. Without this paragraph the same thing would happen again, and the
contract would fall further behind the code it describes.

Follow the convention in [`docs/spec/README.md`](../../docs/spec/README.md): **leave `status: approved`
exactly as it is**, add a dated amendment note in the form the existing amendments use, state the
pending state in the words *pending the author's re-approval*, and add the row to that file's
re-approval queue. Flipping the field to `draft` makes `verifier-agent` return `blocked` on the run
verifying this very task.

**Coordinate with `chore-0033`, which is open against the same spec file.** It amends the Proposed
Surface table for `--check` and `--with-hooks`; this task amends the placement behaviour. They do not
conflict in substance and they do collide in mechanics, in two places. **Scenario ids**: the highest
in `install.md` today is `S-015`, so whichever task lands first takes `S-016` and the second must
read the file rather than assume. **The re-approval queue row**: if a row for `install.md` is already
present, extend it rather than adding a second.

**Out of scope:**

- Skill directories, which are **derived** and correctly replaced. Do not extend the carve-out to
  them; `S-014`'s contrast is the point.
- Merging the kit's changes into an edited lens. Report and let a human decide, matching
  `check-provenance.py` and `--check`.
- A prompt or interactive resolution. This tooling is non-interactive by design.
- `--uninstall`, which removing an adopter's file is the *documented* purpose of.

## Implementation notes

**A flag to force the overwrite is probably needed**, since "my lens is stale and I do want the
kit's" is a real case, and without it the only route is deleting the file by hand. Name it
explicitly rather than folding it into `--mode`.

**The pre-digest case has no baseline**, exactly as in `chore-0031`: an install predating that change
records no digest, so an edited lens is indistinguishable from an untouched one. Prefer preserving
the file and saying the baseline is unknown, since the failure directions are not symmetric. Wrongly
preserving costs a stale lens the adopter can see with `--check`; wrongly overwriting costs their
work.

**The bug is in the directory branch, not the file branch.** `_rm(target)` on a directory takes the
whole tree, so a lens the adopter *added* beside the kit's two files disappears as well.

## Decisions

- **The line is drawn against the recorded baseline, never against the kit's current source.** A
  file matching the digest recorded when it was placed is untouched and is refreshed; a file that
  does not is the adopter's. Deciding by "differs from the source" would have been simpler and is
  the failure this task's risks section names: it preserves everything forever and pins every
  adopter to whatever shipped first, with no tool anywhere saying so. It is the same distinction
  `--check` already draws between `diverged` and `revised`.
- **The module is placed file by file rather than as a tree.** A whole-directory verdict cannot
  express two of the required behaviours at once: a lens the kit newly ships must still arrive at a
  home where some other file was edited, and a lens the adopter *added* must be neither refreshed
  nor deleted. `_rm(target)` taking the whole tree is what destroyed the added file.
- **A preserved file keeps its previously recorded digest instead of taking the bytes now on disk.**
  Recording what the adopter wrote would make the next run read their file as untouched and refresh
  over it, which is this same data loss delayed by exactly one install. Pinned by
  `test_a_preserved_lens_is_still_preserved_by_the_run_after_it`, which fails against a fix that
  records the installed tree.
- **The no-baseline case records nothing rather than adopting the source digests.** Recording the
  kit's current digests for files this run did not place would claim a baseline that never existed,
  and `--check` would then report `ok` for a state nobody observed. It stays `unknown`, and
  `--replace-adopted` is the way out.
- **`--replace-adopted` is its own flag, not a `--mode` value.** `--mode` says how files are placed;
  this says what happens to work the adopter did, which is the destructive question and deserves to
  be spelled out at the call site.
- **A file the kit dropped is removed only where the installed copy provably matches its recorded
  digest.** Anything else is left, including a file the adopter kept after the kit stopped shipping
  it; it simply leaves the record and becomes theirs.
- **Two files were touched beyond the four originally scoped, and `touched_files` was extended to
  say so rather than left understating the change.** [`install.conformance.md`](../../docs/spec/install.conformance.md)
  carries the pending-amendment note, which is step 3 of the convention in
  [`docs/spec/README.md`](../../docs/spec/README.md) that this task's scope section points at and
  which its own wording happens to omit; without it that matrix reads as auditing a contract in full
  while three scenarios and a user-visible flag go unaudited.
  [`INSTALL.md`](../../docs/INSTALL.md) is the reader-facing install document and already explains
  how `--check` treats the rules module, so leaving it silent would have shipped a new flag and a
  changed re-install behaviour that no adopter-facing document mentions, which is the `doc-sync` step
  of this task's own definition of done.
- **Skill directories were deliberately left on the `_place` path**, unchanged. `S-014` in
  `build-adapters.md` states the contrast this whole change rests on, and extending the carve-out to
  derived material would strand adopters on stale copies of the thing the kit exists to distribute.

## Risks and rollback

Required: this changes install behaviour on a path every adopter runs, and it changes what a re-run
does to existing files on disk.

- **The failure that costs most is the inverse of the bug**: a guard so broad that the kit can never
  refresh its own rules module, leaving every adopter pinned to whatever shipped first. Distinguish
  "differs from the recorded digest" (the adopter's) from "differs from the current source but
  matches the record" (ours to refresh), which is the same distinction `--check` already draws.
- Rollback is one revert. Nothing persisted changes format; the digest map this relies on is already
  written by `chore-0031`.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/validate-skills.py && python .tasks/validate.py --strict

- [x] A test installing to a throwaway home, editing the installed rules file, re-installing, and
      asserting the edit survives byte-for-byte. It must fail against the current `install.py`.
- [x] A test proving an **unedited** installed rules file is still refreshed when the kit's copy
      changes, so the fix does not pin adopters to a stale lens.
- [x] A test proving skill directories are still replaced, since they are derived.
- [x] A test covering an install whose manifest predates `chore-0031`'s digests: the adopter's file
      is preserved and the unknown baseline is stated.
- [x] The run reports what it preserved rather than passing silently.
- [x] A rules file the adopter **added** alongside the kit's is not deleted.
- [x] Existing tests still pass, unchanged in intent.
- [x] `docs/spec/install.md` carries a scenario for the preserved-lens behaviour, covering both
      directions: an edited file is preserved, and an unedited one is still refreshed. The id
      continues from the highest already in the file, checked rather than assumed.
- [x] The scenario states the adopted-versus-derived distinction at contract level and does not
      contradict `build-adapters.md` `S-010` and `S-014`, which already draw it the same way.
- [x] If a force-overwrite flag is added, the Proposed Surface table lists it and a scenario covers
      it. A new user-visible flag that reaches no scenario is the divergence `chore-0033` exists to
      drain.
- [x] A dated amendment note is added in the form the existing three use, marked pending the
      author's re-approval, and `status:` still reads `approved`.
- [x] `docs/spec/README.md`'s re-approval queue carries the `install.md` row, extended rather than
      duplicated if one is already there.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason.
- [x] File moved to `.tasks/done/`, `status: done`, **with its relative links re-anchored for the
      extra directory level**; one dated line added to `CHANGELOG.md` referencing this task id.
