---
id: bug-0010
title: Resolve home in install() so the manifest never records a relative target
type: bug
status: open
priority: P1
parent: "ROADMAP#tooling install.py"
depends_on: []
spec: "docs/spec/install.md"
scenarios: ["S-003", "S-007"]
touched_files:
  - scripts/install.py
  - tests/test_install.py
  - docs/spec/install.conformance.md
created: 2026-07-29
---

## Problem

[`install()`](../scripts/install.py) builds each target from the `home` it was handed and records the
result verbatim:

    base = home / TOOL_SUBPATHS[tool]
    target = base / src.name
    ...
    entries[str(target)] = {..., "target": str(target), ...}

Nothing resolves `home` first. `main()` does (`Path(args.home).expanduser().resolve()`), so the shipped
CLI always records absolute targets, but `install()` is a directly callable entry point (`chore-0017`)
and a caller passing a relative home writes **relative strings into a persisted record**.

`bug-0009` fixed the reversal predicate to normalise both sides of its comparison. It did not, and could
not, fix this: a relative recorded target has no fixed meaning to normalise toward, because
`Path.resolve()` interprets it against whatever the current working directory happens to be at the
moment it is read.

### Two confirmed consequences, both contract divergences

Measured 2026-07-29 against `profile="core"`, manifest redirected to a temp path.

**Re-run recognition breaks (S-003).** Install with `Path("./h")`, then install again with the absolute
spelling of the same directory:

    recorded target[0]: h\.claude\skills\init-worktracking   (is_absolute: False)
    second run exit: 1   CONFLICT count: 5   updated count: 0

`is_managed()` compares `e.get("target") == str(target)` as an exact string, so the tool refuses its own
work. S-003 requires the opposite: it "replaces or relinks those targets and reports doing so, rather
than reporting a conflict against its own work, and exits zero."

**Reversal silently orphans everything it claims to have reversed (S-007).** Install with `Path("./h")`,
then reverse the same spelling from a different working directory:

    manifest entries before uninstall: 4
    manifest entries after  uninstall: 0
    skills still on disk: ['init-worktracking', 'pr-describe', 'project-bootstrap']
    rules still on disk:  True
    re-install exit: 1   CONFLICTs: 5

The entries pass `_beneath` (both sides resolve against the new cwd consistently), so they are treated
as owned. Then `Path(e["target"]).exists()` is False, because the relative path does not exist from
here, so each is reported `gone` rather than `removed` and nothing is deleted. The record is then
emptied via `save_manifest(others, dry)`.

The result is the worst state this tool can reach: four directories on disk that it created, no longer
recorded, and therefore **permanently unmanaged**. A later re-install reports them as CONFLICT (S-005,
correctly, since a copied directory carries nothing distinguishing it from a user's own) and the only
way out is deleting them by hand. The run exits zero throughout.

This is strictly worse than `bug-0009`, which was a harmless no-op. Here the reversal destroys the
record while leaving the files.

## Scope

**In scope:** resolve `home` once at the top of `install()` so every recorded target is absolute, and
prove both consequences above are gone.

**Out of scope:**

- `_beneath()`. `bug-0009` already normalises both sides of the reversal comparison and that fix stands;
  this task removes the residual case it cannot reach.
- Migrating or rewriting an existing manifest. See the risks section: read the decision before assuming
  a migration is wanted.
- The manifest's location (Open Question 1 in the contract), the `--mode` behavior, and the profile axis.

## Implementation notes

The change itself is one line, `home = home.expanduser().resolve()` at the top of `install()`, matching
what `main()` already does so the two paths agree. Everything hard about this task is around it.

**Two existing tests assert on the recorded string and must be re-read, not blindly updated.**
`test_uninstall_of_one_home_leaves_another_homes_install_intact` asserts
`str(other_home) in e["target"]`, and its sibling asserts `all(str(other_home) in e["target"] ...)`.
Where `other_home` is already absolute these keep passing. On macOS they may not: `tempfile` hands out a
path under `/var`, a symlink to `/private/var`, so `str(other_home)` is the unresolved spelling and the
recorded target becomes the resolved one, making the substring check fail. **That failure would be
correct and the assertion is what is wrong**, so fix it by comparing resolved forms rather than by
loosening it until it passes. This cannot be confirmed on Windows; CI's macOS legs are the check.

**Verify the fix against both consequences, not just one.** They fail at different layers, S-003 in
`is_managed()` and S-007 in `uninstall()`'s existence check, so a test covering only re-run recognition
would leave the orphaning path live. Both reproductions above are directly translatable into tests, and
both must be confirmed to fail against the pre-fix `install()`.

**A regression test needs `os.chdir`** for the reversal case, since the defect only appears when the cwd
moves between install and uninstall. Restore it in a `finally`; `bug-0009`'s test does this already and
is the shape to mirror.

**Read `chore-0023` before starting.** It landed in `#4` on 2026-07-29 and touched two of the same
files, prose only: it rewrote the `tests/test_install.py` docstring and re-anchored the S-014 figure in
the conformance matrix. Nothing under `scripts/` changed and no assertion changed, so this task's
reproduction still holds as written, but the two files no longer read the way `bug-0009` left them.

**The contract does not need amending.** The Record row of the Proposed Surface says "A manifest of the
targets this tool created" without constraining how a target is spelled, and S-003 and S-007 are already
violated by the current behavior rather than under-specified by it. State this rather than assuming it,
and leave [`docs/spec/install.md`](../docs/spec/install.md) alone.

## Risks and rollback

This changes the content written into a persisted record, so the rule fires.

- **An existing `.install-manifest.json` may hold relative targets** written before this fix. Nothing in
  this task migrates them, and that is a deliberate default rather than an oversight: those entries are
  already unreliable (their meaning depends on the reader's cwd), and rewriting them would mean guessing
  the cwd of a past run. Any such manifest was produced by a direct programmatic call, never by the CLI,
  so the realistic population is developer scratch state. **Confirm this reading before implementing**;
  if migration is wanted instead, it is a separate decision and probably a separate task.
- Post-fix entries are absolute, so a manifest containing both forms is possible. Absolute entries behave
  correctly and relative ones behave exactly as badly as they do today, so the fix does not make any
  existing record worse.
- Rollback is reverting the one commit. No schema changes, so no cleanup is needed afterwards, though a
  manifest written after the fix keeps its absolute entries, which is harmless.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py"

- [ ] A test installs with a relative home, installs again with the absolute spelling, and asserts the
      second run exits zero with no CONFLICT (S-003).
- [ ] A test installs with a relative home, reverses it from a different working directory, and asserts
      the targets are removed from disk rather than reported `gone` and dropped from the record (S-007).
- [ ] Both tests are confirmed to **fail** against the pre-fix `install()`, not merely to pass after.
- [ ] Every recorded `target` is absolute after an install, asserted directly.
- [ ] The two existing tests that assert on the recorded string are re-read and, if changed, changed to
      compare resolved forms rather than weakened.
- [ ] `docs/spec/install.md` left unamended, with the reason stated.
- [ ] `docs/spec/install.conformance.md` S-003 and S-007 rows record this re-audit.
- [ ] Existing tests still pass.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
