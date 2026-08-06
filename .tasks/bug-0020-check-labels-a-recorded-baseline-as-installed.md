---
id: bug-0020
title: On the revised path, --check prints the recorded baseline while calling it "installed"
type: bug
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [chore-0031]
touched_files:
  - scripts/install.py
  - tests/test_install.py
created: 2026-08-06
---

## Problem

`_compare()` in [`install.py:640`](../scripts/install.py) takes `(installed, source)` and formats
every disagreement with those words:

```python
problems.append(f"{rel}: installed {found[:12]}, source {digest[:12]}")
problems.append(f"{rel}: in the source, absent from the install")
```

That is accurate on the divergence path, where the first argument really is a digest of the installed
tree. It is **wrong on the `revised` path**, the adopted-lens branch `_check_entry()` uses, which
passes the **recorded manifest baseline** as the first argument. The message still says "installed".

Measured 2026-08-06 during `chore-0031`'s verification. With an adopter edit *and* a kit revision on
the same lens file, the report printed:

```
house-style.md: installed fe4780bc8565, source d29d46c650d0
```

while the file actually on disk hashes to `00534650d2d5`. **All three numbers are different and the
one labelled "installed" is the one number that is not.** An adopter who runs a checksum on their own
file gets a third value and has no way to reconcile it with the report.

The same defect hits the absence wording on that path: "in the source, absent from the install" means
absent from the **record**, not from the install, so it can name a file the adopter is looking at.

**Why this matters more than a typo.** The `revised` state is the one that exists to tell an adopter
"your lens is yours, but the kit's copy moved underneath it". That message is only useful if the
adopter can act on it, and acting on it means comparing their file to something. A label naming the
wrong artifact makes a correct diagnosis unusable, and it does it in the one branch designed to be
read by someone who deliberately edited a file.

The classification is right and the exit code is right. Only the words are wrong, which is why this
is a bug and not a design change.

## Scope

**In scope:** make the two message forms name the artifact they actually compared. `_compare()` gains
a label pair, or the adopted branch gets its own wording ("recorded" and "source now"). Tests
asserting the wording per path.

**Out of scope:**

- The `revised` classification itself, and its exit-neutral status. Both are correct and were
  verified against `build-adapters.md`'s `S-010` and `S-014`.
- The digest truncation to twelve characters, which is a readability choice.
- Any other `--check` status word.

## Implementation notes

**Prefer passing labels over duplicating the function.** Two near-identical comparison bodies drifting
apart is the failure this repository has paid for three times, in `house-review`'s rubric,
`bug-0006`'s parser, and the three frontmatter readers in `scripts/`.

**Say what the adopter should do with the third number.** On the `revised` path there are genuinely
three digests: what was installed originally (the record), what is on disk now (their edit), and what
the kit ships today. Naming two and implying the third is what produced this bug. Consider printing
all three on that path, since the whole point of the state is that the adopter reconciles them.

**A neighbouring gate is worth fixing in the same pass, and is cheap.** `_check_entry()` at
[`install.py:672`](../scripts/install.py) tests `recorded is None` to detect a missing baseline, so a
`digests` value that is present but **empty** counts as a valid baseline and yields `revised` at exit
0. It is not reachable from `install.py` itself, since `digest_tree()` returns `{}` only for a
non-directory source, so this is a hand-edited-manifest edge rather than a live defect. A falsiness
check closes it. It never degrades toward `ok`, so it is not urgent, but it is one character.

## Risks and rollback

Low. This changes report wording and one truthiness test, not classification, exit codes, or the
persisted format. The risk worth naming is asserting the new strings in tests so loosely that the
labels could regress unnoticed; assert the exact words per path. Rollback is one revert.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/validate-skills.py && python .tasks/validate.py --strict

- [ ] A test staging an adopter edit **plus** a kit revision on the same rules file, asserting the
      report does not label the recorded baseline as "installed". It must fail against the current
      wording.
- [ ] Every digest the `revised` path prints is reconcilable: each number is labelled with the
      artifact it was taken from.
- [ ] The absence wording on the adopted path names the record rather than the install.
- [ ] The divergence path's wording is unchanged, since it was already correct.
- [ ] A `digests` value present but empty no longer counts as a valid baseline.
- [ ] Classification and exit codes are unchanged on every path: `ok`, `linked`, `revised`,
      `diverged`, `unknown`.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason.
- [ ] File moved to `.tasks/done/`, `status: done`, **with its relative links re-anchored for the
      extra directory level**; one dated line added to `CHANGELOG.md` referencing this task id.
