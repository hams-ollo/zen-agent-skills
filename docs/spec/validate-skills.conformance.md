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
| Scenarios | S-001 directory without SKILL.md | Conformed | `main()` / `not skill_md.is_file()` branch | `errors.append(f"{rel}: no SKILL.md")`, then `continue` |
| Scenarios | S-002 no frontmatter | Conformed | `main()` / `fm is None` branch, with `parse_frontmatter()` / both `return None, 0` paths | `parse_frontmatter` returns `None` when the first line is not `---` or no closing `---` is found; `main` then records the error |
| Scenarios | S-003 name != directory | Conformed | `main()` / `elif name != d.name` branch | `errors.append(... name {name!r} != directory {d.name!r})` |
| Scenarios | S-004 missing name or description | Conformed | `main()` / `if not name` and `if not desc` branches | separate error branches for each missing key |
| Scenarios | S-005 thin description warns, does not fail | Conformed | `main()` / `elif len(desc) < MIN_DESC_CHARS` branch, with the `return 1 if errors else 0` exit | appends to `warnings`, never `errors`, so the exit stays 0 |
| Scenarios | S-006 oversized body warns, does not fail | Conformed | `main()` / `if body_lines > MAX_BODY_LINES` branch, with the `return 1 if errors else 0` exit | body-line warning, no error |
| Scenarios | S-007 all valid | Conformed | `main()` / the `Checked {len(skills)} skill(s)` summary print and `return 1 if errors else 0` | prints the summary and returns 0 |
| Scenarios | S-008 description states what and when | Diverged | spec: `validate-skills.md` S-008; code: `main()` / `elif len(desc) < MIN_DESC_CHARS` branch | spec requires flagging descriptions that do not state both what and when; code only checks `len(desc) < MIN_DESC_CHARS` (a length proxy the module docstring itself calls "a rough proxy"). A description over that length saying neither still passes. |
| Proposed Surface | Invocation `python scripts/validate-skills.py` | Conformed | module `__main__` guard | `if __name__ == "__main__": raise SystemExit(main())` |
| Proposed Surface | Exit non-zero on error only | Conformed | `main()` / final `return 1 if errors else 0` | warnings do not affect the exit code |
| Proposed Surface | Summary output format | Conformed | `main()` / the `WARN`/`ERROR` print loops and the `Checked ...` summary print | per-issue lines first, then the summary |

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

## Citation maintenance

Citations were re-anchored on 2026-07-24 (`chore-0005`) from line references to symbol and branch
references. The original audit cited line numbers, and the `chore-0003` refactor later inserted the
`skills_dir` parameter, the missing-directory guard, and the `_rel` helper above the audited code,
shifting every citation inside `main()` by eight lines while leaving the classifications correct. The
`verifier-agent` dogfood caught the drift ([`validate-skills.verification.md`](validate-skills.verification.md)).

No status, evidence meaning, or disposition changed in that re-anchoring: the audit's findings stand
exactly as first recorded. Symbol and branch references were chosen because they survive unrelated
edits above them, which bare line numbers do not.
