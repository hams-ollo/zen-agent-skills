---
id: chore-0038
title: Five one-line upkeep items from the 2026-08-08 review, bundled because none is worth its own round trip
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [chore-0037]
touched_files:
  - .github/workflows/checks.yml
  - .agents/hooks/README.md
  - .claude/settings.json
  - .agents/hooks/spec-conformance-gate.py
  - scripts/install.py
  - tests/test_hooks_conformance_gate.py
created: 2026-08-08
---

## Problem

Five items found in the 2026-08-08 review, each a small correction with no interesting design
question behind it. They are bundled deliberately: every one is a line or two, and the authoring and
verification overhead of five task files would exceed the work. The bundling is the exception rather
than the pattern, and the reason is written here so a later reader does not take it as licence.

**1. The workflow pins two actions a major version behind.**
[`checks.yml`](../.github/workflows/checks.yml) uses `actions/checkout@v4` and
`actions/setup-python@v5`, each one major behind and running on the older Node runtime. Nothing is
broken; this is upkeep before it becomes a deprecation warning on every run of every matrix cell.

**2. The hooks README points every new hook's tests at one file.**
[The hooks module contract](../.agents/hooks/README.md) says "add tests to `tests/test_hooks.py`".
The last two hooks put theirs in `tests/test_hooks_reachability.py` and
`tests/test_hooks_conformance_gate.py`, so the instruction describes what the module stopped doing
two hooks ago.

**3. The committed hook registration uses a repository-relative path.**
[`.claude/settings.json`](../.claude/settings.json) runs
`python3 .agents/hooks/skill-reachability-reminder.py`, which resolves only when the hook's working
directory is the repository root. Reproduced 2026-08-08 from a subdirectory:

```text
rc=2   python3: can't open file '.../docs/.agents/hooks/skill-reachability-reminder.py'
```

Claude Code exposes `$CLAUDE_PROJECT_DIR` for exactly this, and using it removes a dependency on the
working directory that nothing else guarantees.

**4. `--tools` is not de-duplicated.** `python scripts/install.py --tools claude,claude` reports
"x 2 tool(s)" and does the work twice. Cosmetic, and the count it prints is wrong.

**5. The conformance gate joins a frontmatter value without bounding it.**
`_evaluate_task_close()` in [`spec-conformance-gate.py`](../.agents/hooks/spec-conformance-gate.py)
does `os.path.join(_repo_root(path, cwd), spec_ref)`, so an absolute `spec:` value discards the root
and escapes it. The hook only reads a file head and never emits its contents, so the impact today is
nil. Bounding the join costs one line and removes the question.

## Scope

**In scope:** the five corrections above.

**Out of scope:**

- Pinning actions by commit SHA. That is a different hardening posture with its own maintenance cost,
  and adopting it is a decision rather than upkeep.
- Registering a second hook in `.claude/settings.json`, or changing which hook it registers. Item 3
  changes **how the existing command names its file** and nothing else. The exception recorded in the
  conventions section of [`AGENTS.md`](../AGENTS.md) stays exactly one hook, in the reminder shape.
- The `python3` versus `python` interpreter choice, which is a stated platform trade documented inside
  the settings file.
- Any behaviour change to the gate beyond bounding the join.

## Implementation notes

Item 3 interacts with [`chore-0037`](chore-0037-committed-hook-registration-is-untested.md), which is
why this task depends on it. That task adds a test asserting the settings file names a hook that
exists; this one changes how the name is written. Do them in that order so the test exists first and
the change has to keep it passing, and make the test tolerant of a `$CLAUDE_PROJECT_DIR` prefix rather
than pinning the bare relative spelling.

Item 3 also needs a sentence in the `_comment` block already inside the settings file, since that
block explains every other choice in it and an unexplained change there reads as drift.

Item 5: reject an absolute `spec_ref`, or normalise and confirm the result is still under the root.
Rejecting is simpler and matches how the surrounding code already treats a reference that does not
resolve, which is to stay silent because that is the validator's finding rather than the gate's.

Item 1 should be verified rather than assumed: check what the current majors actually are at the time
of the change rather than taking the numbers in this task file, which were written on 2026-08-08.

## Risks and rollback

Touches CI, a hook, a hook registration, and the installer, so it meets the more-than-one-module rule.
The one item that can fail invisibly is item 3: a wrong path makes the hook not run, and a hook that
does not run looks identical to one that ran and found skills reachable. Verify it by running the hook
through the registered command from at least two working directories, not by reading it.

Item 1 can fail loudly on CI and is reversible by reverting the two version bumps. Everything else is
reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [ ] Both actions are bumped, verified against the current majors at the time of the change, and CI
      passes on all six matrix cells.
- [ ] The hooks README names where a new hook's tests go, matching what the module now does.
- [ ] The settings command resolves independently of the working directory, demonstrated from a
      subdirectory as well as from the root, and `chore-0037`'s assertion still passes.
- [ ] The settings file's `_comment` block explains the path form.
- [ ] `--tools claude,claude` places one set and reports one tool, covered by a test.
- [ ] An absolute `spec:` value cannot make the gate read outside the repository root, covered by a
      test.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
