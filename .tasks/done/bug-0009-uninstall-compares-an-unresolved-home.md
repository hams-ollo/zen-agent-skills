---
id: bug-0009
title: Normalize both sides of the uninstall home comparison, so an unresolved home is not read as an empty one
type: bug
status: done
priority: P1
parent: "ROADMAP#tooling install.py"
depends_on: []
spec: "docs/spec/install.md"
scenarios: ["S-007", "S-012"]
touched_files:
  - scripts/install.py
  - tests/test_install.py
  - docs/spec/install.conformance.md
created: 2026-07-29
---

## Problem

[`_beneath()`](../../scripts/install.py) decides which recorded targets a reversal owns, and it decides
it lexically:

    return Path(target).is_relative_to(home)

`is_relative_to` compares path components as spelled. Neither side is resolved, so `home` only matches
if the caller happened to spell it the same way the manifest recorded it. When it does not match,
every entry falls into `others`, `mine` is empty, and [`uninstall()`](../../scripts/install.py) takes the
early return:

    print(f"Nothing recorded as installed beneath {home}.")
    ...
    return 0

A reversal that removed nothing exits zero and says so in language that reads like "there was nothing
to do". This is the same failure shape as `bug-0003`, inverted: that one destroyed more than it was
asked to, this one destroys nothing while reporting success.

**The shipped CLI is safe.** `main()` resolves the flag (`Path(args.home).expanduser().resolve()`), so
no `python scripts/install.py --uninstall --home <dir>` invocation can hit this.

**`uninstall()` is not reached only through `main()`.** `chore-0017` deliberately gave `install.py` an
injectable entry point so its functions are drivable without subprocesses, and
[`tests/test_install.py`](../../tests/test_install.py) calls `install()` and `uninstall()` directly. A
direct call is therefore a supported use, and it carries no resolution guarantee. The guarantee lives
in the wrong place: with one caller, rather than with the comparison that depends on it.

### Reproduced 2026-07-29

Against a recorded target of `<worktree>/.tmp/zen-home/.claude/skills/doc-sync`:

| `home` as the caller spells it | `_beneath` |
|---|---|
| `Path('./.tmp/zen-home').resolve()` | `True` |
| `Path('./.tmp/zen-home')` | `False` |
| `Path('./.tmp/../.tmp/zen-home')` | `False` |

End to end, installing the `core` profile to a resolved home and then reversing it as `Path("./home")`
from that directory's parent:

    Nothing recorded as installed beneath home.
    4 target(s) recorded under other homes are untouched.
    exit code: 0
    still installed: ['init-worktracking', 'pr-describe', 'project-bootstrap']

The three skills and the rules module are still on disk. The "under other homes" line is wrong twice
over: they are under *this* home, and calling them untouched conceals that the command did nothing.

### Today's suite cannot catch it

Every existing test passes `self.home` to both `install()` and `uninstall()`, so the two spellings are
identical by construction and the lexical comparison succeeds by accident. Adding a test that reverses
a resolved home would prove nothing, because that is already the covered path.

### This is a conformance divergence, not a contract gap

Unlike `bug-0003`, no spec amendment is needed. S-007 already says the tool is asked to reverse
"against the same home", and `./home` and `<abs>/home` name the same directory. The contract is about
the directory, not about how a caller spells it, so the code is diverging from what S-007 already
requires. Leave [`docs/spec/install.md`](../../docs/spec/install.md) unamended.

## Scope

**In scope:** normalize both sides of the comparison inside `_beneath()` so every caller inherits it;
a regression test that reverses an unresolved home and proves entries are actually removed; re-anchor
the two conformance rows whose evidence quotes the expression being changed.

**Out of scope:**

- Amending `docs/spec/install.md`. See above. It is `status: approved` and human-owned; if the author
  wants S-007 to say "however the home is spelled" that is their call, not this task's.
- Resolving `home` inside `install()` so the manifest never records a relative target. That is the same
  family of defect and is arguably worth doing, but it changes what gets written to a persisted record,
  and two existing tests assert on the recorded string
  (`test_uninstall_of_one_home_leaves_another_homes_install_intact`). Keep it separate.
- The `--mode` symlink/copy behavior, the profile axis, and the manifest's location (Open Question 1).

## Implementation notes

**Resolving only `home` is not enough, and on its own is a regression.** The obvious minimal fix,
`home = home.resolve()` at the top of `uninstall()`, breaks a case that works today. On macOS
`tempfile.TemporaryDirectory()` returns a path under `/var`, which is a symlink to `/private/var`. The
existing tests install and uninstall with the same unresolved value, so the manifest holds
`/var/.../home/...`; resolving only `home` yields `/private/var/.../home` and matches none of them.
Both sides have to be normalized the same way, which is why the fix belongs in `_beneath()`.

**Do not resolve the target's final component.** `Path(target).resolve()` looks like the symmetric
answer and is a trap. In symlink mode every recorded target *is* a link this tool created, pointing at
its source inside this checkout, so resolving it lands somewhere beneath no home at all and reversal
silently finds nothing to remove. That converts this bug into a worse version of itself on the default
POSIX path. Resolve the directory chain and keep the name:

    t = Path(target)
    return (t.parent.resolve() / t.name).is_relative_to(home.resolve())

The parent chain always includes `home`, so a symlinked home normalizes identically on both sides.
`Path.resolve()` is non-strict, so an already-removed target or one recorded on another machine
normalizes lexically rather than raising. Keep the existing `except (OSError, ValueError)` guard, which
now also covers resolution.

**The regression test must fail against the pre-fix code**, per the bar `bug-0003` set. Install to a
resolved home, then call `uninstall()` with a spelling `main()` would never produce, and assert the
targets are gone and the record is empty. Assert on the absence of "Nothing recorded as installed
beneath" too: a fix that removed the targets while still printing that line would be a different bug.

**Pin symlink-mode reversal while you are here.** No test covers it, and the whole reason the fix
spares the final component is to protect it. Guard the test on whether the platform and account can
actually create a symlink, since Windows without Developer Mode cannot (S-011). This test passes before
and after the fix by design: it is a guard against the wrong fix, not the proof of the right one, and
should say so.

## Risks and rollback

The deterministic rule does not fire (one module, no persisted format change, revertible by reverting
one commit), but there is a real risk worth stating: this widens what a destructive command matches.
After the fix, `--uninstall` removes entries it previously skipped. That is the intended correction,
and the blast radius is still bounded by `home`, but it means a caller relying on the buggy no-op will
now see deletions.

Rollback is reverting the one commit. Nothing persisted changes shape, so no manifest cleanup is needed
afterwards.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py"

- [ ] A new test installs to a resolved home, calls `uninstall()` with an unresolved spelling of the
      same directory (relative, and one containing `..`), and asserts the targets are removed from disk
      and the entries dropped from the record.
- [ ] That test is confirmed to **fail** against the pre-fix `_beneath()`, not merely to pass after.
- [ ] A test pins symlink-mode reversal, skipped where symlinks are unavailable, so a fix that resolved
      the target's final component would fail.
- [ ] `docs/spec/install.md` is left unamended, and the reason is stated rather than assumed.
- [ ] The S-007 and S-012 rows of [`docs/spec/install.conformance.md`](../../docs/spec/install.conformance.md)
      no longer quote the replaced expression, and the test-coverage table records the new tests.
- [ ] Existing tests still pass, on this platform, unchanged.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
