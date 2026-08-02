---
id: feat-0024
title: Exercise verifier-agent's blocked verdict on real work and set the evaluation-record format
type: feat
status: done
priority: P1
parent: "ROADMAP Epic A #8: kit-wide skill evaluation"
depends_on: []
touched_files:
  - docs/spec/code-review.md
  - docs/spec/code-review.verification.md
created: 2026-07-25
---

## Problem

Every skill in this kit was blessed on a single real use. That proves each works once and leaves
whole branches unexercised. [`ROADMAP.md`](../../ROADMAP.md) Epic A item 8 names the three that have
never fired on real work:

1. [`verifier-agent`](../../.agents/skills/verifier-agent/SKILL.md)'s `blocked` verdict;
2. [`test-author`](../../.agents/skills/test-author/SKILL.md)'s characterization mode;
3. [`spec-plan-readiness`](../../.agents/skills/spec-plan-readiness/SKILL.md)'s blocking paths.

`blocked` is the most important of the three, because it is the branch that protects the kit's
honesty. `verifier-agent`'s own body says collapsing `blocked` into `pass` or `fail` is "the most
damaging thing this skill can do, because it turns an absent verification into a confident one." A
branch carrying that much weight and zero real exercise is the kit's largest unmeasured risk.

There is also a second, quieter gap: 4 of 19 skills have a specification, and none has behavioral
tests. The kit built a spec-to-verify spine and has pointed it at four of its own nineteen skills.

This task closes a slice of both at once, because the natural way to produce a genuinely unapproved
contract is to write a contract the kit actually wants.

## Scope

**In scope**, in this order:

1. Use [`spec-author`](../../.agents/skills/spec-author/SKILL.md) to draft `docs/spec/code-review.md`
   from the existing shipped skill, self-checked to `ready` with the `spec-quality` lens, written
   with `status: draft`. This is a spec the kit wants regardless: `code-review` is shipped,
   load-bearing, composes a swappable lens, and has no contract.
2. Run `verifier-agent` against the `code-review` implementation **while that spec is still
   `status: draft`**. It must return `verdict: blocked` with a blocking reason naming the unapproved
   contract, and must not report a pass or fail for the work itself.
3. Record that run as `docs/spec/code-review.verification.md`, and use it to settle what an
   evaluation record contains: which branch was exercised, what triggered it, the verdict, and the
   evidence. This is the format the two remaining branches will reuse.

**Out of scope:** exercising `test-author`'s characterization mode or `spec-plan-readiness`'s
blocking paths. Those follow once this format exists and are deliberately left at roadmap altitude
until then. Approving the spec (only a human sets `status: approved`). Editing
`.agents/skills/code-review/SKILL.md` or any other skill: `verifier-agent` never edits what it
verifies, and a spec drafted from an implementation must not quietly reshape that implementation.
Writing tests.

## Implementation notes

- **The point is that the blocked case is real, not staged.** Do not construct a fixture spec to
  trigger `blocked`. The spec must be one the kit genuinely wants, drafted properly, that happens to
  be unapproved at the moment verification runs, because that is exactly the situation the branch
  exists to catch. A staged trigger would prove the branch runs, not that it fires when it should.
- Draft the spec from the shipped skill's actual behavior, not from what it arguably should do. This
  is a characterization spec: it records the contract as built. Where the skill is ambiguous, that
  ambiguity is a finding for Open Questions, not something to resolve by inventing behavior.
- `code-review` is report-only and has two modes (explicit path scope, and change review against the
  merge base with a working-tree fallback). Both belong in the scenarios, as does the
  validate-before-reporting rule it inherits from
  [`review-quality`](../../.agents/rules/review-quality.md).
- After the `blocked` run is recorded, **stop**. Do not approve the spec and re-run. The second run
  against an approved contract is worth doing but is the human's call and a separate task.
- The evaluation record is the durable output here. Keep it short enough that repeating it for the
  other two branches is cheap; if the format takes more effort than the exercise, it is wrong.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py && python .tasks/validate.py --strict

- [x] `docs/spec/code-review.md` exists with `status: draft`, and the sections Problem, Goals,
      Non-Goals, Constraints, Scenarios, Proposed Surface, Open Questions in that order.
- [x] Every scenario carries a stable `S-NNN` id, and the `spec-quality` self-check returns `ready`.
- [x] Both `code-review` modes and the report-only rule appear in at least one scenario each.
- [x] `docs/spec/code-review.verification.md` records `verdict: blocked` with a blocking reason
      naming the unapproved contract, and reports no pass or fail for the implementation.
- [x] The verification record states which branch was exercised and what triggered it.
- [x] `.agents/skills/code-review/SKILL.md` is byte-for-byte unchanged.
- [x] No spec anywhere gains `status: approved` as part of this task.
- [x] `python scripts/validate-skills.py` exits 0 with 19 skills and no new warnings.
- [x] `python .tasks/validate.py --strict` exits 0.
- [x] `python -m unittest discover -s tests -p "test_*.py"` exits 0, unaffected.
- [x] Every relative markdown link added resolves; no em-dashes; headings sentence case.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in the `AGENTS.md` conventions section followed.
- [x] Report to the user: the scenario count, the blocked verdict and its reason, and an honest
      assessment of whether the `blocked` branch behaved as its spec (`S-005`) describes.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.

## Outcome (2026-07-27)

The `blocked` branch fired on a real trigger and behaved exactly as `verifier-agent`'s S-005
describes: `verdict: blocked`, a blocking reason naming the unapproved contract, no command executed,
and no pass or fail reported for the implementation. `code-review/SKILL.md` is byte-for-byte
unchanged, confirmed by object hash against `HEAD`.

Eleven scenarios in the new `code-review` contract. `spec-quality` caught one coverage gap before the
draft was finished: S-011 (a structured findings channel) traced to no goal, so a sixth goal now
covers harness portability. That is the third consecutive spec where the lens caught a scenario with
no goal, after `validate-skills` S-015 and `build-adapters` S-013, and in all three the orphan was an
invocation or channel concern rather than a core behavior. Worth watching for on the next spec.

Two findings, both recorded rather than resolved:

- **Both blocked preconditions were true at once.** `code-review` also has no declared verification
  command, so S-006's trigger held alongside S-005's. The skill's Step 1 reads as short-circuit while
  its `blocking_reasons` list reads as accumulation, and the contract never says which is intended.
  Filed as `chore-0014`.
- **"Exercising a branch" of a prose skill is weaker than exercising a branch of a program**, and the
  evaluation format now says so explicitly. This record is evidence that the procedure, followed
  faithfully against a real trigger, produces the specified outcome. It is not evidence that anything
  enforces it, because nothing does.

The evaluation-record format is settled and documented in the record itself: frontmatter naming the
branch exercised, why the trigger is real, the skill's own output format verbatim, a clause-by-clause
check against the scenario, and observations. One page. The two remaining branches reuse it.
