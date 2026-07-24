---
id: feat-0014
title: Fold the spec-plan-readiness gate into the kit (port and adapt)
type: feat
status: done
priority: P1
parent: "ROADMAP Epic B #3: spec-plan-readiness"
depends_on: []
touched_files:
  - .agents/skills/spec-plan-readiness/SKILL.md
created: 2026-07-24
---

## Problem

ROADMAP Epic B item 3 is `spec-plan-readiness`: a deterministic go/no-go gate that blocks tests,
code, and delegation until an approved spec plus an ordered, repository-grounded plan are both
implementable (scenarios, tasks, validation, risks, rollback notes, task-to-scenario
traceability, and a first safe task all explicit). A finished, standalone source exists in the
vendored upstream at
[`repoprompt-workflows-main/.agents/skills/spec-plan-readiness/SKILL.md`](../repoprompt-workflows-main/.agents/skills/spec-plan-readiness/SKILL.md)
(moonray's RepoPrompt Workflows, MIT, by Balarama Bosch). It is a report-only gate with no
harness-specific machinery. It is not yet a first-class kit skill.

## Scope

**In scope:** create `.agents/skills/spec-plan-readiness/SKILL.md` by porting the upstream source
and adapting it to the kit:

1. Adapt to house style ([`.agents/rules/house-style.md`](../.agents/rules/house-style.md)):
   remove every em-dash, convert Title-Case headings to sentence case, keep sources named, use
   relative markdown links.
2. Keep `name: spec-plan-readiness` matching the directory; keep the `description` concise and
   distinct from `spec-quality` by role word ("gates implementability" vs "well-formedness").
3. Reconcile the upstream "Deep Plan" vocabulary with the kit: the kit's plan artifact is a
   ROADMAP Feature decomposed into `.tasks/` files (AGENTS.md section 3 altitude model), not an
   RPCE Deep Plan. Rephrase so the gate reads against the kit's own spec-plus-tasks shape while
   keeping the portable intent. Cross-link `spec-quality` (the lens it uses as supporting input).
4. Add the one-line provenance note: "Adapted from repoprompt-workflows (Balarama Bosch), MIT."
5. Preserve the skill's logic and output format verbatim except the edits above.

**Out of scope:** blessing the skill; editing `ROADMAP.md`, `docs/CATALOG.md`, or `NOTICE`
(orchestrator handles these once post-reconciliation); porting the other Phase-1 lenses; changing
anything under `repoprompt-workflows-main/`.

## Implementation notes

- Harness-agnostic; no Claude-Code portability section needed. Replace hard `docs/spec/test.md`
  path assumptions with portable "repo test taxonomy when available" phrasing.
- Keep the body under the 500-line guideline (source is ~166 lines).

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [x] `.agents/skills/spec-plan-readiness/SKILL.md` exists with valid frontmatter (`name` equals
      the directory, non-thin `description`).
- [x] `scripts/validate-skills.py` exits 0 with the new skill present.
- [x] Body contains no em-dashes and all headings are sentence case.
- [x] Body carries the provenance note, a `spec-quality` cross-link, and no residual RPCE-only
      "Deep Plan" assumption that contradicts the kit's tasks model.

## Definition of done

- [x] Acceptance command passes locally.
- [x] Conventions in AGENTS.md section 6 followed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
- [x] Skill left as a draft (orchestrator marks ROADMAP/CATALOG draft post-reconcile), not shipped.
