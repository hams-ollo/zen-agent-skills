---
id: bug-0060
title: A skill's frontmatter name becomes a path component with no containment check, so an adapter can be written outside the selected output root
type: bug
status: done
priority: P1
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
spec: docs/spec/build-adapters.md
scenarios: []
touched_files:
  - scripts/build-adapters.py
  - tests/test_build_adapters.py
created: 2026-08-31
---

## Problem

[`build-adapters.py`](../../scripts/build-adapters.py) reads a skill's frontmatter and hands the
`name` value straight to an emitter, which puts it in a path:

```python
name = fm.get("name", d.name)
...
dest = EMITTERS[t](d, name, desc, body, out, args.dry_run)

def emit_cursor(src: Path, name, desc, body, out: Path, dry: bool) -> Path:
    dest = out / ".cursor" / "rules" / f"{name}.mdc"
```

`_write` then does `dest.parent.mkdir(parents=True, exist_ok=True)` and writes, whatever `dest`
resolved to. Nothing between the frontmatter and the disk asks whether the destination is still
under `out`.

**The escape was already anticipated at display time and not at write time.** The line that reports
each emitted file guards for exactly this:

    print(f"{tag}{t:7} {name}  -> {dest.relative_to(out) if dest.is_relative_to(out) else dest}")

A destination that is not relative to `out` is a case this file already knows can happen. It prints
it and writes it.

**Measured on 2026-08-31**, on a temporary output root that was removed afterwards. The name was
inert text, not a payload:

```text
cursor: contained=False escaped_file_exists=True
        dest=...\nested\out\.cursor\rules\..\..\..\escaped-cursor.mdc
vscode: contained=False escaped_file_exists=True
        dest=...\nested\out\.github\prompts\..\..\..\escaped-vscode.prompt.md
```

Both link-rewriting emitters escape. `emit_plugin` does not, because it builds its destination from
`src.name`, the source **directory**, and says so in its docstring.

**What limits this today, and what does not.** [`validate-skills.py`](../../scripts/validate-skills.py)
already rejects a mismatch, `name {name!r} != directory {d.name!r}`, and
[`run-checks.py`](../../scripts/run-checks.py) runs that gate before the adapters gate, which is itself
`--dry-run` and writes nothing. So inside this repository the path needs a merge past a red gate.
What that does not cover is the case the tool is actually for: `build-adapters.py` is a standalone
script an adopter runs with `--out` pointed at their own project, over a skill tree this kit's
validator never saw. [`SECURITY.md`](../../SECURITY.md) names this class in its own words, "tooling
that writes outside its declared scope, for example `install.py` or `build-adapters.py` touching a
path they never announced", so the bar is the maintainer's own.

## Scope

**In scope:** a destination outside the resolved output root is refused, and the run says so.

- **The check goes at `_write`**, the single shared write boundary, so every present and future
  emitter inherits it instead of each one restating it. Compare resolved paths, since the escape
  above is a `..` segment that only appears after resolution.
- **Reuse the rule that already exists** rather than writing a second name grammar: the frontmatter
  `name` must equal the source directory name, which is what `validate-skills.py` already states.
  A mismatch is a refusal here too, before an emitter is dispatched.
- **Refusing is a run-level failure, not a skipped skill.** Goal 6 of the contract is "fail clearly
  on an unusable invocation rather than writing a partial result", and a tree carrying such a name
  is unusable. Follow the existing exit-code vocabulary in this file: `2` is could-not-run.
- **A traversal test per link-rewriting target**, asserting on the filesystem (nothing exists
  outside the root) and not only on the return value.

**Out of scope:**

- **The contract half.** No scenario in [`build-adapters.md`](../../docs/spec/build-adapters.md)
  governs where a write may land, so this guard closes a gap the spec never spoke to rather than
  changing anything it requires. Amending it is `chore-0087`, filed separately following the
  precedent `chore-0043` set for `bug-0028`. `scenarios` is empty here for that reason, and it is
  the honest value rather than a placeholder.
