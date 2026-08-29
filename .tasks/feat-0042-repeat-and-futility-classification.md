---
id: feat-0042
title: Add repeat detection and futility classification so a review-fix loop cannot spin
type: feat
status: open
priority: P2
parent: "ROADMAP Epic B #17: repeat detection and futility classification"
depends_on: [feat-0040, feat-0061]
touched_files:
  - .agents/skills/fix-batch/SKILL.md
  - .agents/skills/house-review/SKILL.md
  - .agents/rules/review-quality.md
created: 2026-08-05
---

## Problem

The kit has no answer to a loop that will not converge. If a reviewer keeps reporting the same
finding and an implementing agent keeps failing to satisfy it, nothing notices, nothing counts, and
nothing decides. The pair simply continues until a human interrupts or a context window ends. This
has not bitten yet because review here is single-pass and batches are small, and it will bite the
first time `fix-batch` runs a review-fix cycle unattended.

Three outcomes are conflated today, and they need different responses:

- the finding is wrong (a false positive, and the reviewer should drop it);
- the finding is right and the fix is aimed at the wrong place (a core issue, and the work should be
  re-scoped rather than retried);
- the finding is right and cannot be resolved within this task's scope (futility, and it should be
  deferred as its own task rather than blocking).

Balarama Bosch's [repoprompt-workflows](https://github.com/moonray/repoprompt-workflows) (MIT)
handles this in its Loop workflow with a counted trigger and a forced classification: after two
failed fix attempts, or three observations sharing a stable finding signature, the orchestrator must
classify the finding as `false_positive`, `core_issue`, or `futility`, and a finding that exhausts
its classification budget is deferred rather than retried. The counting is what makes it work, and
counting requires the stable signature that `feat-0040` introduces.

## Scope

**In scope:**

- Define the repeat trigger in terms of the stable signature from `feat-0040`: N failed fix attempts
  on the same signature, or M observations of it. Pick the thresholds deliberately and state the
  reasoning; upstream's 2 and 3 are a starting point, not a finding.
- Consume the three verdicts the `systematic-debugging` contract defines, and define the required
  response to each. Do not introduce a second vocabulary; see the decisions section.
- State where the classification is recorded, and make it reference `feat-0037`'s decision log
  rather than inventing a second place for an agent to write down why it gave up.
- Wire the trigger into `fix-batch`'s review-fix path and into `house-review`'s reporting, so a
  repeat is visible on both sides of the loop.
- Define the deferral path: a futile finding becomes a task file, not a silent drop.

**Out of scope:**

- Any budget, token ceiling, or wall-clock limit. Upstream keys durable budgets to a persistent
  ledger this kit does not have, and a count of repeats is a better signal than a count of tokens
  for this specific failure.
- A persistent cross-run ledger. Counting within one `fix-batch` run is enough to stop a spin;
  counting across runs needs storage the kit has not designed and should not design speculatively.
- Automatic re-scoping or automatic task creation. The classification decides; a human or a
  subsequent `new-task` run acts.

## Decisions

- **2026-08-18, author: the classification vocabulary is owned by `systematic-debugging`, and this
  task consumes it.** Retargeted after the 2026-08-18 review pass, which found that this task was
  about to define `false_positive`, `core_issue` and `futility` while a diagnosis contract was being
  drafted with three verdicts drawing the same distinction. The correspondence is exact enough to make
  two sets a translation layer rather than a distinction: `false_positive` is `not_reproducible`
  reached from the reviewing side, `core_issue` is `root_cause_found`, and `futility` is
  `architectural` triggered by a repeat count rather than a hypothesis count. Naming is now settled in
  [`systematic-debugging.md`](../docs/spec/systematic-debugging.md); the counted trigger, the
  thresholds, and the deferral path remain this task's own work and are unaffected.
- **Consequence for sequencing.** This task should not be dispatched until that contract is
  `approved`, because implementing against a `draft` is what `new-task` and `verifier-agent` both
  refuse. It is not recorded as a `depends_on` because the implementing task does not exist yet.

## Implementation notes

This task is genuinely blocked on `feat-0040`, not merely sequenced after it. Without a stable
signature there is nothing to count, and counting by prose similarity would be a worse mechanism
than the human interrupt it replaces.

Resist making the thresholds configurable. A knob here means every adopter has to have an opinion
about a number they cannot calibrate, and the failure this prevents is rare enough that a fixed,
documented default is more useful than a setting.

The honest framing for the closeout is that this is preventive. Unlike `feat-0040` and `feat-0041`,
which both fix an observed failure, this one fixes a predicted one. Say so, and state the kill
criterion: if no batch trips the trigger in the first several real runs, the mechanism is carrying
cost for nothing and should be reconsidered rather than kept by default.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py && python .tasks/validate.py --strict && python -m unittest discover -s tests -p "test_*.py" -v

- [ ] The repeat trigger is stated with explicit thresholds and the reasoning for those numbers.
- [ ] Each of the three verdicts named in the `systematic-debugging` contract has a required response
      defined here, and no fourth classification name is introduced anywhere in the change.
- [ ] The futility path produces a task file rather than a silent drop.
- [ ] `fix-batch` and `house-review` both reference the trigger, and neither restates the other's
      definition of it.
- [ ] A stated kill criterion is recorded, per the contribution bar in AGENTS.md.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
