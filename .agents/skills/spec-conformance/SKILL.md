---
name: spec-conformance
description: Use when closing a spec-driven feature or issue, or auditing whether an implementation actually matches its spec. Given a spec path, emits a section-by-section conformance matrix mapping every scenario and proposed surface element to conformed (with file:line or test evidence), diverged (what, why, and both sides), or not-built, plus an audited/unreconciled coverage proof. This is the spec-vs-implementation audit, distinct from spec-quality (spec well-formedness) and doc-sync (doc-vs-code drift), and it is independent of test pass/fail.
license: MIT. Adapted from repoprompt-workflows (Balarama Bosch), MIT.
---

# Spec conformance

Adapted from repoprompt-workflows (Balarama Bosch), MIT.

## Intent

Prove the implementation conforms to the spec, section by section. Green tests are not proof: they assert code contracts (an element exists, an endpoint returns 200), not that behavior matches the spec's requirements. This skill is the audit that closes that gap.

It is the report-only half of the kit's independent verification. The matrix it produces is an input, not a verdict: [`verifier-agent`](../verifier-agent/SKILL.md) composes this lens for the contract half of its own `pass` / `fail` / `blocked` decision, and [`fix-batch`](../fix-batch/SKILL.md) runs that verification against every worktree before anything is reconciled. Use this lens directly when the spec-versus-code audit is all you want; go through `verifier-agent` when the question is whether the work is ready to land.

## When to use

- Before closing a spec-driven issue or feature, where the matrix is the evidence that it is done.
- When asked "does the implementation match the spec?" or "what diverges from the spec?"
- To produce a conformance report for a spec, conventionally at `docs/spec/<spec>.conformance.md`.

## Inputs

- **spec path** (required): the spec document to audit.
- **implementation scope** (optional): defaults to the repo or working tree.

## Workflow

1. **Enumerate** every auditable item in the spec: each scenario (`S-NNN`), each proposed surface element (tool, endpoint, parameter, field, or return shape), and each stated value, enum, or constraint.
2. **Locate evidence** for each item in the implementation: a code location (`file:symbol`) or a test that asserts the requirement.
3. **Classify** each item: **Conformed** (evidence matches the requirement) | **Diverged** (evidence conflicts, state both the spec side and the code side) | **Not-built** (no evidence found).
4. **Coverage proof**: emit the `audited` set (every item checked) and the `unreconciled` set (Diverged + Not-built). Each unreconciled item is either to-fix or accepted-with-reason; nothing is silently dropped.

## Output

Write the matrix and the coverage proof, conventionally to `docs/spec/<spec>.conformance.md` (adjust the location to fit repos without a `docs/spec/` convention):

- matrix rows: `{ section, item, status: Conformed|Diverged|Not-built, evidence, note }`
- `audited`: every spec section and item checked
- `unreconciled`: Diverged + Not-built items, each with a disposition (fix | accepted-with-reason)

An empty result is valid only as `{ audited: [...], unreconciled: [] }`, "no divergence" requires positive evidence that the whole spec was checked.

## Non-goals

- Do not fix divergences; report them.
- Do not judge spec well-formedness ([`spec-quality`](../spec-quality/SKILL.md)) or doc drift ([`doc-sync`](../doc-sync/SKILL.md)).
- Do not write tests ([`test-author`](../test-author/SKILL.md)); do flag where a spec invariant lacks a covering test.

## Conventions

Follow the repo's house-style module (in this kit, [`.agents/rules/house-style.md`](../../rules/house-style.md)): sentence-case headings, clickable relative links, named sources, no em-dashes. That file is a swappable default; a downstream adopter may replace it without touching this skill.

When this runs unattended, follow the repo's autonomy module too (in this kit, [`.agents/rules/autonomy.md`](../../rules/autonomy.md)), which consolidates this skill's coverage rule as `A6`: a partial audit is never reported as a whole one, so the audited and unreconciled sets are stated alongside the verdict. That file is a swappable default; a downstream adopter may raise or lower the ceiling without touching this skill.

## Provenance

Adapted from RepoPrompt Workflows by Balarama Bosch (MIT). The digest below is of the retrieved upstream file, not of this adapted one, which differs by design. Re-check it by running `scripts/check-provenance.py` in the Zen Agent Skills repository.

```provenance
source: https://raw.githubusercontent.com/moonray/repoprompt-workflows/main/.agents/skills/spec-conformance/SKILL.md
author: Balarama Bosch
license: MIT
retrieved: 2026-08-06
sha256: f59286923b046553678d7d638574d323a8012d1fe066507496d15e0861552be8
note: backfilled baseline (feat-0043). The snapshot this skill was adapted from is gone, so the digest pins upstream as of the retrieved date, not the exact bytes adapted.
```
