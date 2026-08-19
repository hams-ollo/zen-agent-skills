---
id: bug-0036
title: Adapter asset emission copies __pycache__ and .pyc into every generated tree, which the installer explicitly refuses to do
type: bug
status: done
priority: P2
parent: "ROADMAP Epic A: distribution tooling"
depends_on: [chore-0042]
spec: "docs/spec/build-adapters.md"
touched_files:
  - scripts/build-adapters.py
  - tests/test_build_adapters.py
created: 2026-08-18
---

## Problem

`emit_skill_assets()` in [`build-adapters.py`](../../scripts/build-adapters.py) walks a skill's
directory with `skill_dir.rglob("*")` and copies every file that is not `SKILL.md`, with no
exclusion of any kind:

```python
for src in sorted(skill_dir.rglob("*")):
    if not src.is_file() or src.name == "SKILL.md":
        continue
```

So a checkout that has run the test suite emits
`init-worktracking/templates/__pycache__/validate.cpython-311.pyc` into the Cursor tree, the
VS Code tree, and the plugin tree. An adopter receives compiled Python bytecode inside what is meant
to be a portable, human-readable skill payload.

**The installer already knows this hazard by name and refuses it, twice.**
[`install.py`](../../scripts/install.py) filters it at line 301, under a comment at line 299 saying the
templates directory grows a `__pycache__` "as soon as anything imports it and the copy deliberately
has none", and again at line 741 with
`shutil.copytree(..., ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))`. `build-adapters.py`
contains the string `pycache` zero times. Two tools place the same payload and only one of them is
careful.

The condition became reachable on 2026-08-18. `bug-0026` added tests that import the shipped
template validator, which is what creates the `__pycache__` in the first place, and that task's own
agent noted the directory appearing and correctly concluded `install.py` was already safe. It did not
check the other emitter. Found by `chore-0042`'s agent, which noticed the `.pyc` only because it was
the single CRLF-containing file in an emitted tree.

Two reasons it stayed invisible: the artefacts are gitignored here, so nothing in this repository's
own status or diff shows them, and the `adapters dry run` gate counts files rather than inspecting
them, so a run that emits bytecode looks exactly like one that does not.

## Scope

**In scope:** exclude `__pycache__` directories and `.pyc` files from adapter asset emission, and
cover it with a test that fails against the current code.

**Out of scope:**

- `install.py`, which is already correct and is the reference for what the exclusion should be. Reuse
  its rule rather than inventing a second spelling of it, but do not refactor the two into one
  helper: the two tools have different copy mechanics and a shared helper is a bigger change than
  this defect justifies.
- Any other filtering. This task excludes build artefacts, not, for example, dotfiles or large
  assets, which are separate questions nobody has asked.
- Whether `emit_skill_assets` should copy anything other than `templates/`. A narrower allow-list
  might be better and is a design change; excluding bytecode is the defect fix.
- `docs/spec/build-adapters.md`. Whether the contract should state the exclusion is worth asking at
  closeout, but `chore-0043` is already amending that spec and two tasks editing it in parallel
  collide.

## Implementation notes

Match `install.py`'s predicate rather than paraphrasing it: suffix is not `.pyc` **and**
`__pycache__` is not among the relative path's parts. The directory check matters on its own, since
a future artefact inside `__pycache__` with a different suffix should still be excluded.

The test is the durable half and it has to be built rather than observed, because the condition
depends on whether the suite has been run in that checkout. Create the `__pycache__` and a fake
`.pyc` in a fixture skill directory, emit, and assert neither appears in the output. A test that
merely runs the emitter against the real tree passes or fails depending on ordering, which is worse
than no test.

`depends_on: [chore-0042]` is a file collision: that task edits `_write` in the same module.

## Decisions

- **Rejected: a shared exclusion helper across the two tools.** The predicate is now spelled twice,
  once in `install.py`'s `_digestable` and once inline in `emit_skill_assets`, which the scope
  section rules on. The comment on the adapter side names `install.py` as the rule it mirrors, so
  the duplication is discoverable rather than accidental.
- **Rejected: filtering at the `main()` accounting layer instead of inside the emitter.** Excluding
  a file from the write but not from the returned list would have left the reported asset count
  describing files nobody wrote, which is exactly the divergence `bug-0025` closed. The skip is
  before both the copy and the append, and the test asserts on the returned list as well as on disk.
- **Seam left open deliberately: `docs/spec/build-adapters.md` is unchanged.** The contract still
  does not state the exclusion, per this task's scope, because `chore-0043` is amending that file in
  parallel. Whoever closes this decides whether the contract should name it.
- **Premise confirmed, with one addition.** The task predicted three artefacts would leak; against
  the pre-fix code the fixture emitted all three (`loose.pyc`, `templates/__pycache__/*.pyc`, and a
  non-`.pyc` file inside `__pycache__`) into all three layouts, cursor, vscode, and plugin. The
  third of those is why the directory half of the predicate is carried rather than only the suffix
  half.

## Risks and rollback

Two files in one module, so the more-than-one-module rule does not fire.

The way this fix goes wrong is by excluding more than intended. `emit_skill_assets` is what carries
`templates/` into an adopter's tree, and `init-worktracking` is unusable without its nine templates,
one of which is a real `validate.py` that must not be caught by a rule aimed at `.pyc`. Assert that a
`.py` file under `templates/` still emits, in the same test.

Reversible by reverting one commit. Nothing already generated changes until the next build.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [x] A `__pycache__` directory and a `.pyc` file in a fixture skill directory are absent from every
      emitted target, proven by a test that fails against the current code.
- [x] A `.py` file that is not bytecode, such as the shipped `templates/validate.py`, still emits,
      proven in the same test.
- [x] The exclusion predicate matches `install.py`'s in both halves, suffix and path part.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
