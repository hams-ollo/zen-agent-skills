---
title: tracker-links conformance
spec: docs/spec/tracker-links.md
audited: 2026-07-28
---

# tracker-links conformance matrix

Spec-vs-implementation audit of the `external` field in
[`.tasks/validate.py`](../../.tasks/validate.py) and the closing-reference procedure in
[`pr-describe`](../../.agents/skills/pr-describe/SKILL.md), against
[`tracker-links.md`](tracker-links.md). Evidence is by code location or by skill-body clause; this
audit is independent of test pass/fail.

The contract spans two surfaces of different kinds, which is unusual here and is the fact that
shapes the matrix: S-007 and S-008 are code and are testable, while S-001 to S-006 and S-009 are
clauses in a prose procedure an agent follows. A prose clause can be audited for presence and
correctness but not executed, so its evidence is the clause plus the run recorded in
[`tracker-links.verification.md`](tracker-links.verification.md).

## Matrix

| Section | Item | Status | Evidence | Note |
|---|---|---|---|---|
| Scenarios | S-001 a linked task produces a closing reference | Conformed | `pr-describe` / "Close the linked issue, when a task names one" | Exercised on PR #2; GitHub resolved and closed issue #1 |
| Scenarios | S-002 several linked tasks each get their own keyword | Conformed | `pr-describe` / the "Repeat the keyword per issue" rule, with the failing example spelled out | Clause present and correct; not exercised, see the verification record |
| Scenarios | S-003 an unlinked task produces no reference | Conformed | `pr-describe` / "Emit nothing when no task names an issue" | Clause present; not exercised |
| Scenarios | S-004 a non-default base links without closing | Conformed | `pr-describe` / the "Only the default branch closes anything" rule | Clause present and states the reason to emit; not exercised |
| Scenarios | S-005 a cross-repository reference is carried through | Conformed | `pr-describe` / "Emit the value verbatim after the keyword", plus `EXTERNAL_RE` accepting `owner/repo#123` | Accepted by the validator and covered by a test; the emission half is not exercised |
| Scenarios | S-006 the reference never appears in the title | Conformed | `pr-describe` / "In the description, never the title" | Exercised on PR #2; the title was queried and is clean |
| Scenarios | S-007 a malformed reference fails validation | Conformed | `.tasks/validate.py` / `EXTERNAL_RE` and the `err(...)` call in the per-file loop | Two tests, both confirmed to fail against a validator with the check removed |
| Scenarios | S-008 an absent reference is valid | Conformed | `.tasks/validate.py` / `fm.get("external", "")` guarding the check | Three tests: absent, `#123`, and `owner/repo#123` |
| Scenarios | S-009 a task completed in the same change still gets a reference | Conformed | `pr-describe` / "A completed task still counts", naming `.tasks/done/` | Clause present; structurally hard to exercise, see the verification record |
| Proposed Surface | `external` field | Conformed | `.tasks/_TEMPLATE.md`, `.tasks/README.md` field table, `.tasks/validate.py` | Documented in both places an author would look |
| Proposed Surface | Reference form | Conformed | `.tasks/validate.py` / `EXTERNAL_RE` | Both forms accepted, bare number rejected |
| Proposed Surface | Keyword `Closes` | Conformed | `pr-describe` / the emission examples | |
| Proposed Surface | Pull request body | Conformed | `pr-describe` / "one per line" | |
| Proposed Surface | Non-default base | Conformed | `pr-describe` / the default-branch rule | |
| Proposed Surface | Validation | Conformed | `.tasks/validate.py` | Error, not warning, per the spec's silent-failure reasoning |

## Coverage proof

- **audited**: S-001 through S-009, and all six Proposed Surface elements. Every spec item was
  checked.
- **unreconciled**: none. No item diverged and none is unbuilt.

## Observations

**"Conformed" carries two different strengths in this matrix, and the distinction matters.** For
S-007 and S-008 it means code was read and tests were run against it. For the prose scenarios it
means the clause exists, says the right thing, and in two cases was observed working. A clause an
agent might still misread is weaker evidence than a passing test, and this matrix does not pretend
otherwise. Five of the seven prose scenarios have never fired on real work.

**The pattern to watch:** if a later run finds an agent following `pr-describe` and getting one of
these wrong anyway, the fix is not a firmer clause but moving that rule into something mechanical.
The nearest candidate would be a check in `validate-skills.py` or a lint over drafted PR bodies. That
is speculative today and should stay on the roadmap until an actual miss is observed.
