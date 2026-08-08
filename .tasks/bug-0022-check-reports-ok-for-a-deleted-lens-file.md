---
id: bug-0022
title: --check reports ok for a rules module whose lens file was deleted from the install
type: bug
status: open
priority: P1
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - scripts/install.py
  - tests/test_install.py
  - docs/INSTALL.md
created: 2026-08-08
---

## Problem

`_check_entry()` in [`install.py`](../scripts/install.py) handles the adopted rules module by
comparing the **recorded baseline** against the **current source**, and never reads the installed
tree at all. A missing installed file therefore has no check anywhere: whole-directory absence is
caught one branch earlier, and per-file absence is not caught by anything.

Reproduced 2026-08-08 against a real install:

```text
$ python3 scripts/install.py --mode copy --tools claude --home $H
copied    claude   rules  -> $H/.claude/rules

$ rm $H/.claude/rules/review-quality.md
$ python3 scripts/install.py --check --home $H
ok        claude   rules  the kit's copy is unchanged since this install (3 file(s))
exit=0

$ python3 scripts/install.py --mode copy --tools claude --home $H
preserved claude   rules
          preserved review-quality.md: you removed it, so it is not restored
```

**The installer knows and the checker does not.** `_place_adopted()` names the removal in plain words
on the very next run, while `--check` reports the install clean at exit 0. The manifest keeps
asserting the file too: the removal branch in `_place_adopted()` keeps the deleted file's digest in
`digests`, so the record and the disk disagree and nothing reconciles them.

**Why this one is P1 rather than cosmetic.** The file deleted above is `house-review`'s entire
rubric. An install missing it reproduces the incident this repository cites more than any other, that
`house-review` once shipped with no rubric, and `--check` is the tool
[`chore-0031`](done/chore-0031-installed-skills-go-stale-with-no-signal.md) added specifically to
answer whether an install can still be trusted. Two written claims are wider than the code:

- [`INSTALL.md`](../docs/INSTALL.md)'s report table reads `ok` = "Every placed file still matches the
  kit".
- `chore-0031`'s changelog entry reads "a deleted lens is still divergence". True of the directory,
  false of a file inside it.

## Scope

**In scope:** make `--check` report a placed file that is absent from the installed adopted module,
and stop the manifest carrying a digest for a file the run knows is gone. Correct `INSTALL.md`'s
`ok` row so it describes what the check actually proves for each entry kind.

**Out of scope:**

- Reporting an adopter's **edit** to a lens as divergence. That exemption is deliberate and is the
  whole reason the adopted branch exists; a missing file is a different claim from a changed one and
  only the missing one is being added.
- Restoring the file. `--check` detects and reports and never rewrites, per rule `A3` in
  [`autonomy.md`](../.agents/rules/autonomy.md). `--replace-adopted` is the existing route back.
- The `unknown` remedy wording, which is [`bug-0020`](bug-0020-check-unknown-remedy-is-wrong-for-the-adopted-lens.md).
- Amending `docs/spec/install.md`. Its Proposed Surface does not list `--check` at all, which is
  [`chore-0033`](chore-0033-amend-install-spec-for-check-and-with-hooks.md)'s scope. Note the
  divergence in the closeout rather than amending unasked, following the precedent `chore-0031` set.

## Implementation notes

The adopted comparison currently answers one question, "has the kit's copy moved since you
installed". The fix is a second, independent question, "is every file we placed still there", not a
replacement for the first. Keep them separable in the output so an adopter who edited a lens does not
start seeing noise on every run.

A status word already exists for the answer. `diverged` is what the derived path returns for a
missing file, and reusing it keeps one vocabulary rather than inventing a second for the same idea.
Whether a missing adopted file should be `diverged` or a new word is a real choice; make it once and
say why.

`_place_adopted()`'s `digests` handling is the other half. The removal branch records
`preserved.append((rel, "you removed it, so it is not restored"))` and leaves `digests[rel]` set from
`dict(recorded)`. Dropping the key there makes the record honest; check that it does not break the
"preserved file keeps its old baseline" property that
[`bug-0018`](done/bug-0018-reinstall-destroys-an-adopter-edited-lens.md) pinned with a test, which is
about **edited** files and not removed ones.

## Risks and rollback

Touches the installer and a reader-facing document. The failure direction to design against is a
false `diverged` for an adopter who deliberately deleted a lens they do not want: the report must
name the file and say it is theirs to keep, or the check becomes noise for exactly the people the
adopted exemption was written for.

Reversible by reverting one commit. No manifest migration: an entry written before this change is
read the same way afterwards.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [ ] A test that installs to a throwaway home, deletes one installed rules file, runs `--check`, and
      asserts the file is named and the exit code is non-zero. It must fail against the current
      `install.py`.
- [ ] A test that edits an installed rules file and asserts `--check` still does **not** call it
      divergence, so the adopted exemption survives.
- [ ] A test that a rules file the adopter **added** is still ignored in both directions.
- [ ] A test that the manifest no longer records a digest for a file a run reported as removed.
- [ ] Exit codes still follow the documented precedence, with "could not answer" outranking
      "diverged".
- [ ] `INSTALL.md`'s report table states what `ok` proves for a derived entry and for the adopted
      one, since the two answer different questions.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
