---
id: feat-0019
title: Draft the verifier-agent skill (composes spec-conformance, from its own spec)
type: feat
status: done
priority: P1
parent: "ROADMAP Epic B #7: verifier-agent"
depends_on: []
touched_files:
  - .agents/skills/verifier-agent/SKILL.md
created: 2026-07-24
---

## Problem

ROADMAP Epic B item 7 is `verifier-agent`: independently test an implementation against its approved
specification and task acceptance criteria before reconciliation, composing the blessed
[`spec-conformance`](../../.agents/skills/spec-conformance/SKILL.md) lens, producing structured pass,
fail, or blocked evidence, running the declared commands, and never editing the implementation it
verifies. The behavioral contract is approved at
[`docs/spec/verifier-agent.md`](../../docs/spec/verifier-agent.md), drafted by `spec-author` and
self-checked to `ready` by `spec-quality`.

It is the last core skill of the delivery loop. Every other stage exists:
[`spec-conformance`](../../.agents/skills/spec-conformance/SKILL.md) already forward-declares this skill
as its composer, and [`fix-batch`](../../.agents/skills/fix-batch/SKILL.md) requires an independent
verification pass but leaves its procedure to the agent running it, so verification depth and
evidence vary between runs. Nothing today combines a command result, a conformance matrix, and a
task's acceptance criteria into a single deterministic verdict, which is what makes "verified" an
assertion rather than a record.

## Scope

**In scope:** author `.agents/skills/verifier-agent/SKILL.md`, harness-agnostic, delivering scenarios
S-001 through S-010 of the spec: read the approved spec and the task acceptance criteria; refuse to
verify against an unapproved (`status: draft`) spec by returning `blocked`; run the declared
verification commands and record each exact outcome; return `blocked` rather than substituting a
command when none is declared or its runner is absent; compose `spec-conformance` for the conformance
matrix so a to-fix divergence fails the run even when every command passes, while a divergence
already recorded as accepted-with-reason does not; map each acceptance criterion to `met` or `unmet`
with named evidence; verify against criteria alone when no spec exists, stating that conformance was
not assessed; emit a deterministic `pass | fail | blocked` verdict in a `## Output format` schema
following the [`spec-plan-readiness`](../../.agents/skills/spec-plan-readiness/SKILL.md) idiom; return
the report inline unless a destination is supplied; and never edit the implementation, its tests, or
its spec, reporting repairable defects as findings instead. Cross-link `spec-conformance`,
`test-author`, `fix-batch`, and `spec-plan-readiness`. Mark it a draft in `ROADMAP.md` and
`docs/CATALOG.md`.

**Out of scope:** blessing the skill (waits for a real dogfood, verifying `scripts/validate-skills.py`
against `docs/spec/validate-skills.md`); building `user-testing` (Epic B #8); changing
`spec-conformance`, `fix-batch`, or the approved spec; wiring the skill into `fix-batch`'s
verification pass, which is a separate follow-up once this skill has been used.

## Implementation notes

- Compose `spec-conformance` **by reference only**. Do not restate its matrix rules or re-derive the
  `Conformed`/`Diverged`/`Not-built` classification inline; the two must not drift.
- The `blocked` verdict is the point of Goal 5 and carries the skill's honesty: a verification that
  could not run must never be recorded as a pass or a fail. Give it equal weight in the procedure,
  not a footnote.
- Mirror the deterministic-verdict idiom of `spec-plan-readiness`: a fenced `text` block with an
  ordered field schema, plus an explicit rule for when each verdict applies, so two runs over the
  same evidence agree.
- Mirror the never-edit discipline `test-author` already states for production code
  ([`test-author/SKILL.md`](../../.agents/skills/test-author/SKILL.md) step 4), and keep the structure
  of that skill: intro positioning against siblings, `## When to use` / `## When not to use`,
  `## Inputs`, numbered `## Procedure`, `## Output format`, `## Notes`, `## Conventions`.
- Independence is the reason this skill exists. Say plainly that the verifier should not be the agent
  that wrote the implementation where the harness allows that separation.
- Follow [`.agents/rules/house-style.md`](../../.agents/rules/house-style.md); keep the body under the
  500-line guideline.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [x] `.agents/skills/verifier-agent/SKILL.md` exists with valid frontmatter (`name` equals the
      directory, non-thin `description`).
- [x] `scripts/validate-skills.py` exits 0 with the new skill present.
- [x] Body composes `spec-conformance` by reference (no inline restatement of its matrix rules) and
      cross-links `test-author`, `fix-batch`, and `spec-plan-readiness`.
- [x] Body contains an `## Output format` section defining a deterministic verdict schema whose
      values are exactly `pass`, `fail`, and `blocked`, with a stated rule for each.
- [x] Body states the never-edit rule, the unapproved-spec block, the undeclared-command block, the
      accepted-with-reason exemption, and the inline-report default.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md section 6 followed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
- [x] Skill left as a draft; ROADMAP/CATALOG mark it draft (pending dogfood), not shipped.
