---
id: bug-0032
title: test-author names an approved spec as its input and never checks the status, so it is the one spine skill that will derive tests from a draft
type: bug
status: done
priority: P2
parent: "ROADMAP Kit coherence hardening (2026-08-18 review pass)"
depends_on: []
touched_files:
  - .agents/skills/test-author/SKILL.md
created: 2026-08-18
---

## Problem

[`test-author`](../../.agents/skills/test-author/SKILL.md) names an approved spec as its input three
times: in its frontmatter description, in its opening line ("Turn an approved spec into runnable,
traceable tests"), and in its when-to-use list ("an implementation exists ... and its **approved**
spec's scenarios need tests"). Its Step 1 then gates only on `spec-quality` well-formedness. Nothing
reads the spec's `status` field.

Both of its siblings do, and both say why:

- [`verifier-agent`](../../.agents/skills/verifier-agent/SKILL.md): "**Is the contract approved?** If a
  spec is supplied and its `status` is not `approved`, the run is blocked ... verifying against it
  would launder an unapproved contract into evidence."
- [`new-task`](../../.agents/skills/new-task/SKILL.md): "**Refuse an unapproved spec.** If `status` is not
  `approved`, stop and say so."

So the same draft spec is refused by the skill that decomposes it into tasks and blocks the skill that
verifies against it, and is silently accepted by the skill that writes the tests. The asymmetry runs the
wrong way round. Well-formedness is not approval: `spec-quality` returns `ready`, meaning the spec is
answerable, which is precisely the state a spec is in while it waits for a human to approve it. So the
gate that exists passes exactly the case the missing gate should stop.

Tests are also the most durable form an unapproved contract can take. A draft spec can be edited or
abandoned; a test suite derived from it becomes the thing later work is measured against, and
`spec-conformance` and `verifier-agent` will cite those tests as evidence. `docs/spec/README.md`
records the amendment convention precisely because an unapproved contract must not silently become
authoritative, and this is the one door left open.

## Scope

**In scope:** add the status gate to `test-author` Step 1, in the shape its siblings already use, and
make the frontmatter and body consistent with it.

**Out of scope:**

- The `spec-quality` composition. Well-formedness is still required; this adds a check, it does not
  replace one.
- Characterization mode, which by definition has no spec and must stay reachable. The gate applies to
  the acceptance mode only, and saying so explicitly is part of the change, since
  [`chore-0040`](chore-0040-four-coherence-corrections-across-skill-bodies.md) separately makes
  `fix-batch` point at that mode.
- `verifier-agent` and `new-task`, which are correct.
- Whether the verdict should be `blocked` in `verifier-agent`'s sense. `test-author` has no verdict
  vocabulary and should not gain one; stopping and saying why is enough.

## Implementation notes

Mirror `new-task`'s wording rather than `verifier-agent`'s. `verifier-agent` returns a structured
`blocked` verdict because it is a reporting skill with an output schema; `test-author` writes files and
its sibling refusal shape is `new-task`'s "stop and say so", which is the right precedent.

State the reason, not just the rule. Both siblings give theirs, and the reason here is specific enough
to be worth writing: tests outlive the draft they came from, so a test derived from an unapproved
contract is how a draft becomes authoritative without anyone approving it.

Say explicitly that characterization mode is exempt. Without that sentence a reader applies the gate to
both modes and the mode that exists for code with no spec at all becomes unreachable.

## Decisions

- **Rejected: a lint or unit test for the gate.** `validate-skills.py` has no hook for asserting a
  phrase in a skill body (its only body-content check is the draft-versus-shipped status warning),
  so catching this class mechanically means a new check in `scripts/validate-skills.py` plus a case
  in `tests/test_validate_skills.py`, both outside this task's `touched_files`. Left unwritten
  rather than smuggled in.
- **Rejected: a separate precondition step mirroring `verifier-agent`'s "Establish that verification
  can run at all".** That shape carries a `blocked` verdict this skill has no vocabulary for, and
  the task scopes the change to Step 1. The gate went at the head of Step 1 instead, ahead of the
  `spec-quality` gate, so the cheaper check runs first.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] `test-author` Step 1 stops when a supplied spec's `status` is not `approved`, and says why.
- [x] The exemption for characterization mode is stated where the gate is stated.
- [x] The frontmatter description and the body agree that acceptance mode requires an approved spec.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
