---
title: validate-skills conformance
spec: docs/spec/validate-skills.md
audited: 2026-07-24
---

# validate-skills conformance matrix

Spec-vs-implementation audit of [`scripts/validate-skills.py`](../../scripts/validate-skills.py)
against [`validate-skills.md`](validate-skills.md). Produced as the first in-kit dogfood of the
`spec-conformance` lens. Evidence is by code location; this audit is independent of test pass/fail.

## Matrix

| Section | Item | Status | Evidence | Note |
|---|---|---|---|---|
| Scenarios | S-001 directory without SKILL.md | Conformed | `validate-skills.py:64-65` | `if not skill_md.is_file(): errors.append(... no SKILL.md)` |
| Scenarios | S-002 no frontmatter | Conformed | `validate-skills.py:67-69` with `parse_frontmatter:26,33-34` | returns `None` when first line is not `---` or no closing `---`, then error |
| Scenarios | S-003 name != directory | Conformed | `validate-skills.py:75-76` | `elif name != d.name: errors.append(...)` |
| Scenarios | S-004 missing name or description | Conformed | `validate-skills.py:73-74,77-78` | separate error branches for each missing key |
| Scenarios | S-005 thin description warns, does not fail | Conformed | `validate-skills.py:79-81` + exit `:93` | appends to `warnings`; `return 1 if errors else 0` keeps exit 0 |
| Scenarios | S-006 oversized body warns, does not fail | Conformed | `validate-skills.py:82-84` + exit `:93` | body-line warning, no error |
| Scenarios | S-007 all valid | Conformed | `validate-skills.py:91-93` | prints `Checked N skill(s)...` and returns 0 |
| Scenarios | S-008 description states what and when | Diverged | spec: `validate-skills.md` S-008; code: `validate-skills.py:79-81` | spec requires flagging descriptions that do not state both what and when; code only checks `len(desc) < 40` (a length proxy the docstring at `:6` itself calls "a rough proxy"). A description over 40 chars that says neither passes. |
| Proposed Surface | Invocation `python scripts/validate-skills.py` | Conformed | `validate-skills.py:96-97` | `if __name__ == "__main__": raise SystemExit(main())` |
| Proposed Surface | Exit non-zero on error only | Conformed | `validate-skills.py:93` | `return 1 if errors else 0` |
| Proposed Surface | Summary output format | Conformed | `validate-skills.py:87-92` | `WARN`/`ERROR` lines then the `Checked ...` summary |

## Coverage proof

- **audited**: S-001, S-002, S-003, S-004, S-005, S-006, S-007, S-008, and all three Proposed
  Surface elements (invocation, exit code, output format). Every spec item was checked.
- **unreconciled**:
  - **S-008 (Diverged)**: disposition **accepted-with-reason**. The "what and when" bar is aspirational
    and a full natural-language check is out of scope for a standard-library structural linter; the
    length proxy is a deliberate, documented approximation. If the kit later wants to enforce it, the
    honest fix is to soften the spec wording to "length proxy" or add a real check, not to claim the
    current code satisfies the stated intent.

No spec item was silently dropped. One item diverges by design and is accepted with a stated reason;
everything else conforms.