- `emit_plugin`, which derives its destination from the source directory and is not affected. Do not
  change it to use the frontmatter `name` for symmetry.
- `validate-skills.py`. It already carries the rule; this task borrows it, it does not move it.
- Absolute-path names, drive letters, and reserved Windows device names. They belong to the same
  family and a containment check on the resolved path answers the first two by construction. If the
  test finds a case the containment check misses, widen the test and say so rather than adding a
  second mechanism.

## Implementation notes

`Path.resolve()` is the operation that turns `out/.cursor/rules/../../../escaped.mdc` into
something comparable; `is_relative_to` on unresolved paths answers the wrong question. `out` is
already resolved in `_main`, so resolve `dest` and compare against it.

`_write` currently returns early on `dry`, so a dry run never reaches the check. Decide deliberately:
a preview that reports a destination it would refuse to write is misleading, and the cheapest honest
answer is to check before the `dry` branch so `--dry-run` fails on the same input a real run would.
The adapters gate in `run-checks.py` is a dry run, which is the reason this matters.

`emit_plugin_manifests` also calls `_write`, with a destination the tool constructs itself. The check
must not make that path noisy.

## Decisions

- **Rejected: reporting the two refusals on stderr.** Both print to stdout, because `_main`'s one
  existing exit-2 refusal (`Unknown target(s)`) already does, and `_run` in the test suite reads
  stdout. The `main()` backstop keeps stderr to match the `NotUTF8` handler it sits beside. Nothing
  turns on it for the gate: `run-checks.py` concatenates a gate's stdout and stderr before picking
  its summary line.
- **A contradiction inside this task, resolved toward Scope.** Scope bullet 2 requires the name
  refusal *before an emitter is dispatched*, which is what leaves no destination to name, and
  acceptance criterion 3 requires a message *naming the skill and the destination*. Independent
  verification failed the task on the criterion. Scope bullet 2 was kept, and the message was widened
  instead: it now names one requested target's destination, labelled representative rather than
  offered as the only one, read from `NAME_DESTINATIONS` so the refusal and the emitter cannot
  disagree about where a name lands. No emitter is dispatched to obtain it. The first attempt named
  the output root alone, which is what failed: a reader could not see that the name escapes at all,
  and the escape is what carries the severity.
- **Rejected: reconstructing the destination inside the refusal.** That is the second source of truth
  this repository treats as a defect class, and its failure mode here is a refusal confidently naming
  a path the tool no longer emits. Extracting `NAME_DESTINATIONS` costs `emit_cursor` and
  `emit_vscode` one level of indirection and buys one place to change. `emit_plugin` stays out of it,
  per Scope: it derives its destination from the source directory, so a `name` is never a path
  component there, and a plugin-only run says so rather than claiming an escape that cannot happen.
- **Seam left open: `emit_rules_module` and `emit_skill_assets` still copy with `shutil.copy2` and
  do not pass through `_write`.** Deliberate, not an oversight. Both build their destination from a
  real filesystem entry relative to a real source directory, so no `..` segment can enter the way a
  frontmatter string does, and routing a binary copy through a text writer to share the guard is a
  larger change than this defect warrants. A future emitter that writes *text* inherits the check by
  calling `_write`, which is what putting it there bought.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] A test per link-rewriting target (`cursor`, `vscode`) drives a traversal name and asserts **no
      file exists outside the resolved output root** afterwards.
- [x] Those tests fail against the current code. Confirm the failure before the fix.
- [x] A traversal name makes the run exit non-zero with a message naming the skill and the
      destination, rather than skipping quietly.
- [x] `--dry-run` refuses the same input a real run refuses.
- [x] A normal run over this repository's own skills emits exactly what it emits today: same file
      count, same destinations. The guard must be invisible on valid input.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
