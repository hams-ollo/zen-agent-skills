---
id: chore-0067
title: The --with-hooks placement path has zero test coverage, so the only thing the kit runs inside a session ships untested
type: chore
status: done
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - tests/test_install.py
  - scripts/run-checks.py
  - tests/test_run_checks.py
created: 2026-08-27
---

## Problem

`.agents/hooks/` is, in `AGENTS.md`'s own words, "the only thing the kit ships that runs inside an
adopter's session". [`install.py`](../../scripts/install.py) places it behind `--with-hooks`. **That
placement path is exercised by nothing.**

Searched 2026-08-27:

```text
grep -rn "with_hooks" tests/     ->  0 matches
grep -n "with-hooks" scripts/run-checks.py  ->  0 matches
```

[`tests/test_install.py`](../../tests/test_install.py) covers `claude_registration()` and
`HOOK_REGISTRATIONS` thoroughly, so the *printed registration* is well tested. What is untested is the
step before it: copying or linking the module into `<home>/<subpath>`, recording the manifest entry, and
whatever `--uninstall` then has to reverse. `run-checks.py`'s `install cycle` gate runs `install.py`
twice without the flag, so none of the six CI cells has ever placed a hook.

**This is the finding `house-review`'s own skill body uses as its worked example of absence-shaped
evidence**, search command included, and it is still literally true.

Two reasons it is worth more than an ordinary coverage gap. The module is the one component whose failure
runs inside somebody else's session rather than in a build. And the manifest entry it writes is what
`install.py --check` and [`install-currency-reminder.py`](../../.agents/hooks/install-currency-reminder.py)
both read, so a defect here is silent by construction: it produces a wrong baseline, and every later
currency answer is measured against it.

**A live instance is already in this checkout.** The `hooks` entries in the local
`scripts/.install-manifest.json` record digests for five files and omit `install-currency-reminder.py`
entirely, so the recorded baseline predates the hook whose job is reporting stale installs. That is what
an unexercised placement path produces.

## Scope

**In scope:** cover the placement path, and decide whether the acceptance command should exercise it.

- Tests for `install(..., with_hooks=True)`: what lands, what the manifest records, and that
  `--uninstall` reverses it. Mirror the existing install tests' fixture idiom rather than inventing one.
- **Cover the asymmetry deliberately**: `HOOK_SUBPATHS` maps `claude` and `opencode` and not `codex`, so
  `--with-hooks` places nothing for a Codex install. Pin that as intended behaviour or report it as a
  defect; do not leave it untested either way.
- **Decide whether `run-checks.py`'s install cycle should pass `--with-hooks`.** This is the real
  question and it has a cost: the gate would then place files into the throwaway home on every run in
  every CI cell. Weigh that against the module being uncovered on all six, and **record the rejected
  option** rather than only the chosen one.

**Out of scope:**

- **Writing any new hook.** Several are worth considering and none is this task. Adding a hook and
  covering the path that ships it are separate changes, and doing both at once means the new test and the
  new hook validate each other.
- **Registering anything in [`.claude/settings.json`](../../.claude/settings.json).** `AGENTS.md` states
  that adding a second hook there, or any hook that blocks, is a new decision not covered by the existing
  exception. That decision is the author's and is not delegable to this task.
- The four hooks' own behaviour, already covered by 129 tests across four files.
- Repairing the stale local manifest entry, which is per-machine state and not tracked.

## Implementation notes

`install.py`'s `main()` takes `--home`, which every existing install test already uses to redirect at a
temporary directory, so the sandboxing question is solved. Read `_place_adopted` and the `hooks` branch
of the placement loop before writing, because the hooks entry is recorded under a single name rather than
per file, which differs from how skills are recorded and is the detail a test is most likely to get wrong.

On the `run-checks.py` question, `chore-0029`'s rule applies: one rule, two callers. Whatever is decided,
it must not create a second place where the gate set is stated.

## Decisions

- **Rejected: leaving `--with-hooks` off `run-checks.py`'s install cycle and covering the placement
  path with component tests alone.** Chosen against because those tests run `install()` in-process
  and, on Windows or any account without symlink privileges, never take the `_place` link branch,
  which is the branch the real CLI uses by default on four of the six CI cells. The rejected option's
  saving is six files written into the gitignored throwaway home and removed again by the cleanup
  that already runs; its cost is that the only module the kit executes inside an adopter's session
  keeps running on no cell. The flag is now on both runs of the cycle. The cleanup deliberately does
  not carry it: `install.py`'s uninstall branch returns before it reads the flag, and reversal is
  driven by the recorded manifest entry.
- **Premise that turned out false: the `codex` asymmetry.** The task states that `HOOK_SUBPATHS` maps
  `claude` and `opencode` and not `codex`, "so `--with-hooks` places nothing for a Codex install".
  Re-derived 2026-08-27: `TOOL_SUBPATHS` and `HOOK_SUBPATHS` carry **identical** key sets, `codex` is
  in neither, and `main()` rejects `--tools codex` at exit 2 before `install()` runs. There is no
  Codex install to place nothing for. Pinned as intended: Codex hook wiring is repo-scoped in the
  committed `.codex/hooks.json` per the wiring table in
  [`.agents/hooks/README.md`](../../.agents/hooks/README.md),
  already held to the every-hook rule by `WiringConsistencyTests` in
  [`test_hooks.py`](../../tests/test_hooks.py), and a `HOOK_SUBPATHS` row would place a second copy
  where nothing reads it.
- **Seam left open deliberately: the wordless skip if the two maps ever diverge.** The placement
  loop's `tool in HOOK_SUBPATHS` guard would skip a tool that gets skills but no hooks while printing
  nothing about the skip, and the comment above `HOOK_SUBPATHS` explicitly permits that shape. It is
  unreachable today because the maps agree, which is now pinned by
  `test_every_installable_tool_has_a_hook_path`. Closing it means changing `install.py`, which this
  task does not scope.
- **Premise unverifiable from here: the live stale-manifest instance.** The task cites `hooks` entries
  in the local `scripts/.install-manifest.json` recording five files and omitting
  `install-currency-reminder.py`. That file is per-machine, gitignored, and absent from this
  worktree, and reading the one in the main checkout was out of bounds, so the claim was neither
  confirmed nor refuted. What was measured instead: a fresh install today records all six files in
  the module, and `test_the_placement_is_recorded_with_a_digest_for_every_file_in_the_module` fails
  against a mutant that drops exactly that one file from the record.

## Risks and rollback

Two test modules and possibly one gate, so this section is required.

The risk is a test that asserts the placement happened without asserting what was recorded. The manifest
entry is the load-bearing half, because it is the baseline every later currency answer is measured
against, and a test that checks only for files on disk would pass against the live defect described
above.

Reversible by reverting one commit. No hook is added, so nothing new runs in anyone's session.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] A test places hooks via `install(..., with_hooks=True)` and asserts both what landed and what the
      manifest recorded, failing against a stubbed-out placement.
- [x] A test asserts `--uninstall` reverses the placement.
- [x] The `codex` omission from `HOOK_SUBPATHS` is pinned as intended or reported as a defect, in writing.
- [x] The closeout states whether `run-checks.py` now passes `--with-hooks`, and records the rejected
      option with its cost.
- [x] No file under `.agents/hooks/` and no harness registration is modified.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
