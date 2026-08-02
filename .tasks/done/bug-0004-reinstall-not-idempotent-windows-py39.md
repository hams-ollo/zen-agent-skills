---
id: bug-0004
title: Make re-install idempotent on Windows with Python 3.9, or narrow the supported range
type: bug
status: done
priority: P1
parent: "ROADMAP#tooling install.py"
depends_on: []
spec: "docs/spec/install.md"
scenarios: ["S-004"]
touched_files:
  - scripts/install.py
  - tests/test_install.py
  - README.md
created: 2026-07-28
---

## Problem

Running `install.py` twice against the same home reports every target as a conflict on the second
run, on Windows with Python 3.9. The command exits 1.

```
40 CONFLICT(s): a real file exists at those targets. Move or remove them, then re-run.
```

This contradicts the documented promise. [`README.md`](../README.md) says "The installer is
idempotent, so it is safe to run again after the kit changes", and `docs/spec/install.md` carries a
scenario for re-run recognition. A user on this combination cannot re-run the installer at all after
the first install: they are told to move or remove files the installer itself created.

First observed by CI on 2026-07-28, on the workflow's first run. The matrix isolates it cleanly:

| | Python 3.9 | Python 3.13 |
|---|---|---|
| ubuntu-latest | pass | pass |
| macos-latest | pass | pass |
| windows-latest | **fail** | pass |

This has never been reachable on the maintainer's machine, which is Windows on Python 3.14, and it is
the first defect found by running the kit anywhere other than there.

## Leading hypothesis, not yet proven

Two facts in the code make the failure coherent, and both are worth confirming before fixing:

1. **The manifest keys on a path string.** [`is_managed()`](../../scripts/install.py) compares
   `str(target)` against the recorded `"target"` string. If the string a run computes differs from
   the string the previous run recorded, the installer does not recognize its own file and reports a
   conflict.
2. **Only copy mode consults the manifest.** Symlink mode can identify its own work from the link
   itself. Copy mode is the Windows default and POSIX defaults to symlinks, which is consistent with
   Windows being the only failing platform.

The likely trigger is `home = Path(args.home).expanduser().resolve()` in `main()`. On the first run
`./.tmp/zen-home` does not exist; on the second it does. Windows `Path.resolve()` handles
non-existent paths differently from existing ones, and that difference narrowed across versions, so
3.9 disagreeing with 3.13 fits. Confirm by printing the recorded and recomputed strings side by side
on the failing combination before changing anything.

CI is now the reproduction environment: `windows-latest` with `python-version: "3.9"` in
[`.github/workflows/checks.yml`](../../.github/workflows/checks.yml) reproduces it every run.

## Resolution (2026-07-28)

**Option B was taken: the supported floor is now Python 3.10.**

The deciding fact was not the defect but the calendar. Python 3.9 reached end of life in October
2025, so the kit was claiming support for a runtime that upstream no longer supports, and CI proved
the claim false on one of the three platforms it targets. A floor that holds everywhere is worth more
than a lower one that does not.

Option A was not attempted. The cause is well localized (all 40 targets conflicted rather than some,
which points at the shared `home` prefix rather than per-target handling, and `main()` resolves
`--home` once against a path that does not exist on the first run and does on the second), but it
does not reproduce on the maintainer's machine, so the fix would have been written blind against CI
and would have changed how every manifest entry is keyed. That is a lot of risk to keep an
end-of-life version.

The cost is real and worth stating: macOS and Linux passed on 3.9, so this drops users whose system
`python3` is 3.9 even though nothing was broken for them. They can install 3.10 or newer, and since
3.9 is unsupported upstream they should.

If someone later needs 3.9, Option A below is still the route, and the diagnosis stands.

## Scope

**In scope:** confirm the cause, then either make re-run recognition stable across runs on this
combination, or narrow the documented and tested Python range and say so everywhere it is claimed.

**Out of scope:** the manifest's blast radius on uninstall (that is [`bug-0003`](bug-0003-uninstall-ignores-home.md), which touches the same file, so sequence the two rather than running them in parallel); moving the manifest out of the repository (Open Question 1 in the spec).

## Implementation notes

The decision is which of two things to fix, and they are not equivalent:

- **Option A, make the key stable.** Normalize once and record that form, for example
  `os.path.normcase(os.path.abspath(...))`, or resolve the home only after creating it so both runs
  see an existing path. This keeps the 3.9 support claim true. It changes how entries are keyed, so
  an existing manifest written by the old code will not match and every target becomes a conflict on
  the next run, which is the same failure this task exists to remove. A migration or a one-time
  re-key is part of the work, not an afterthought.
- **Option B, drop 3.9.** Raise the floor to the lowest version that actually passes, update the
  `Prerequisites` section of `README.md`, `CONTRIBUTING.md`, and the CI matrix together, and note it
  in the spec. Cheaper and honest, but it narrows who can adopt the kit.

Option A is preferable if the fix is as small as the hypothesis suggests, because a claimed floor
that CI proves false is worse than a higher floor that holds. Verify the cause first: if 3.9 diverges
somewhere less tractable than path resolution, Option B becomes the better trade.

## Risks and rollback

Changes how a persisted record is keyed.

- Under Option A, any manifest written before the change may stop matching. Decide explicitly whether
  to migrate it, re-key it in place on first run, or document that users should uninstall before
  upgrading. Doing none of those turns this fix into a silent repeat of the same bug.
- Rollback is reverting the one commit, plus deleting any manifest written in the new format.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py"

- [ ] A test installs twice to the same temporary home and asserts the second run reports zero
      conflicts and exits 0.
- [ ] The CI matrix passes on every combination it declares, with no combination excluded to make it
      pass unless that exclusion is the deliberate Option B outcome.
- [ ] If Option B is chosen, `README.md`, `CONTRIBUTING.md`, and the CI matrix state the same minimum
      Python version, and no document claims a version the matrix does not test.
- [ ] Existing tests still pass.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
