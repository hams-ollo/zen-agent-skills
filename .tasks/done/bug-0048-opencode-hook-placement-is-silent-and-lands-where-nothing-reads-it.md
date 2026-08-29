---
id: bug-0048
title: Hooks placed for opencode alone are announced by nothing and land where the opencode plugin never looks
type: bug
status: done
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [chore-0067]
touched_files:
  - scripts/install.py
  - tests/test_install.py
created: 2026-08-27
---

## Problem

Found by [`chore-0067`](chore-0067-the-with-hooks-placement-path-is-covered-by-no-test-and-no-gate.md)
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
[`tests/test_install.py`](../../tests/test_install.py). That test's docstring says explicitly that it
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
  [`.agents/hooks/README.md`](../../.agents/hooks/README.md), unless the chosen answer requires them. If
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

## Decisions

**Chosen: warn and place, with the warning decided from the filesystem rather than fixed.** An
opencode run now names where the module landed, names the plugin that would have to read it, and
reports `LIVE` when `<home>/.opencode/plugins/zen-hooks.mjs` exists and `INERT` when it does not. A
single fixed sentence would not have satisfied the rule this task inherited from `chore-0058` and
`chore-0065`, since a placement that worked and one that did nothing useful have to be
distinguishable in the output, and one sentence printed either way distinguishes nothing.

**Rejected: place it where the opencode plugin actually reads.** Blocked twice over, and the second
reason was not known when this task was written. `install.py` is home-scoped by construction: `--home`,
`TOOL_SUBPATHS`, `HOOK_SUBPATHS`, the manifest, and `--uninstall` all key off one home, so a
project-scoped placement is a new surface and a different contract, exactly as the task warned. The
new reason is that it would not have made the copy live either: `grep -rn zen-hooks` finds
`.opencode/plugins/zen-hooks.mjs` only as this repository's own committed wiring, and nothing under
`scripts/` distributes it, so the move would trade an inert home-scoped copy for an inert
project-scoped one waiting on a reader nothing installs. Shipping the plugin and adding a project
scope is a feature, not this bug's fix.

**Rejected: refuse the combination.** It would have removed the one configuration in which the
opencode half of `--with-hooks` currently works. `--home <project root>` places
`<project>/.agents/hooks`, which is exactly the path the plugin resolves against its own root, so the
placement is correct there and refusing it would delete a working case to fix a message.
`test_an_opencode_placement_a_plugin_would_read_is_reported_live` pins that case.

**A premise narrowed: the placement is conditionally inert, not unconditionally.** The problem
statement says "the copy that was just placed is read by nothing", which holds for the default home
and not for `--home <project root>`. The output says which of the two happened rather than asserting
the common case.

**Seam left open deliberately: `docs/spec/install.md` is still not amended, and hooks remain
uncontracted there.** `grep -in hook docs/spec/install.md` still returns nothing. Every amendment in
that file records the author's explicit instruction and this task carries none, which is the same
reason `chore-0031` recorded for declining, and an amendment would add a fifth spec to the author's
re-approval queue without being asked. The contract worth writing is also wider than this bug: what
`--with-hooks` promises per tool cannot be settled while the opencode reader is undistributed, so a
scenario covering only the message would pin half a contract and imply the other half was decided.

**Seam left open deliberately: the latent `tool in HOOK_SUBPATHS` skip is untouched**, as scoped.
`test_every_installable_tool_has_a_hook_path` still pins it. The activation note is driven off the
tools that actually received a module rather than off `tools`, so it cannot speak for a tool the
placement loop skipped, but the skip itself is still wordless and is still `chore-0067`'s finding.

**The flipped test was renamed.** `test_hooks_placed_for_opencode_alone_are_announced_by_nothing`
asserts the opposite of its name once flipped, and a name stating the behaviour it disproves is the
stale signal this repository keeps paying for. It is now
`test_hooks_placed_for_opencode_alone_are_announced_and_named_inert`; its docstring carries the old
name, says it changed sides, and quotes what the pin used to assert, so the old name is still
greppable.

## Risks and rollback

One module plus its tests, and a possible contract amendment, so this section is required.

The realistic failure is fixing the silence and leaving the placement inert, which produces a warning
nobody can act on. The guard: whichever answer is chosen, state where the file lands and who reads it,
in the output rather than only in the task file.

Reversible by reverting one commit. If a contract amendment is written, it follows the convention in
[`docs/spec/README.md`](../../docs/spec/README.md) and leaves `status:` reading `approved`.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] An opencode-only `--with-hooks` install produces output that distinguishes what happened from a
      working Claude placement, and the closeout quotes both.
- [x] The chosen answer is recorded with its rejected alternatives in the task's `## Decisions`.
- [x] `test_hooks_placed_for_opencode_alone_are_announced_by_nothing` asserts the chosen behaviour
      rather than pinning the current one, and its docstring says it changed sides.
- [x] The test is shown failing against the unfixed `install.py` before it passes against the fixed one.
- [x] No file under `.agents/hooks/` and no harness registration is modified, or if one is, the
      contract change is stated rather than folded in.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
