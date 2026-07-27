---
id: chore-0015
title: State the build-adapters shared-asset overwrite asymmetry in its contract
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A: distribution tooling"
depends_on: []
spec: docs/spec/build-adapters.md
scenarios: [S-014]
touched_files:
  - docs/spec/build-adapters.md
  - docs/spec/build-adapters.conformance.md
  - scripts/build-adapters.py
created: 2026-07-27
---

## Problem

[`scripts/build-adapters.py`](../scripts/build-adapters.py) emits two kinds of shared material and
guards them differently, and only one of the two guards is in the contract.

The rules loop skips a destination that already exists, so an adopter who edits
`.agents/rules/house-style.md` keeps their version across regenerations. That is `S-010`. The
skill-asset loop has no such guard, so an adopter who edits an emitted template such as
`.agents/skills/project-bootstrap/templates/ruff.toml` loses it silently on the next run. Confirmed
by execution during the `feat-0026` audit: after editing both and re-running, the rules file kept its
content and the skill template was replaced.

The asymmetry is defensible and probably intended, since a skill's templates are derived from the kit
while the rules module belongs to the adopter. It is also invisible: nothing in the spec, the tests,
or the emitted output says the two are treated differently, so a reader of any one of them would
guess wrong.

## Scope

**In scope:** state the intended behavior in [`docs/spec/build-adapters.md`](../docs/spec/build-adapters.md),
then regenerate [`build-adapters.conformance.md`](../docs/spec/build-adapters.conformance.md) so the
"behavior found outside the contract" section can be retired.

Decide first which behavior is intended, since the wording follows from it:

- **Keep the asymmetry** (likely): add a scenario asserting that skill assets are refreshed while
  rules files are preserved, plus a Constraint explaining why the two differ. No code changes.
- **Make them symmetric**: guard the skill-asset loop the same way, so nothing an adopter edited is
  ever replaced. One line in `scripts/build-adapters.py`, plus a scenario.

**Out of scope:** any other adapter behavior. Changing the rules-module guard, which `S-010` already
specifies and which is not in question.

## Implementation notes

- The spec is `status: approved`, so this follows the `chore-0013` procedure: reopen to `draft`,
  amend, self-check with `spec-quality`, a **human** sets `approved`, then regenerate the matrix.
- If the asymmetry is kept, the scenario needs both halves in one place, since the point is the
  contrast. A scenario that only asserts the skill-asset half would leave the same gap in a new form.
- `tests/test_build_adapters.py` already covers the rules half (`test_an_existing_rules_file_is_not_clobbered`).
  Whichever way this goes, the skill-asset half needs its own test, because it currently has none.

## Risks and rollback

Required: this touches more than one module (the contract under `docs/spec/`, and
`scripts/build-adapters.py` if the symmetric option is chosen).

- **If the asymmetry is kept**, the change is documentation only and reverts with one commit.
- **If the loops are made symmetric**, the risk is the opposite of the current defect: a skill template
  that legitimately changed in the kit would stop reaching a project that already has an older copy,
  turning a silent overwrite into a silent staleness. Mitigate by saying so in the emitted summary,
  the way the rules-module skip already is. Reverts with one commit.
- **Either way the conformance matrix is regenerated**, so a bad amendment shows up as a diff in
  `build-adapters.conformance.md` rather than as a silent change of meaning.

Added 2026-07-27 by `chore-0016`, applying the `required_resolution` the readiness gate recorded for
this task's `source: plan` gap. The `source: spec` and `source: both` gaps remain, so this task is
still blocked.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py && python -m unittest discover -s tests -p "test_*.py"

- [ ] `docs/spec/build-adapters.md` states how each shared-asset kind is treated on a re-run.
- [ ] `spec-quality` returns `ready`, and a human set `status: approved`.
- [ ] A test covers the skill-asset half, whichever behavior was chosen.
- [ ] `build-adapters.conformance.md` is regenerated and its "behavior found outside the contract"
      section is retired.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
