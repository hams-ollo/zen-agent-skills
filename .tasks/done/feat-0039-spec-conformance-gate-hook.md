---
id: feat-0039
title: Add the spec-conformance gate hook, adapted so 'approved' is not treated as a closing status
type: feat
status: done
priority: P1
parent: "ROADMAP Epic B #13: telemetry-guard (reframed as enforcement hooks)"
depends_on: [feat-0038, chore-0025]
touched_files:
  - AGENTS.md
  - docs/CATALOG.md
created: 2026-08-05
---

## Problem

The kit's conformance convention (an approved spec gets a `<stem>.conformance.md` sibling recording
the audit) is enforced by nothing. `chore-0025` exists because four of nine specs quietly went
without one for months. Backfilling them fixes the state; it does not stop the same drift from
happening again on the tenth spec.

Balarama Bosch's [repoprompt-workflows](https://github.com/moonray/repoprompt-workflows) (MIT) ships
`spec-conformance-gate.py`, which is the deterministic-gate case of the hook contract established in
`feat-0038`. It fires `PostToolUse` on file edits, detects spec-like files three ways (a path
segment of `spec`/`specs`/`specifications`, a `*.spec.md` filename, or a frontmatter `type` in a
known set), reads the frontmatter `status`, checks for a sibling matrix or a frontmatter reference
to one, and returns `{"decision": "block", "reason": ...}` when a spec reaches a closing status
without one. Its stated rationale is the right one: green tests assert code contracts, not spec
conformance.

**The adaptation that matters, and the reason this is not a copy job.** Upstream's terminal-status
set is:

    implemented, shipped, done, closed, complete, completed, resolved, final, released, verified, approved

`approved` is in that list. In this kit `approved` does not mean closed. It means the opposite end of
the lifecycle: a human has signed off on the contract so that
[`new-task`](../../.agents/skills/new-task/SKILL.md) may decompose it, which is the `S-003` gate
[`spec-author`](../../.agents/skills/spec-author/SKILL.md) enforces. Every one of this repository's nine
specs is `status: approved` right now. Dropping upstream's file in unmodified would block the next
edit to all nine, and would demand a conformance matrix for a spec whose implementation has not been
written yet. The hook would be uninstalled within an hour and the idea would be discredited by its
own first run.

## Scope

**In scope:**

- Author `.agents/hooks/spec-conformance-gate.py` on the module contract from `feat-0038`, adapted:
  - Remove `approved` from the terminal set, and document in the docstring why, since the removal
    looks like an oversight to anyone reading it against upstream.
  - Keep the sibling-matrix detection, including the frontmatter-reference escape
    (`conformance:` / `conformed:` / `audited:`), which gives an author a way out that is a written
    claim rather than a silent bypass.
  - Keep the multi-harness payload handling. Upstream already parses both a Claude-style
    `tool_input.file_path` and a Codex/opencode `apply_patch` command body, so the portability work
    here is smaller than it looks.
- Register it in all three harness wirings created by `feat-0038`.
- Add tests covering the block path, the pass path, and specifically the `approved` case, so the
  adaptation is pinned by a test and cannot be silently reverted by a future upstream sync.

New file: `.agents/hooks/spec-conformance-gate.py`. Tests extend `tests/test_hooks.py`.

**Out of scope:**

- Backfilling the four missing matrices. That is `chore-0025` and is a hard prerequisite: switching
  this on first means the repository blocks on its own files.
- Any gate on issue-based closes. Upstream documents this limit explicitly and does not handle it,
  and neither should this: a GitHub issue closing does not touch a spec file, so there is no payload
  to decide from. Note it in the docstring.
- Reworking the kit's spec lifecycle statuses. Renaming `approved` to something upstream would not
  match was considered and rejected: it churns nine specs and every skill that reads the field, to
  avoid a one-line change in a set literal.

## Implementation notes

Read the upstream source at
`https://raw.githubusercontent.com/moonray/repoprompt-workflows/main/.agents/hooks/spec-conformance-gate.py`
before writing. Its `_evaluate(path)` is already factored out of `main()` so one `apply_patch`
touching several files can be checked per path, which is also what makes it straightforward to test.

Decide during implementation which status actually means closed here. The kit's specs use `approved`
and nothing else today, so the terminal set may have no members that occur in this repository at
all, which would make the gate correct and inert. That is an acceptable outcome and worth stating in
the task's closeout, but check first whether `verifier-agent` or `spec-conformance` already writes a
closing status somewhere before concluding the set should be empty.

Consider whether the gate should also fire when a spec is edited while its sibling matrix is older
than the spec, which is the staleness case. Do not build it in this task; record the decision.

## Risks and rollback

This hook can block a user's session, which no other artifact in the kit can do. It touches more
than one module (`.agents/hooks/`, the three harness registrations, `tests/`), so the rule fires.

The failure mode to guard against is a false block: a file the detector thinks is a spec, in a
status the set thinks is closing, with a matrix the detector fails to find. The frontmatter escape
hatch is the mitigation, and the block message must name it so a user who hits a false positive can
get past it without reading the source.

Rollback is a revert plus re-running the installer, since the hook is a separate file and its
registration is additive.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" -v && python .tasks/validate.py --strict && python scripts/install.py --dry-run --home ./.tmp/zen-home

- [ ] A test asserts a spec edited to a closing status with no sibling matrix produces
      `{"decision": "block", ...}` and that the reason names the frontmatter escape.
- [ ] A test asserts a spec with `status: approved` and no matrix produces **no** block, and its name
      states that this is the deliberate divergence from upstream.
- [ ] A test asserts a spec with a sibling `<stem>.conformance.md` passes.
- [ ] A test drives the `apply_patch` payload shape, not only the `file_path` shape.
- [ ] Running the hook against every file in `docs/spec/` produces zero blocks after `chore-0025`.
- [ ] Existing tests still pass.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
