---
id: chore-0010
title: Have spec-plan-readiness compose test-quality's layer taxonomy instead of restating it
type: chore
status: open
priority: P2
parent: "ROADMAP Kit hardening (2026-07-25 review pass)"
depends_on: [bug-0002]
touched_files:
  - .agents/skills/spec-plan-readiness/SKILL.md
created: 2026-07-25
---

## Problem

[`spec-plan-readiness/SKILL.md:105-117`](../.agents/skills/spec-plan-readiness/SKILL.md) (workflow
step 6, "Build the scenario-to-test map") restates the test-layer taxonomy inline:

> `unit/core` for pure logic, parsing, normalization, policy decisions, reducers, and state machines;
> `component/service` for public service behavior with controlled dependencies;
> `filesystem/database/wire-format integration` for persistence, schemas, migrations, file layout,
> query behavior, or wire compatibility; `provider/adapter/entrypoint` for command/tool/API argument
> conversion, routing, serialization, protocol behavior, UI event wiring, or adapter behavior;
> `end-to-end/smoke` only for critical user journeys or diagnostics.

[`test-quality/SKILL.md:49-74`](../.agents/skills/test-quality/SKILL.md) is the swappable lens that
owns this taxonomy, and its `Layer selection` section carries the same list plus a sixth layer
(`Raw real-shape fixtures`) that `spec-plan-readiness` silently drops.

The step even says "and any project `test-quality` guidance", so it knows the lens exists and
restates it anyway. Two copies of the same taxonomy will drift, and one has already fallen a layer
behind. This is the exact failure the kit's compose-by-reference rule prevents elsewhere:
`test-author` composes `test-quality` without restating it, `verifier-agent` composes
`spec-conformance`, `doc-sync` composes `doc-revise`.

The lens is also **swappable**. An adopter who retunes `test-quality` for their stack gets a
`spec-plan-readiness` that silently disagrees with it.

## Scope

**In scope:** replace the inline taxonomy in step 6 with a reference to
[`test-quality`](../.agents/skills/test-quality/SKILL.md)'s `Layer selection` section, preserving what
step 6 uniquely requires: that a layer plus a reason is recorded per scenario, that the lowest
faithful layer is preferred, and that the repo's own test taxonomy wins when one exists.

**Out of scope:** changing [`test-quality`](../.agents/skills/test-quality/SKILL.md). Changing
`spec-plan-readiness`'s `Output format`, its `Readiness checklist`, or any other workflow step, except
checklist item 11, which references the same taxonomy and should stay consistent with the rewritten
step 6. Adding a `## Conventions` section, which is a separate open decision on the roadmap.

## Implementation notes

- The folded-in lens skills (`spec-quality`, `spec-plan-readiness`, `test-quality`, `spec-conformance`)
  came from `repoprompt-workflows` (Balarama Bosch, MIT) where they were standalone and could not
  reference each other. In this kit they can, which is the point of the fold-in. Keep the provenance
  line at the top of the file unchanged.
- `spec-plan-readiness` already composes a sibling by reference at line 10, where it links
  `spec-quality` as supporting input in a single sentence. Mirror that idiom rather than inventing a
  new one.
- Step 6's genuinely local content is the *contract* it enforces: every mapped scenario gets a
  recommended layer and a reason, and an empty `scenario_to_test_map` when readiness was already
  blocked. That must survive. The taxonomy itself is the lens's.
- Checklist item 11 currently reads "Scenario test layers are selected from the repo's test taxonomy
  when available, plus any project `test-quality` guidance." Keep it consistent with the rewrite; it
  may need no change.
- **Depends on `bug-0002`**, which also edits `spec-plan-readiness/SKILL.md` (its line 18
  `AGENTS.md` section reference). Do not dispatch these two to parallel worktrees.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [ ] Step 6 no longer enumerates the layer taxonomy inline.
- [ ] Step 6 links to `test-quality`'s `Layer selection` section with a working relative link.
- [ ] Step 6 still requires a recommended layer plus a reason per mapped scenario, still prefers the
      lowest faithful layer, and still defers to the repo's own taxonomy when one exists.
- [ ] The `Output format` block and the `Readiness checklist` are unchanged except for any wording
      needed to keep item 11 consistent.
- [ ] The provenance line crediting `repoprompt-workflows` is unchanged.
- [ ] `python scripts/validate-skills.py` exits 0 with 19 skills and no new warnings.
- [ ] `python .tasks/validate.py --strict` exits 0.
- [ ] `python -m unittest discover -s tests -p "test_*.py"` exits 0.
- [ ] No em-dashes; headings sentence case.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in the `AGENTS.md` conventions section followed.
- [ ] `bug-0002` confirmed in `.tasks/done/` before starting.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
