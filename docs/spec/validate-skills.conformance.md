---
title: validate-skills conformance
spec: docs/spec/validate-skills.md
audited: 2026-07-27
supersedes: 2026-07-24 audit (S-001 through S-008 only)
---

# validate-skills conformance matrix

Spec-vs-implementation audit of [`scripts/validate-skills.py`](../../scripts/validate-skills.py)
against [`validate-skills.md`](validate-skills.md). Evidence is by code location; this audit is
independent of test pass/fail.

Regenerated 2026-07-27 (`chore-0013`) against the amended contract. The previous matrix audited
S-001 through S-008 and reported full coverage with one accepted divergence, which was true of what
it checked and misleading about the tool: the contract then described less than half of what the
validator did. Scenarios S-009 through S-016 are audited here for the first time.

Extended 2026-07-28 (`feat-0032`) with S-017 and S-018, audited here for the first time. This is a
partial re-audit rather than a regeneration: the two new rows were audited against the code as it now
stands, and every carried-forward citation was re-checked to still resolve after the
`parse_frontmatter()` change, which touched a function five other rows cite. No carried-forward status
or disposition changed.

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
| Scenarios | S-009 link target does not exist | Conformed | `check_links()` / final `if not resolved.exists()` branch | records the unresolved path; reached only after the external, anchor, sibling and portability branches have passed |
| Scenarios | S-010 dangling sibling-skill reference | Conformed | `check_links()` / `if sibling:` branch, `sibling_name not in skill_names` | a `../<name>/SKILL.md` link is resolved by skill-name membership rather than by path, then `continue`s |
| Scenarios | S-011 link escapes the distributed tree | Conformed | `check_links()` / `not resolved.is_relative_to(portable_root)` branch, with `main()` / `portable_root = skills_dir.parent.resolve()` | the escape branch precedes the existence check, so a link whose target exists in this repository still errors, which is the behavior the scenario requires |
| Scenarios | S-012 link to the rules module is legal | Conformed | `main()` / `portable_root = skills_dir.parent.resolve()`, with `check_links()` / the `is_relative_to` guard | `../../rules/<file>` resolves inside `.agents/`, so it passes the portability guard and is then subject only to the ordinary existence check |
| Scenarios | S-013 external and same-page links not resolved | Conformed | `check_links()` / `EXTERNAL_LINK_PREFIXES` guard and the `if not path_part` anchor guard | both `continue` before any filesystem access |
| Scenarios | S-014 contradictory status claim warns | Conformed | `check_status_contradiction()` with the widened `DRAFT_STATUS_RE` and `SHIPPED_STATUS_RE` | diverged when first audited on 2026-07-27 and was fixed the same day. The patterns now cover assertion forms (`is`/`remains`/`stays` a draft, a `status: draft` line, `draft pending`) and provenance forms (a `shipped`/`blessed` list item, or either word before an ISO date). Re-probed against the five phrasings that produced the original finding: all five flag. Four negative cases produce no finding, including prose that merely discusses drafts and a skill whose `status: draft` refers to a spec it authors rather than to itself. |
| Scenarios | S-015 skills directory does not exist | Conformed | `main()` / `if not skills_dir.is_dir()` guard | prints the missing-directory error and returns 1; confirmed by execution (exit 1, `ERROR no skills directory at ...`) |
| Scenarios | S-016 skills directory exists but is empty | Conformed | `main()` / `if not skills:` guard after `skills_dir.iterdir()` | prints `No skills found under ...` and returns 0; confirmed by execution (exit 0) |
| Scenarios | S-017 description over the harness limit fails | Conformed | `main()` / `elif len(desc) > MAX_DESC_CHARS` branch, with `MAX_DESC_CHARS = 1024` | appends to `errors`, so the run exits non-zero; the message carries both the measured length and the limit. Confirmed by execution against a copy of the real skills tree with one description padded over the bound: exit 1, `description is 1173 chars, over the 1024-char limit`. The boundary is `>`, so a description of exactly 1024 produces no finding |
| Scenarios | S-018 description measured by value, not YAML syntax | Conformed | `parse_frontmatter()` / `BLOCK_SCALAR_RE.sub("", value, count=1)` on the field-line branch | the indicator is stripped at the head of the field line only and once, so `>`, `>-`, `>+`, `\|`, `\|-`, and `\|+` are removed while a plain scalar and any angle bracket inside the prose are untouched. The four block-scalar descriptions in the kit each measure 3 fewer characters than before the fix, which is the defect this closes |
| Scenarios | S-019 unparseable frontmatter fails | Conformed | `check_frontmatter_is_parseable()`, called from `main()` after `check_links()` | errors on a plain unquoted scalar containing `": "` or ending in `":"`, and skips a block scalar or a fully quoted value. Confirmed by execution: a copy of the real `.agents/` tree with `house-review`'s description put back into the single-line plain form that shipped exits 1 with the nested-mapping error. The message states that it checks one known construct rather than YAML validity, which is the honest limit of a standard-library check |
| Scenarios | S-020 angle bracket in a description fails | Conformed | `main()` / the `if desc and ("<" in desc or ">" in desc)` branch | reads the parsed value, so the twelve block-scalar descriptions are not flagged for the `>` in their own indicator. `human-handoff` was violating this in the field and is fixed |
| Scenarios | S-021 unrecognised frontmatter property fails | Conformed | `main()` / the `for key in sorted(set(fm) - ALLOWED_FRONTMATTER_KEYS)` loop, with the `ALLOWED_FRONTMATTER_KEYS` constant | an allow-list of the schema's six properties, commented with its source and the date it was read. `version` is deliberately excluded: the reference implementation rejects it even though Anthropic's own example skill documents it as optional |
| Proposed Surface | Invocation `python scripts/validate-skills.py` | Conformed | module `__main__` guard | `if __name__ == "__main__": raise SystemExit(main())` |
| Proposed Surface | Exit non-zero on error only | Conformed | `main()` / final `return 1 if errors else 0` | warnings do not affect the exit code |
| Proposed Surface | Output format | Conformed | `main()` / the `WARN`/`ERROR` print loops and the `Checked ...` summary print, plus the two early-return prints | per-issue lines then the summary; the missing-directory and no-skills-found lines replace the summary as the amended surface states |

