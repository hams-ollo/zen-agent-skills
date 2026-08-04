---
id: bug-0003
title: Scope uninstall to the home it was given, instead of every recorded target
type: bug
status: done
priority: P0
parent: "ROADMAP#tooling install.py"
depends_on: []
spec: "docs/spec/install.md"
scenarios: ["S-007", "S-012"]
touched_files:
  - scripts/install.py
  - tests/test_install.py
  - docs/spec/install.md
created: 2026-07-28
---

## Problem

`python scripts/install.py --uninstall --home <dir>` removes **every target the manifest records,
from every home ever installed to from this checkout**, not the targets under `<dir>`.

The `home` parameter of [`uninstall()`](../../scripts/install.py) is accepted and then never read. The
function loads the manifest, iterates `manifest["entries"]` in full, deletes each target, and calls
`save_manifest([])` to empty the record. Nothing filters on the home the caller asked for.

The damage requires a second ingredient, and `install()` supplies it: it merges into the existing
record rather than replacing it (`entries = {e["target"]: e for e in manifest["entries"]}`). So
installing to a throwaway home does not create a separate record, it appends to the real one.

Observed on 2026-07-28, on a real machine, in this order:

1. `install.py` (real homes) recorded 40 targets.
2. `install.py --home ./.tmp/zen-home` appended 40 more, for 80 in one record.
3. `install.py --uninstall --home ./.tmp/zen-home` reported `Uninstalled 80 target(s)` and removed
   the user's actual installation: all 19 skills from `~/.claude/skills`, both rules modules from
   `~/.claude/rules`, and the same under `~/.agents/`.

Unmanaged files were correctly left alone, so the never-overwrite rule held and the loss was
limited to kit-managed targets, which a reinstall restored. That is the only reason this was
recoverable.

This is the kit's own worst category: a command that reports success while destroying work the user
did not ask it to touch. It is also a live trap for the documented evaluation path, since
[`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md) and [`SECURITY.md`](../../SECURITY.md) both suggest a
throwaway `--home` for previewing, and anyone who installs there for real and later uninstalls loses
their working installation.

### This is a contract gap, not a conformance divergence

The implementation matches the approved contract's literal wording: `docs/spec/install.md:148`
defines `--uninstall` as "Remove the recorded targets and empty the record", which is exactly what it
does. No scenario states that `--home` narrows what uninstall touches, so the code is not violating
the spec.

Open Question 1 in that spec reasoned about one manifest serving several *checkouts* and rejected
moving the record into the home directory. It never considered the inverse, one manifest serving
several *homes* from one checkout, which is this bug. The contract needs amending before the code
changes, so the fix is decided rather than guessed.

## Scope

**In scope:** amend `docs/spec/install.md` with a scenario fixing uninstall's blast radius, then make
`uninstall()` honor it, with a test that fails against today's behavior.

**Out of scope:** relocating the manifest out of the repository (that is Open Question 1 and a
separate decision); changing `install()`'s merge semantics beyond whatever the chosen fix requires;
the `--mode` symlink and copy behavior.

## Implementation notes

The contract decision comes first and is a genuine choice, not a formality:

- **Option A, filter on uninstall.** Remove only entries whose target lies under the resolved
  `--home`, and keep the rest in the record. Narrowest change, keeps one manifest, and makes `--home`
  mean the same thing on both paths.
- **Option B, key the record by home.** `{"homes": {"<resolved home>": [entries]}}`. Cleaner model,
  but changes a persisted format, so it needs a migration path for an existing manifest.

Option A is the smaller and more obviously correct change and is the recommendation, but the call is
the maintainer's.

Whichever is chosen, `uninstall()` must stop calling `save_manifest([])` unconditionally, since that
discards the record for homes it did not touch.

A regression test must construct two distinct homes, install to both, uninstall one, and assert the
other's targets still exist. A test that uses a single home cannot fail against the current code and
would be theatre. `install.py` already takes an injectable `argv` (`chore-0017`), so this is
reachable from `tests/test_install.py` without subprocesses.

## Risks and rollback

Changes behavior of a destructive command and, under Option B, a persisted format.

- An existing `.install-manifest.json` predates any fix. Under Option A it keeps working unchanged.
  Under Option B it must be migrated or explicitly treated as a legacy single-home record; failing to
  do either silently orphans every currently-installed target, which converts this bug into a quieter
  one.
- Rollback is reverting the one commit. Any manifest written in a new format would need to be deleted
  by hand afterwards, so state that in the changelog entry if Option B is taken.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py"

- [ ] A new test installs to two distinct temporary homes, uninstalls one, and asserts the other's
      targets survive and remain in the record.
- [ ] That test is confirmed to **fail** against the pre-fix `uninstall()`, not merely to pass after.
- [ ] `docs/spec/install.md` carries a scenario stating uninstall's blast radius, and the spec is
      re-approved rather than edited silently.
- [ ] `docs/spec/install.conformance.md` is regenerated and the new scenario is `Conformed`.
- [ ] `uninstall()` no longer discards records for homes it did not touch.
- [ ] Existing tests still pass.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
