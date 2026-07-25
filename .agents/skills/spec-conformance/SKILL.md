---
name: spec-conformance
description: Use when closing a spec-driven feature or issue, or auditing whether an implementation actually matches its spec. Given a spec path, emits a section-by-section conformance matrix mapping every scenario and proposed surface element to conformed (with file:line or test evidence), diverged (what, why, and both sides), or not-built, plus an audited/unreconciled coverage proof. This is the spec-vs-implementation audit, distinct from spec-quality (spec well-formedness) and doc-sync (doc-vs-code drift), and it is independent of test pass/fail.
---

# Spec conformance

Adapted from repoprompt-workflows (Balarama Bosch), MIT.

## Intent

Prove the implementation conforms to the spec, section by section. Green tests are not proof: they assert code contracts (an element exists, an endpoint returns 200), not that behavior matches the spec's requirements. This skill is the audit that closes that gap and produces the artifact the closeout gate requires. It is the report-only half of the kit's independent verification, meant to compose into the existing verification pass of the [`fix-batch`](../fix-batch/SKILL.md) skill rather than duplicate or replace it. See also [`verifier-agent`](../verifier-agent/SKILL.md), a kit skill that composes this lens with others.

## When to use

- Before closing a spec-driven issue or feature (the closeout gate requires the matrix).
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
- Do not judge spec well-formedness (`spec-quality`) or doc drift (`doc-sync`).
- Do not write tests; do flag where a spec invariant lacks a covering test.