## Coverage proof

- **audited**: S-001 through S-021, and all three Proposed Surface elements (invocation, exit code,
  output format). Every spec item was checked.
- **unreconciled**:
  - **S-008 (Diverged)**: disposition **accepted-with-reason**. The "what and when" bar is aspirational
    and a full natural-language check is out of scope for a standard-library structural linter; the
    length proxy is a deliberate, documented approximation. If the kit later wants to enforce it, the
    honest fix is to soften the spec wording to "length proxy" or add a real check, not to claim the
    current code satisfies the stated intent. Unchanged from the 2026-07-24 audit.

S-014 was the second unreconciled item when this matrix was first regenerated on 2026-07-27, carrying
disposition **fix**. The author chose to widen rather than to narrow the scenario, the patterns were
widened the same day, and the row above is the re-audit. It is recorded here rather than erased
because the divergence is the useful part of the history: the check had shipped on 2026-07-25, was
believed correct for two days, and was only caught when a scenario was written that stated the
condition semantically instead of restating the implementation.

No spec item was silently dropped. One item diverges, accepted with a stated reason; everything else
conforms.

## Test coverage of spec invariants

Flagged per `spec-conformance`'s non-goal (it does not write tests, but does say where an invariant
lacks one). Against [`tests/test_validate_skills.py`](../../tests/test_validate_skills.py):

