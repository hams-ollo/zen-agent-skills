---
id: feat-0015
title: Fold the test-quality lens into the kit (port and adapt)
type: feat
status: done
priority: P1
parent: "ROADMAP Epic B #4: test-quality"
depends_on: []
touched_files:
  - .agents/skills/test-quality/SKILL.md
created: 2026-07-24
---

## Problem

ROADMAP Epic B item 4 is `test-quality`: a reusable test-quality lens for choosing the lowest
faithful test layer, naming the plausible defect each test protects, testing the real bug
population, asserting meaningful observable outcomes, and handling fixtures, mocks, diagnostics,
and trust boundaries deliberately. A finished, standalone source exists in the vendored upstream
at
[`repoprompt-workflows-main/.agents/skills/test-quality/SKILL.md`](../repoprompt-workflows-main/.agents/skills/test-quality/SKILL.md)
(moonray's RepoPrompt Workflows, MIT, by Balarama Bosch). It is a report-only lens with no
harness-specific machinery. It is not yet a first-class kit skill.

## Scope

**In scope:** create `.agents/skills/test-quality/SKILL.md` by porting the upstream source and
adapting it to the kit:

1. Adapt to house style ([`.agents/rules/house-style.md`](../.agents/rules/house-style.md)):
   remove every em-dash, convert Title-Case headings to sentence case, keep sources named, use
   relative markdown links. The source also contains a few curly quotation marks and en-dash-like
   glyphs; normalize those too.
2. Keep `name: test-quality` matching the directory; keep the `description` concise and distinct
   from `code-review`/`review-quality` by role word ("chooses test layer and oracle").
3. Add a clickable cross-link noting that `test-author` (a planned kit skill) composes this lens.
4. Add the one-line provenance note: "Adapted from repoprompt-workflows (Balarama Bosch), MIT."
5. Preserve the skill's logic, layer taxonomy, and checklists verbatim except the edits above.

**Out of scope:** blessing the skill; editing `ROADMAP.md`, `docs/CATALOG.md`, or `NOTICE`
(orchestrator handles these once post-reconciliation); porting the other Phase-1 lenses;
authoring `test-author`; changing anything under `repoprompt-workflows-main/`.

## Implementation notes

- Language- and harness-agnostic already; no portability section needed.
- Keep the body under the 500-line guideline (source is ~154 lines).
- Watch for the smart-quote characters in the "does not crash" / oracle passages; the house
  style implies straight quotes.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [x] `.agents/skills/test-quality/SKILL.md` exists with valid frontmatter (`name` equals the
      directory, non-thin `description`).
- [x] `scripts/validate-skills.py` exits 0 with the new skill present.
- [x] Body contains no em-dashes and all headings are sentence case.
- [x] Body carries the provenance note and a clickable `test-author` cross-link.

## Definition of done

- [x] Acceptance command passes locally.
- [x] Conventions in AGENTS.md section 6 followed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
- [x] Skill left as a draft (orchestrator marks ROADMAP/CATALOG draft post-reconcile), not shipped.
