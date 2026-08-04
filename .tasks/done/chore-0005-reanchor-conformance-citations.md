---
id: chore-0005
title: Re-anchor validate-skills conformance citations to durable symbol references
type: chore
status: done
priority: P2
parent: "Kit tooling hardening (surfaced by the verifier-agent dogfood, feat-0019)"
depends_on: []
touched_files:
  - docs/spec/validate-skills.conformance.md
created: 2026-07-24
---

## Problem

The `verifier-agent` dogfood (`feat-0019`, recorded at
[`docs/spec/validate-skills.verification.md`](../../docs/spec/validate-skills.verification.md)) found
that every evidence citation inside `main()` in
[`docs/spec/validate-skills.conformance.md`](../../docs/spec/validate-skills.conformance.md) is off by
+8 lines. The `chore-0003` refactor inserted the `skills_dir` parameter, the missing-directory
guard, and the `_rel` helper above that code, shifting everything below. The classifications are all
still correct; only the pointers rotted. The `parse_frontmatter` citations are unaffected, since that
function did not move.

This is a live defect in a contract artifact: a reader following `validate-skills.py:64-65` for the
"no SKILL.md" branch lands on `skills = sorted(...)` instead. It also makes the audit look
authoritative while being unverifiable, which is worse than an audit that is obviously stale.

## Scope

**In scope:** re-anchor every citation in the conformance matrix to a durable reference.
[`spec-conformance`](../../.agents/skills/spec-conformance/SKILL.md) already permits `file:symbol`
evidence, which does not drift when unrelated code is inserted above it. Use the enclosing function
plus the distinguishing branch or expression, so a reader can locate the evidence by searching rather
than by counting lines. Record in the document that the citations were re-anchored and why.

**Out of scope:** changing any classification, status, or disposition in the matrix (the audit's
findings stand, including the S-008 accepted-with-reason divergence); re-running the full
`spec-conformance` audit; editing `scripts/validate-skills.py`, the tests, or the spec; rewriting
[`docs/spec/validate-skills.verification.md`](../../docs/spec/validate-skills.verification.md), which is
the dated record of a run and correctly reports the drift as it stood.

## Implementation notes

- Line numbers are the fragile part, not the evidence itself. Prefer `main() / <branch>` or
  `parse_frontmatter() / <expression>` over `file:NN-NN`.
- The verification report already states the durable-citation recommendation; this task acts on it.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [x] No citation in `docs/spec/validate-skills.conformance.md` uses a bare `file:NN` or `file:NN-NN`
      line reference.
- [x] Every cited symbol or branch exists in `scripts/validate-skills.py` and contains what the
      matrix says it does.
- [x] Every `Status` value in the matrix is unchanged from before this task.
- [x] The S-008 unreconciled item and its accepted-with-reason disposition are unchanged.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md section 6 followed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