| Scenario | Covering test | Note |
|---|---|---|
| S-009 through S-013 | present | one test each, plus negative cases for S-010 and S-012, each tagged with its scenario id |
| S-014 | present | table-driven over all five contradiction phrasings and four negative cases. Confirmed to fail on four of the five against the pre-fix patterns, which is the bug population; the canonical phrasing always passed and proves nothing on its own, which is exactly how the original single-case test hid the divergence |
| S-015, S-016 | present | added 2026-07-27 once the contract was approved. Asserts the pair together: the absent directory must fail and must not report `Checked 0 skill`, the empty one must succeed |
| S-017 | present | two tests: over the limit errors with the measured length in the message, and exactly at the limit does not, so an off-by-one that rejected a legal description would fail |
| S-020, S-021 | present | added by `bug-0008`. Five tests: an angle bracket errors, a block-scalar description is not flagged for its own indicator, an unrecognised key (`version`) errors, all six permitted properties together pass, and both rules hold across the real nineteen. The two negative cases are the ones that keep the checks usable: flagging a block scalar would fail twelve valid skills, and rejecting a legal property would fail a valid skill while looking like a kit bug |
| S-019 | present | added by `bug-0007`. Six tests: the two positive constructs (a colon-space inside a plain scalar, and a value ending in a colon), three negative cases that must not fire (a block scalar, a quoted value, and a URL whose colon has no following space), and one that runs the check over all nineteen shipped skills, which is the assertion that would have caught the defect. The negative cases carry the weight: a false positive would push authors to contort a description to satisfy a checker rather than a parser |
| S-018 | present | three tests: a block scalar whose text is exactly at the limit must pass (it measured 3 over before the fix), every indicator form strips at the parser layer, and two negative cases hold, a plain scalar and prose containing angle brackets. The negative cases are the load-bearing ones, because over-eager stripping shortens a description silently instead of failing |

Every scenario except S-008 now has a covering test. S-008 remains deliberately untested, because a
passing test there would assert behavior the accepted divergence says does not exist.

All five S-017 and S-018 tests were confirmed to fail against the pre-fix script before it was changed,
so they test the change rather than restate it. The two positive S-019 tests likewise fail against the
pre-fix script; its three negative cases pass both before and after, which is what a negative case
should do and is why they were not counted as evidence of the change.

**S-019 through S-021 are the scenarios this contract was least able to reach on its own, and it is
worth saying why.** Every other scenario is checkable by reading the script against the spec. These
three were invisible to that method, because the script and the spec agreed with each other and both
disagreed with the schema. Each was found by running an external implementation over the real tree: a
third-party YAML parser for S-019, and Anthropic's reference validator for S-020 and S-021.

The count is the argument. Three defects in one field (`bug-0005`, `bug-0007`, `bug-0008`) shipped
past nineteen skills, four gates, an approved contract, and a clean conformance matrix, over two days.
None was subtle once seen, and none was reachable from inside. Where a tool reimplements an external
standard rather than calling it, conformance to the spec is not evidence of conformance to the
standard, and the only closing move is to run the reference implementation. This matrix is now audited
against both.

The whole set is verified end to end: all nineteen skills pass Anthropic's `quick_validate.py`, 19 of
19, alongside this repository's own validator reporting 0 errors and 0 warnings.

## Citation maintenance

Citations were re-anchored on 2026-07-24 (`chore-0005`) from line references to symbol and branch
references. The original audit cited line numbers, and the `chore-0003` refactor later inserted the
`skills_dir` parameter, the missing-directory guard, and the `_rel` helper above the audited code,
shifting every citation inside `main()` by eight lines while leaving the classifications correct. The
`verifier-agent` dogfood caught the drift ([`validate-skills.verification.md`](validate-skills.verification.md)).

No status, evidence meaning, or disposition changed in that re-anchoring, and the 2026-07-27
regeneration re-verified every S-001 through S-008 citation still resolves before carrying it
forward. Symbol and branch references were chosen because they survive unrelated edits above them,
which bare line numbers do not.
