---
id: feat-0018
title: Draft the test-author skill (composes test-quality, from its own spec)
type: feat
status: done
priority: P1
parent: "ROADMAP Epic B #5: test-author"
depends_on: []
touched_files:
  - .agents/skills/test-author/SKILL.md
created: 2026-07-24
---

## Problem

ROADMAP Epic B item 5 is `test-author`: derive focused acceptance tests from an approved spec and a
task's acceptance criteria, retaining characterization-test support for legacy code with no coverage,
composing the blessed [`test-quality`](../../.agents/skills/test-quality/SKILL.md) lens, and running
between implementation and reconciliation so test evidence is part of the spine. The behavioral
contract is already written and passes `spec-quality` at [`docs/spec/test-author.md`](../../docs/spec/test-author.md)
(drafted by the `spec-author` dogfood). The discipline exists upstream only inside the RPCE Test
workflow (gitignored `repoprompt-workflows-main/.agents/workflows/Test.md`), so it must be extracted
into a portable `SKILL.md`, not folded in. `test-author` is the only spine skill that actually writes
tests: `test-quality` judges test design, `spec-conformance` audits code against a spec, and
`fix-batch` runs tests, but none author them.

## Scope

**In scope:** author `.agents/skills/test-author/SKILL.md`, harness-agnostic, delivering scenarios
S-001 through S-005 of the spec: read an approved spec and gate it with `spec-quality` (do not
generate tests from a `needs_revision` spec); discover and match the repository's existing test
framework, layout, naming, and assertion style rather than inventing one; map each scenario to at
least one test tagged with its `S-NNN` id, choosing the lowest faithful layer and an exact-outcome
oracle by composing `test-quality`; support acceptance and characterization modes (inferred from
whether a spec is present, with user override); for a bug fix, prove the regression fails against the
pre-fix behavior first; report gaps rather than writing low-value passing tests; emit a coverage
report of scenarios covered and omitted with reasons; never modify production code to make a test
pass. Cross-link `test-quality`, `spec-quality`, `spec-conformance`, and `fix-batch`. Mark it a draft
in `ROADMAP.md`/`docs/CATALOG.md`.

**Out of scope:** blessing the skill (waits for a real dogfood, deriving the `validate-skills.py`
acceptance tests from `docs/spec/validate-skills.md`, which is `chore-0003`); implementing the tests
themselves; building the `verifier-agent`; changing `test-quality`, `spec-quality`, or the spec file.

## Implementation notes

- Extract the durable discipline from the upstream Test workflow; drop RPCE-only tool names
  (`get_file_tree`, `file_search`) and the reproduced per-language framework code blocks. Keep a
  short language-agnostic "discover and match the repo" instruction instead, so the body stays under
  the 500-line guideline.
- Compose both lenses by reference: `spec-quality` gates the input spec, `test-quality` governs layer
  and oracle choice. Do not restate either lens's rules inline.
- Mirror the spec's Constraints exactly (mode inference and override, characterization labeling,
  no new framework, scenario-id traceability, position in the spine). Follow
  [`.agents/rules/house-style.md`](../../.agents/rules/house-style.md).

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [x] `.agents/skills/test-author/SKILL.md` exists with valid frontmatter (`name` equals the
      directory, non-thin `description`).
- [x] `scripts/validate-skills.py` exits 0 with the new skill present.
- [x] Body composes `test-quality` and `spec-quality` by reference (no inline restatement) and
      cross-links `spec-conformance` and `fix-batch`.
- [x] Body states the discover-and-match rule, both modes, the bug-fix fails-first rule, the
      report-gaps-not-fake-tests rule, and the never-edit-production-code rule.

## Definition of done

- [x] Acceptance command passes locally.
- [x] Conventions in AGENTS.md section 6 followed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
- [x] Skill left as a draft; ROADMAP/CATALOG mark it draft (pending dogfood), not shipped.
