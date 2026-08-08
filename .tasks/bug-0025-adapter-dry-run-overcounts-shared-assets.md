---
id: bug-0025
title: build-adapters --dry-run overstates the shared assets a real run writes, by a factor of the skill count
type: bug
status: open
priority: P2
parent: "ROADMAP Epic A: distribution tooling"
depends_on: []
spec: "docs/spec/build-adapters.md"
scenarios: []
touched_files:
  - scripts/build-adapters.py
  - tests/test_build_adapters.py
created: 2026-08-08
---

## Problem

`emit_shared_assets()` in [`build-adapters.py`](../scripts/build-adapters.py) is called once per
skill, and it re-emits the rules module every time. On a real run the second and later calls
short-circuit on `dest.exists()`. Under `--dry-run` nothing is written, so that guard never becomes
true and the rules files are counted once per skill.

Measured 2026-08-08 into an empty output directory:

```text
$ python3 scripts/build-adapters.py --dry-run --out $EMPTY
[dry-run] Generated 40 adapter file(s) for 20 skill(s), plus 74 shared asset file(s)

$ python3 scripts/build-adapters.py --out $EMPTY
          Generated 40 adapter file(s) for 20 skill(s), plus 17 shared asset file(s)
```

The arithmetic is exact: 3 rules files x 20 skills + 14 skill-local supporting files = 74, against 3
+ 14 = 17. The function's own docstring says "The rules module, once per run", which is what a real
run does and not what the preview reports.

**The acceptance gate cannot catch it.** [`run-checks.py`](../scripts/run-checks.py) runs the adapter
dry run with the default `--out .`, where every destination equals its source, both branches skip on
`dest.resolve() == src.resolve()`, and the count is 0 whether the bug is present or not. So the one
gate covering this path exercises the reporting code only in the configuration where it carries no
information.

A preview whose numbers do not describe the run it previews is the class this repository is least
willing to tolerate, and [`SECURITY.md`](../SECURITY.md) names it directly under "tooling that writes
outside its declared scope".

## Scope

**In scope:** make the dry run report the file count a real run would write, and give the gate a
configuration where the number is load-bearing.

**Out of scope:**

- The "never clobber a project's own rules file" rule. That `dest.exists()` guard is `S-010` and
  `S-014` behaviour and stays exactly as it is for the real path.
- Emitting the rules module per skill rather than per run. The current real-run behaviour is correct;
  only the counting is wrong.
- The plugin target's layout or manifests.

## Implementation notes

Two shapes are available and they are not equivalent.

Hoist the rules-module emission out of the per-skill loop in `main()` so it runs once per layout,
which makes the count correct by construction and matches what the docstring already claims. Or track
what a dry run would have written and consult that set alongside `dest.exists()`, which leaves the
call structure alone at the cost of carrying state. The first is smaller and removes the divergence
rather than compensating for it; take it unless something in the layout loop makes it wrong.

`emit_shared_assets()` returns the list it wrote, and `main()` only sums the length. If the rules half
moves out, the return contract changes, so check both call sites.

**The gate is half the fix.** Add a `--out` that is not the repository root to the adapters gate in
`run-checks.py`, or add a test that asserts dry-run and real-run counts agree for the same output
directory. Without one of those, the same class recurs and nothing notices. A temporary directory
under `.tmp/` matches what the install gates already do and is already gitignored.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [ ] A test asserting the dry-run asset count equals the real-run asset count for the same non-root
      `--out`. It must fail against the current `build-adapters.py`.
- [ ] A test that a real run still writes each rules file exactly once.
- [ ] A test that an output directory already holding a rules file still has it left alone, in both
      dry and real runs.
- [ ] Emitting into the repository root itself still reports 0 assets and writes nothing, so building
      into the kit is unchanged.
- [ ] The adapters gate exercises a configuration where the asset count is non-zero.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
