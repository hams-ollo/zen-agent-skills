---
id: bug-0048
title: Hooks placed for opencode alone are announced by nothing and land where the opencode plugin never looks
type: bug
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [chore-0067]
touched_files:
  - scripts/install.py
  - tests/test_install.py
created: 2026-08-27
---

## Problem

Found by [`chore-0067`](done/chore-0067-the-with-hooks-placement-path-is-covered-by-no-test-and-no-gate.md)
while writing the first tests that path has ever had, and correctly reported rather than fixed there,
since `scripts/install.py` was outside that task's scope.

`install.py --tools opencode --with-hooks` copies the hooks module into the home it is given and then
says almost nothing about it, because **both** the "placed but INACTIVE" warning and the registration
block are gated on the same condition:

```text
grep -n 'hooks and "claude" in tools' scripts/install.py   ->  one hit, guarding both
```

So an opencode-only install prints `plus 4 hook(s).` and no registration, where a Claude install
prints the block a person is meant to paste.

**The second half is worse than the silence.** The module lands at `<home>/.agents/hooks`, and
`.opencode/plugins/zen-hooks.mjs` resolves its own `HOOKS_DIR` as `.agents/hooks` against
`worktree || directory || process.cwd()`, which is the **project** root rather than the home. So the
copy that was just placed is read by nothing, and nothing says so.

This is the failure `feat-0038` hit twice while establishing the module, "installed, correct-looking,
and doing nothing", arriving on the one path that has no warning attached to it. It is invisible by
construction: the exit code is 0, the summary line counts the files, and the only signal that the
placement is inert is knowing where the plugin looks.

Current behaviour is pinned, not endorsed, by
`test_hooks_placed_for_opencode_alone_are_announced_by_nothing` in
[`tests/test_install.py`](../tests/test_install.py). That test's docstring says explicitly that it
asserts what the code does rather than what it should do, and that the intended signal is the test
failing when this task fixes it.

## Scope

**In scope:** decide what an opencode-only `--with-hooks` install should do, and make it do that.

- **The decision comes first and it is not obvious.** At least three answers are defensible: warn that
  the placement is inert for opencode and place it anyway; place it where the opencode plugin actually
  reads and accept that this is project-scoped rather than home-scoped, which is a different contract
  from the Claude path; or refuse the combination and say why. Weigh them and record the rejected
  ones, because the shape of the fix is the deliverable and the diff follows from it.
- Whatever is chosen, **the run must say what happened**, per the same rule `chore-0058` and
  `chore-0065` fixed one level up: a placement that did nothing useful and a placement that worked
  must be distinguishable from each other in the output.
- Flip `test_hooks_placed_for_opencode_alone_are_announced_by_nothing` from a characterization pin to
  an assertion of the chosen behaviour, and say in its docstring that it changed sides.

**Out of scope:**

- `.opencode/plugins/zen-hooks.mjs` and the wiring tables in
  [`.agents/hooks/README.md`](../.agents/hooks/README.md), unless the chosen answer requires them. If
  it does, that is a contract change and it needs saying out loud rather than folding in.
- The `claude` path, which works and is covered.
- Registering anything in this repository's own `.claude/settings.json`. That exception is the
  author's and `AGENTS.md` says so.
- The latent `tool in HOOK_SUBPATHS` seam `chore-0067` also reported, which is unreachable while the
  two maps are identical and is pinned by `test_every_installable_tool_has_a_hook_path`.

## Implementation notes

Read `chore-0067`'s `## Decisions` first. It records why the codex asymmetry turned out not to be a
defect, which is the neighbouring question, and the reasoning transfers: a map key with no reader is
not automatically a gap.

The three-way choice above is a contract question about what `--with-hooks` promises per tool, so
check whether `docs/spec/install.md` says anything about hooks before deciding. As of 2026-08-27,
`grep -in hook docs/spec/install.md` returns nothing, which means the promise is unwritten and this
task may be the occasion to write it or may deliberately decline to.

## Risks and rollback

One module plus its tests, and a possible contract amendment, so this section is required.

The realistic failure is fixing the silence and leaving the placement inert, which produces a warning
nobody can act on. The guard: whichever answer is chosen, state where the file lands and who reads it,
in the output rather than only in the task file.

Reversible by reverting one commit. If a contract amendment is written, it follows the convention in
[`docs/spec/README.md`](../docs/spec/README.md) and leaves `status:` reading `approved`.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] An opencode-only `--with-hooks` install produces output that distinguishes what happened from a
      working Claude placement, and the closeout quotes both.
- [ ] The chosen answer is recorded with its rejected alternatives in the task's `## Decisions`.
- [ ] `test_hooks_placed_for_opencode_alone_are_announced_by_nothing` asserts the chosen behaviour
      rather than pinning the current one, and its docstring says it changed sides.
- [ ] The test is shown failing against the unfixed `install.py` before it passes against the fixed one.
- [ ] No file under `.agents/hooks/` and no harness registration is modified, or if one is, the
      contract change is stated rather than folded in.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
