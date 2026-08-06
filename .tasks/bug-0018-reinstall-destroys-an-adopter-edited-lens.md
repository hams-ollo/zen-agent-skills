---
id: bug-0018
title: A re-install silently destroys an adopter's edited rules module
type: bug
status: open
priority: P1
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - scripts/install.py
  - tests/test_install.py
  - docs/spec/install.md
created: 2026-08-06
---

## Problem

[`install.py`](../scripts/install.py) places `.agents/rules/` alongside the installed skills. In copy
mode, `_place()` at [`install.py:531`](../scripts/install.py) sees a managed target that already
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
[`house-style.md`](../.agents/rules/house-style.md) opens by inviting exactly that ("keep this file,
empty it, or rewrite it"). The kit invites the edit and then reverts it on the next install.

**The other distribution path already gets this right, which is what makes this a defect rather than
a design choice.** [`build-adapters.md`](../docs/spec/build-adapters.md) `S-010` says a rules file
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

- [ ] A test installing to a throwaway home, editing the installed rules file, re-installing, and
      asserting the edit survives byte-for-byte. It must fail against the current `install.py`.
- [ ] A test proving an **unedited** installed rules file is still refreshed when the kit's copy
      changes, so the fix does not pin adopters to a stale lens.
- [ ] A test proving skill directories are still replaced, since they are derived.
- [ ] A test covering an install whose manifest predates `chore-0031`'s digests: the adopter's file
      is preserved and the unknown baseline is stated.
- [ ] The run reports what it preserved rather than passing silently.
- [ ] A rules file the adopter **added** alongside the kit's is not deleted.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason.
- [ ] File moved to `.tasks/done/`, `status: done`, **with its relative links re-anchored for the
      extra directory level**; one dated line added to `CHANGELOG.md` referencing this task id.
