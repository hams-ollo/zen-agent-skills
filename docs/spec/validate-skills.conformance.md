---
title: validate-skills conformance
spec: docs/spec/validate-skills.md
audited: 2026-07-27
supersedes: 2026-07-24 audit (S-001 through S-008 only)
re_audited: 2026-07-28 (feat-0032), 2026-08-19 (chore-0039), 2026-08-20 (chore-0047), 2026-08-20 (bug-0040), 2026-08-21 (chore-0036), 2026-08-21 (chore-0054), 2026-08-22 (chore-0055), 2026-08-27 (chore-0065), 2026-08-27 (chore-0045, partial: the S-022 test-coverage row only)
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

Re-audited 2026-08-19 after `chore-0039` amended the contract with S-022, the code-span and fence
exception `bug-0027` had already given `check_links()` on 2026-08-18. That amendment is likewise
**pending the author's re-approval**, stated in the spec's header and repeated here so this matrix is
not read as auditing an approved contract in full. The five link rows S-009 through S-013 were
re-audited against the current function in the same pass and all five remain `Conformed`: none of
their branches changed, and each is now reached only for a link the span and fence guard let through. This is a partial
re-audit of the rows `bug-0027` moved, not a regeneration; no other row was re-derived.

Extended 2026-08-20 (`chore-0047`) with S-023, the lens-composition rule `feat-0048` added to the
script on 2026-08-19 and this contract did not state.
That amendment is likewise **pending the author's re-approval**.
This is an extension rather than a regeneration: the one new row was audited
against the code as it now stands, and no carried-forward row was re-derived, because
`check_lenses_are_composed()` is called after the per-skill loop and touches no function any other row
cites. S-023 is the first row here whose evidence sits outside `.agents/skills/`, which is why the
Proposed Surface gained a "what it reads" entry and this matrix gained a row for it.

Re-audited 2026-08-20 (`bug-0040`) after the asymmetry the `chore-0047` row recorded was closed:
`check_lenses_are_composed()` now counts a reference only outside a fenced code block. Only the S-023
row and its test row were re-derived; no other row is touched, for the reason the `chore-0047`
paragraph gives, that this rule shares no function with any other. **The fence exclusion did not
extend to inline code spans, and that is a decision rather than an oversight**, argued in
`_names_file_outside_fences()` and pinned by the test named below. S-022 excludes a span for the link
rules because a link inside one is not a link: its brackets render as literal text, so there is
nothing to follow. A filename inside a span is still prose naming the file, which S-023's "what
counts as a reference" paragraph protects explicitly, and backticks are how the house style writes
such a mention. Measured over the same twenty bodies on 2026-08-20: the three lens filenames occur 60
times, 0 of them inside a fence and 27 inside an inline code span. The first number is why this fix is
inert in the kit today; the second is why the span half would not have been, and it lands on a named
skill rather than in the abstract, since `house-review` names `house-style.md` only in the span
"it is swappable like `house-style.md`" and would have been the one body to lose its reference.

Re-audited 2026-08-21 (`chore-0036`), which widened the checked file set from each skill's
`SKILL.md` to the markdown a skill ships beside it, and added a second summary line reporting how
many supporting files were read and how many were skipped. **This contract does not state that rule
at all**, and the task that built it declares `scenarios: []`, so nothing here is audited against a
scenario for it. The pass is recorded the only honest way available: the `Output format` row moves to
`Diverged`, the `What it reads` row keeps its status and gains a note, and the unreconciled section
below carries the amendment that is owed. This is the fourth time the implementation has grown past
this contract (after `feat-0023`, `bug-0027`, and `feat-0048`), and the pattern is worth naming: the
gap is always found at the next task's closeout rather than by any gate. Only those two rows were
re-derived; every other row is carried forward, safe because `check_supporting_files()` and
`classify_supporting_file()` are new functions no other row cites, and the one existing function the
change touched, `check_links()`, kept every branch and every message body (`chore-0036` renamed two
of its parameters and made the `../<name>/SKILL.md` shortcut conditional, which is reached only from
the new caller).

Extended 2026-08-21 (`chore-0054`) with S-024, the supporting-file link rule the previous pass
recorded as owed. That amendment is likewise **pending the author's re-approval**. The two rows the
`chore-0036` pass moved are re-derived here and both close: `Output format` returns to `Conformed`
now that the contract admits the second summary line, and `What it reads` keeps its status with the
weakness its own note named repaired in the spec rather than in the matrix. No other row is
re-derived, for the reason the `chore-0036` paragraph gives: `check_supporting_files()`,
`classify_supporting_file()` and `_is_shipped()` are functions no other row cites, and this pass
changed no code at all. **This extension is a contract change, not an implementation change**, which
makes it the narrowest kind of re-audit here: the code is byte-identical to what the previous pass
audited, so what moved is only whether a scenario states it.

Re-audited 2026-08-22 (`chore-0055`) over S-024 alone, to close the bound the previous pass stated
inside that row. `classify_supporting_file()` matched the `.tmpl` marker exactly while lowering the
markdown suffixes beside it, so a file named `X.md.TMPL` classified as neither and landed in the
non-markdown count. Both tests are now case-insensitive. **This is an implementation change that
moves no status and amends no contract**: S-024 names "the `.tmpl` suffix on the file's name" without
stating a case rule, so the scenario reads true before and after and was deliberately not touched.
The reach was measured rather than asserted, on the same day and against the same tree: the coverage
line reports `Link-checked 1 supporting file(s) beside them; skipped 8 template(s) ... and 5
non-markdown file(s).` both before and after the change, because every template the kit ships already
carries a lowercase `.tmpl`. Only the S-024 row and its test-coverage row are re-derived; no other row
is, because `classify_supporting_file()` is cited by no other row and no other function changed.

Extended 2026-08-29 (`feat-0064`) with S-026, the universal-lens rule: a lens declaring universal
scope in its own opening must be referenced by every skill, not merely by one. That amendment is
likewise **pending the author's re-approval**. It is the first row here written for behaviour the
same task built, rather than for behaviour that had already shipped, so the row and the code were
produced together and the row records that rather than implying an audit of older work.

Extended 2026-08-27 (`chore-0065`) with S-025, the non-skill `.agents/` markdown link rule
`chore-0058` added to the script on 2026-08-27 and this contract did not state. That amendment is
likewise **pending the author's re-approval**. Three items are re-derived in this pass: the new S-025
row, and the two Proposed Surface elements `Output format` and `What it reads`, both of which were
falsified between the previous pass and this one and neither of which any gate reported. `What it
reads` was falsified by `chore-0058` itself, which made the element's closing clause, that nothing
outside the skills directory and its sibling `rules/` is read, untrue of a script that now opens
`.agents/hooks/README.md`. `Output format` was falsified by `chore-0064` on 2026-08-27, which carried
the skill count into the second summary line and in doing so replaced the wording this row quoted.
Both are closed here by amending the contract rather than by changing the code, which is the same
disposition `chore-0054` recorded, and **both rows are re-audited against the current script rather
than repaired by editing their quotes**: repairing a citation without re-deriving the verdict asserts
a freshness the repair did not establish, which is the move `chore-0062` declined for the same
reason. No other row is re-derived. `check_portable_markdown()` and `portable_coverage()` are new
functions no other row cites; `check_links()`, `classify_supporting_file()` and `_is_shipped()` are
reused by the new caller with every branch and message body unchanged; and `chore-0064` added one
expression to one `print()` and touched nothing else. This is the fifth time the implementation has
grown past this contract, after `feat-0023`, `bug-0027`, `feat-0048` and `chore-0036`, and the
pattern the `chore-0036` paragraph named holds for the fifth time: the gap was found at a later
task's closeout rather than by any gate.

Re-audited 2026-08-27 by `chore-0045`, and **partially**: one row, the `S-022` row in the test
coverage section below. That task retags `TestLinkChecksInsideCodeSpansAndFences` and all six of its
cases from `Scenario S-009 refined` to `S-022`, which is the follow-up this row named and declined to
do, so the row's closing sentence described a state the same change removed. No scenario row and no
surface element was re-derived, and no file under `scripts/` was touched; every row in the matrix
proper carries its previous audit date. Two passes now share the date 2026-08-27 and they are two:
`S-025` and the two surface elements belong to `chore-0065`, and this pass looked at none of them.

That row was re-derived against the retagged file **before** its citation moved, per the disposition
`chore-0062` and `chore-0065` both recorded. It keeps `present`: six tests, unchanged in what they
assert. The re-derivation also found one clause of the row wrong independently of the retag, and the
row now says so rather than quietly dropping it. Correcting a stale tag and correcting a claim that
was never true are different repairs, and a reader who cannot tell them apart cannot tell how much of
this document was ever checked.

Two sentences elsewhere in this document are falsified by the same retag, and are **named here rather
than edited**, because each sits in a row or a passage this pass did not re-derive. The `S-025` row
counts the outstanding retag follow-up at four sets; with S-022's six now done it stands at three,
S-023's nine, S-024's thirteen and S-025's fifteen. And the paragraph closing the test coverage
section, the one `chore-0065` deliberately restated rather than deleted, still places S-022's six
tests in the untagged position they have now left. Editing either would repair a claim this pass did
not audit, which is the move the paragraph above declines.

The reach of the new rule was measured rather than asserted, which is what makes it checkable. Across
the twenty shipped `SKILL.md` bodies on 2026-08-19, `LINK_RE` matches 133 links and 0 of them sit
inside a code span or a fence, so every skill lints exactly as it did before the guard existed. That
second number is the load-bearing one: the exception currently fires on nothing in this kit. It is a
guard against a body that shows a link as an example, which the documentation skills are the likeliest
to want, rather than a rule with live occurrences today. A row asserting a conformed status without
that number would not distinguish a working guard from a dead one. The same measurement over the same
bodies backs S-018 in [`build-adapters.conformance.md`](build-adapters.conformance.md), because the
two tools carry character-identical copies of the two range helpers.

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
| Scenarios | S-009 link target does not exist | Conformed | `check_links()` / final `if not resolved.exists()` branch | records the unresolved path; reached only after the span and fence guard (S-022) and then the external, anchor, sibling and portability branches have passed. Re-audited 2026-08-19 (`chore-0039`): the branch itself is unchanged, and the guard is now first in that order |
| Scenarios | S-010 dangling sibling-skill reference | Conformed | `check_links()` / `if sibling:` branch, `sibling_name not in skill_names` | a `../<name>/SKILL.md` link is resolved by skill-name membership rather than by path, then `continue`s. Re-audited 2026-08-19 (`chore-0039`): unchanged, and now reached only outside a code span or fence (S-022) |
| Scenarios | S-011 link escapes the distributed tree | Conformed | `check_links()` / `not resolved.is_relative_to(portable_root)` branch, with `main()` / `portable_root = skills_dir.parent.resolve()` | the escape branch precedes the existence check, so a link whose target exists in this repository still errors, which is the behavior the scenario requires. Re-audited 2026-08-19 (`chore-0039`): unchanged outside a span or fence, and inside one it is skipped along with every other branch, which S-022 states as a decision rather than an accident |
| Scenarios | S-012 link to the rules module is legal | Conformed | `main()` / `portable_root = skills_dir.parent.resolve()`, with `check_links()` / the `is_relative_to` guard | `../../rules/<file>` resolves inside `.agents/`, so it passes the portability guard and is then subject only to the ordinary existence check. Re-audited 2026-08-19 (`chore-0039`): unchanged, and now reached only outside a code span or fence (S-022) |
| Scenarios | S-013 external and same-page links not resolved | Conformed | `check_links()` / `EXTERNAL_LINK_PREFIXES` guard and the `if not path_part` anchor guard | both `continue` before any filesystem access. Re-audited 2026-08-19 (`chore-0039`): unchanged. S-022 now sits ahead of it and governs a different question, whether the text is a link at all, where this row governs the link's kind |
| Scenarios | S-022 a link that renders as literal text is not a link | Conformed | `_link_targets()` / `spans = code_span_ranges(text) + fenced_block_ranges(text)` and the `any(start <= m.start() < end ...)` guard, with the two helpers `code_span_ranges()` and `fenced_block_ranges()` above it; consumed by `check_links()`, which iterates only what `_link_targets()` yields | added by `chore-0039`, writing down what `bug-0027` built. Suppression happens at the generator, so every branch of `check_links()` is skipped at once rather than each having to remember the rule. The guard is keyed to `m.start()`, the link's opening bracket, so a link whose *text* is itself a code span is still checked, which is how nearly every link in this kit is written. `build-adapters.py` keys the same rule to the bracket closing the link text instead; both leave that common form governed by the ordinary rules. An unterminated fence yields no range, so it suppresses nothing below it. Confirmed by measurement on 2026-08-19: 20 shipped bodies, 133 links matched, 0 inside a span or fence, so the kit lints identically today and the row is a guard rather than a live exclusion |
| Scenarios | S-024 a markdown file shipped beside a SKILL.md is link-checked where it sits | Conformed | `check_supporting_files()`, called from `main()` at the head of the per-skill loop, with `classify_supporting_file()` for the two exclusions and `_is_shipped()` for the byte cache; it calls `check_links()` passing the supporting file as `source` and `sibling_shortcut=False` | added by `chore-0054`, writing down what `chore-0036` built. Every relative target resolves from `source.parent`, which is what "where it sits" means, and the error `label` is the supporting file's path rather than the skill's. The exclusion is `path.name.lower().endswith(TEMPLATE_SUFFIX)`, a property of the file rather than a table, and it is tested by suffix and not by directory name, which is why `project-bootstrap/templates/house-code-style.md` is checked while the eight `.tmpl` files beside their own SKILL.md are not. `sibling_shortcut=False` is the S-010 disapplication the scenario states. The call sits before the `not skill_md.is_file()` branch and outside every `continue` below it, so a directory earning the S-001 or S-002 error keeps its supporting files checked and counted. Confirmed by execution 2026-08-21 against a synthetic skill tree: a supporting markdown file carrying an unresolved link, an escaping link and a `../beta/SKILL.md` link produced exactly three errors, each naming that file and not the `SKILL.md`, and exit 1, while a `.tmpl` sibling carrying the same unresolved link and a `.py` sibling carrying markdown link syntax produced none. **The bound the previous pass stated inside this row is closed** (`chore-0055`): the two suffix tests differed in case sensitivity, `.tmpl` matching exactly and the markdown suffixes matching case-insensitively, so a file named `X.md.TMPL` was counted as non-markdown rather than as a template. Both are now matched against a lowered name and a `.TMPL` file is a template. The scenario's own assertion never moved, since such a file was not read before and is not read now; what changed is only which *skipped* count it lands in. The closure cannot reach the checked set in either direction, and the argument is exhaustive rather than empirical: a name ending in `.tmpl` in any case has `.tmpl` as its `suffix`, so it can never also satisfy the markdown test, and the marker test runs first. Confirmed by execution 2026-08-22: the coverage line over the shipped tree is byte-identical before and after |
| Scenarios | S-025 markdown shipped beside the skills tree is link-checked where it sits | Conformed | `check_portable_markdown()`, called from `main()` after the per-skill loop and after `check_lenses_are_composed()`, with `classify_supporting_file()` and `_is_shipped()` reused for the exclusions and `check_links()` called with the file as `source`, `portable_root` as the ceiling and `sibling_shortcut=False`; the three renderings in `portable_coverage()` over its `counts is None` and `not any(counts.values())` branches | added by `chore-0065`, writing down what `chore-0058` built. The walk is over `portable_root.rglob("*")` with `path.is_relative_to(skills_dir)` skipped, so its subject is the geometry the scenario states and not a named pair of directories: nothing in the function mentions `rules` or `hooks`, and a third sibling would be covered the day it is added. `sibling_shortcut=False` is the S-010 disapplication, and the reason is the sharper one the scenario gives, that `../<name>/SKILL.md` from beside the skills tree names a sibling of that file's own directory. The `portable_root` ceiling is unchanged from S-011, so a rules file reaching `../skills/<name>/SKILL.md` stays inside the tree and one reaching `../../ROADMAP.md` does not. `portable_coverage()` returns three different sentences, only one of which carries the counts, which is what makes the outcomes distinguishable; the guard that produces the first, `skills_dir.name != SKILLS_DIR.name`, is deliberately not a clause of the scenario, per its closing paragraph. Confirmed by execution 2026-08-27 against synthetic trees: a rules file carrying both an escaping link and an unresolvable one produced exactly two errors, each naming that file, one reading `link escapes the shipped skill tree` and the other `link target does not exist`, and exit 1, so the two halves are reported as different findings rather than collapsed into one. The three outcomes were produced in turn and are mutually distinguishable: a bare directory of skill folders reports that it did not look and names the directory; a shipped layout with nothing beside the skills tree says nothing ships there; and the same layout holding one `.tmpl` file reports 0 checked with 1 template skipped beside it. Reach measured the same day over this repository's own tree: 4 markdown files read (`rules/autonomy.md`, `rules/house-style.md`, `rules/review-quality.md`, `hooks/README.md`), 0 templates and 5 non-markdown files counted and not read, and 0 errors, so the rule reports nothing in the kit today and is a guard rather than a live exclusion |
| Scenarios | S-014 contradictory status claim warns | Conformed | `check_status_contradiction()` with the widened `DRAFT_STATUS_RE` and `SHIPPED_STATUS_RE` | diverged when first audited on 2026-07-27 and was fixed the same day. The patterns now cover assertion forms (`is`/`remains`/`stays` a draft, a `status: draft` line, `draft pending`) and provenance forms (a `shipped`/`blessed` list item, or either word before an ISO date). Re-probed against the five phrasings that produced the original finding: all five flag. Four negative cases produce no finding, including prose that merely discusses drafts and a skill whose `status: draft` refers to a spec it authors rather than to itself. |
| Scenarios | S-015 skills directory does not exist | Conformed | `main()` / `if not skills_dir.is_dir()` guard | prints the missing-directory error and returns 1; confirmed by execution (exit 1, `ERROR no skills directory at ...`) |
| Scenarios | S-016 skills directory exists but is empty | Conformed | `main()` / `if not skills:` guard after `skills_dir.iterdir()` | prints `No skills found under ...` and returns 0; confirmed by execution (exit 0) |
| Scenarios | S-017 description over the harness limit fails | Conformed | `main()` / `elif len(desc) > MAX_DESC_CHARS` branch, with `MAX_DESC_CHARS = 1024` | appends to `errors`, so the run exits non-zero; the message carries both the measured length and the limit. Confirmed by execution against a copy of the real skills tree with one description padded over the bound: exit 1, `description is 1173 chars, over the 1024-char limit`. The boundary is `>`, so a description of exactly 1024 produces no finding |
| Scenarios | S-018 description measured by value, not YAML syntax | Conformed | `parse_frontmatter()` / `BLOCK_SCALAR_RE.sub("", value, count=1)` on the field-line branch | the indicator is stripped at the head of the field line only and once, so `>`, `>-`, `>+`, `\|`, `\|-`, and `\|+` are removed while a plain scalar and any angle bracket inside the prose are untouched. The four block-scalar descriptions in the kit each measure 3 fewer characters than before the fix, which is the defect this closes |
| Scenarios | S-019 unparseable frontmatter fails | Conformed | `check_frontmatter_is_parseable()`, called from `main()` after `check_links()` | errors on a plain unquoted scalar containing `": "` or ending in `":"`, and skips a block scalar or a fully quoted value. Confirmed by execution: a copy of the real `.agents/` tree with `house-review`'s description put back into the single-line plain form that shipped exits 1 with the nested-mapping error. The message states that it checks one known construct rather than YAML validity, which is the honest limit of a standard-library check |
| Scenarios | S-020 angle bracket in a description fails | Conformed | `main()` / the `if desc and ("<" in desc or ">" in desc)` branch | reads the parsed value, so the twelve block-scalar descriptions are not flagged for the `>` in their own indicator. `human-handoff` was violating this in the field and is fixed |
| Scenarios | S-021 unrecognised frontmatter property fails | Conformed | `main()` / the `for key in sorted(set(fm) - ALLOWED_FRONTMATTER_KEYS)` loop, with the `ALLOWED_FRONTMATTER_KEYS` constant | an allow-list of the schema's six properties, commented with its source and the date it was read. `version` is deliberately excluded: the reference implementation rejects it even though Anthropic's own example skill documents it as optional |
| Scenarios | S-023 a self-declared lens no skill references fails | Conformed | `check_lenses_are_composed()`, called from `main()` after the per-skill loop with `portable_root / "rules"` and the `skill_texts` dict `main()` accumulates; declaration by `declares_itself_a_lens()` over `LENS_DECLARATION_RE` and `LENS_DECLARATION_LINES` | added by `chore-0047`, writing down what `feat-0048` built. One error per unreferenced lens, not one per skill, because the call sits outside the loop. A reference is `_names_file_outside_fences(skill_text, rules_file.name)`, so a relative link and a prose mention naming the file both satisfy it and the bare subject word does not, which is what the scenario states. The declaration is read only in the opening (10 lines), keyed to a self-declaration rather than a filename list, so the rule fires for the next lens too. Re-measured 2026-08-20 (`bug-0040`): 3 files in `.agents/rules/`, all 3 declare themselves lenses inside the window, and all 3 are referenced, by 20, 5 and 4 skills respectively, unchanged by the fence guard, so the rule reports nothing today and is a guard rather than a live exclusion. **The asymmetry the `chore-0047` audit recorded here is closed** and no longer appears in this row: a body whose only mention of a lens filename sits inside a fenced block no longer satisfies the rule, which is the same refinement S-022 makes for the link rules. **S-023's wording is unchanged and still holds**: the scenario says the filename appears in a `SKILL.md`, and the fence guard changes which appearances count rather than what the scenario asserts, exactly as S-022 does for S-009 through S-013. The guard stops at fences and does not extend to inline code spans, argued in the extension note above |
| Scenarios | S-026 a universal-scope lens some skill never references fails | Conformed | `check_universal_lenses_reach_every_skill()`, called from `main()` immediately after `check_lenses_are_composed()` with the same two arguments; scope read by `declares_universal_scope()` over `UNIVERSAL_SCOPE_RE`, and reference counted by the same `_names_file_outside_fences()` S-023 uses, so the two rules cannot drift on what a reference is | added by `feat-0064`. Both gates must hold before the rule applies: the file declares itself a lens **and** declares universal scope, so a directory README quoting the marker is not conscripted. The marker is matched outside fenced blocks for S-023's reason, a fence showing what a declaration looks like rather than making one. Reported once per lens naming every skill that misses it. Proven by `TestUniversalLensScope`, six tests: two positives (one skill missing, and three missing with the count and every name in one finding), and four negatives that carry the weight (a fully referenced universal lens, a topical lens needing only one referrer, a marker inside a fence, and a non-lens document quoting the marker). Against the real tree by `test_every_shipped_universal_lens_reaches_every_shipped_skill`, `test_autonomy_is_composed_by_every_skill_because_it_declares_universal_scope`, `test_review_quality_stays_topical_so_the_universal_rule_means_something`, and `test_at_least_one_shipped_lens_declares_universal_scope`, which stops the real-tree assertion passing over a tree where nothing is universal |
| Proposed Surface | Invocation `python scripts/validate-skills.py` | Conformed | module `__main__` guard | `if __name__ == "__main__": raise SystemExit(main())` |
| Proposed Surface | What it reads: skills plus the sibling rules module | Conformed | `main()` / `portable_root = skills_dir.parent.resolve()` and the `check_lenses_are_composed(portable_root / "rules", ...)` call | added by `chore-0047`. `portable_root` already existed to serve the S-011 portability guard; the lens rule is the first use that reads a file under it. Nothing outside the skills directory and its sibling `rules/` is opened. Re-derived 2026-08-21 (`chore-0036`): still conformed, and the surface sentence "every skill directory under the target skills directory" is now true of the whole directory rather than of its `SKILL.md` alone. `check_supporting_files()` walks each skill directory and opens the markdown it finds there, which is inside the pair this element names, so the boundary the element draws is unmoved. The wording was nonetheless weaker than it read, because it was written when only one file per directory was ever opened. Re-derived again 2026-08-21 (`chore-0054`): the element now says the directory is read in full and names which of its files are opened and which are only counted, so the gap the previous pass recorded is closed in the contract rather than carried as a note here. **Diverged from 2026-08-27 (`chore-0058`) until this pass, and closed by `chore-0065`** by amending the contract rather than by changing the code. That change gave the script `check_portable_markdown()`, which opens `.agents/hooks/README.md`, and the element's closing clause said that nothing outside the skills directory and its sibling `rules/` is read. The divergence was in the element's boundary rather than in its opening sentences, and it was re-derived here against the current script rather than repaired by editing the clause: the walk is `portable_root.rglob("*")` minus the skills subtree, so what is read is the whole distributed tree and not a second named directory, and the element now says so and adds that the outside-skills walk does not always run |
| Proposed Surface | Exit non-zero on error only | Conformed | `main()` / final `return 1 if errors else 0` | warnings do not affect the exit code |
| Proposed Surface | Output format | Conformed | `main()` / the `WARN` and `ERROR` loops, the `Checked {len(skills)} skill(s)` print, the second `print` following it, and the two early-return prints in the `not skills_dir.is_dir()` and `not skills:` guards | **Diverged in the 2026-08-21 (`chore-0036`) pass and closed by `chore-0054`**, by amending the contract rather than by changing the code, which is the disposition that pass recorded. That pass amended the element to admit a second line carrying the supporting-file counts by reason. Everything the element already stated was unchanged and was re-checked then: the two loops, the summary line verbatim, and the two early-return prints, which replace both summary lines together because the second print sits after the guards that return. **Re-derived 2026-08-27 (`chore-0065`) after two changes falsified the row's account of that second line, neither reported by any gate.** `chore-0058` appended the outside-skills coverage to it, and `chore-0064` opened it on the skill count in place of the pronoun the row quoted, so the quoted wording no longer exists in the script. The verdict is re-derived rather than the quote repaired: read against the current `print()` and against `portable_coverage()`, the line still opens on the supporting-file counts and still reports them by reason, and it now carries the outside-skills half in one of three mutually distinguishable forms, which is what the amended element requires and what the S-025 row confirms by execution. Everything else the element states was re-checked in this pass and is unchanged: the ordering of the two lines, the first line's text, and the two early-return prints. The count `N` is still of skills, so an S-023, S-024 or S-025 error raises `E` without changing `N`. **One thing the line carries that the element does not name**: since `chore-0064` the second line also states the skill count, which is additional rather than contradictory, so this row stays `Conformed`. Whether the element should name it, and whether the two lines should be reordered at all, is the open decision `chore-0064` recorded and rejected shape 3 rather than settle; this pass deliberately left the element's ordering clause alone |

## Coverage proof

- **audited**: S-001 through S-026, and all four Proposed Surface elements (invocation, what it
  reads, exit code, output format). The arithmetic, written out because a matrix that asserts full
  coverage without it is the failure `spec-conformance` exists to prevent: the spec carries 26
  scenarios, numbered S-001 to S-026 with no gap and none retired, and 4 surface elements, so 26 + 4
  = 30 spec items. This matrix carries 26 rows under `Scenarios` and 4 under `Proposed Surface`, 26 +
  4 = 30 rows. Every spec item was checked. S-022 is numbered after S-021 and placed beside S-013 in
  both documents, because it is the exception the link rows are read against, and S-024 is placed
  immediately after it for the same reason: it is the link rules applied to a different file, so it
  is read against the same cluster. S-025 follows S-024 in both, being the same rules applied one
  directory level further out. S-023 is placed last in both, because it is the only rule whose
  subject is the absence of an inbound reference and it is read against nothing above it, and S-026
  sits immediately after it, being the same subject under a stronger rule.
- **re-derived in the 2026-08-29 (`feat-0064`) pass**: 1 item, S-026, which this pass both built and
  audited. The other 25 scenario rows and all 4 surface elements are carried forward from the passes
  named in the header, unchanged and not re-checked: 1 re-derived + 29 carried forward = 30, the
  whole item count above. **A row written by the task that wrote the code is weaker evidence than a
  row written against code somebody else shipped**, and saying so is the point of recording it
  separately rather than folding it into the audited list.
- **re-derived in the 2026-08-27 (`chore-0065`) pass**: 3 items, S-025 and the two Proposed Surface
  elements `Output format` and `What it reads`. The other 24 scenario rows and the other 2 surface
  elements are carried forward from the passes named in the header, unchanged and not re-checked: 3
  re-derived + 26 carried forward = 29, the whole item count above. Stated because a partial audit is
  not a whole one. They are safe to carry because `chore-0058` added two functions,
  `check_portable_markdown()` and `portable_coverage()`, that no other row cites, and reused
  `check_links()`, `classify_supporting_file()` and `_is_shipped()` from a new caller without
  changing a branch or a message body in any of the three; and because `chore-0064` added one
  expression to one `print()`. S-024 is carried rather than re-derived for that second reason: the
  scenario asserts which files are read and counted, which the added expression does not touch, and
  the shape of the line it does touch is the `Output format` element's assertion rather than S-024's.
  **The bullets below state the item count as it stood in their own passes, 28, before S-025
  existed.** Their arithmetic is left exactly as each pass recorded it rather than restated against
  today's 29, because each is a record of what one pass covered on one date and re-adding a row it
  never saw would make it a claim nobody checked.
- **re-derived in the 2026-08-22 (`chore-0055`) pass**: 1 item, S-024. The other 23 scenario rows
  and all 4 surface elements are carried forward from the passes named in the header, unchanged and
  not re-checked: 1 re-derived + 27 carried forward = 28, the whole item count above. Stated because a
  partial audit is not a whole one. They are safe to carry because the change touched one function,
  `classify_supporting_file()`, which no other row cites, and left every other branch and message body
  in the script untouched. `Output format` is carried rather than re-derived because the summary line
  it states is unchanged in wording and, measured on the shipped tree, unchanged in its numbers.
- **re-derived in the 2026-08-21 (`chore-0054`) pass**: 3 items, S-024 and the two Proposed Surface
  elements `Output format` and `What it reads`. The other 23 scenario rows and the other 2 surface
  elements are carried forward from the passes named in the header, unchanged and not re-checked: 3
  re-derived + 25 carried forward = 28, the whole item count above. Stated because a partial audit is
  not a whole one. They are safe to carry for a reason narrower than usual, that this pass changed no
  code: the script is byte-identical to the one the `chore-0036` pass audited, and only the contract
  moved.
- **re-derived in the 2026-08-21 (`chore-0036`) pass**: two Proposed Surface elements only, `Output
  format` and `What it reads`. The twenty-three scenario rows and the other two surface elements are
  carried forward from the passes named in the header, unchanged and not re-checked. Stated because a
  partial audit is not a whole one. They are safe to carry because the change added two functions no
  row cites and left every branch and message body of `check_links()`, the one function any row
  cites, as it was. S-024 did not exist in that pass.
- **re-derived in the 2026-08-20 (`bug-0040`) pass**: S-023 only, plus its row in the test-coverage
  table. The other twenty-two rows and all four Proposed Surface elements are carried forward from
  the passes named in the header, unchanged and not re-checked in this pass. Stated because a partial
  audit is not a whole one, and the carried-forward rows are safe to carry only because
  `check_lenses_are_composed()` and its new helper are reached by no other rule here.
- **unreconciled**:
  - **S-008 (Diverged)**: disposition **accepted-with-reason**. The "what and when" bar is aspirational
    and a full natural-language check is out of scope for a standard-library structural linter; the
    length proxy is a deliberate, documented approximation. If the kit later wants to enforce it, the
    honest fix is to soften the spec wording to "length proxy" or add a real check, not to claim the
    current code satisfies the stated intent. Unchanged from the 2026-07-24 audit.
The one item the 2026-08-21 (`chore-0036`) pass added to that list, **Output format (Diverged)** and
the supporting-file rule behind it, is **closed** and no longer unreconciled. Its disposition was
**amend the spec**, and `chore-0054` did exactly that: S-024 states the rule, the `Output` element
admits the second summary line, and the `What it reads` element says the skill directory is read in
full. All three owed items that entry named are delivered, and both rows are re-derived above against
the same unchanged code. It is recorded as closed rather than erased, because the useful part of the
history is that the rule shipped on 2026-08-21 pinned only by `TestSupportingFileLinkChecks` in
[`tests/test_validate_skills.py`](../../tests/test_validate_skills.py), which was the same position
S-022 and S-023 were in before `chore-0039` and `chore-0047` wrote them down, and the fourth time the
implementation grew past this contract without a gate noticing.

S-014 was the second unreconciled item when this matrix was first regenerated on 2026-07-27, carrying
disposition **fix**. The author chose to widen rather than to narrow the scenario, the patterns were
widened the same day, and the row above is the re-audit. It is recorded here rather than erased
because the divergence is the useful part of the history: the check had shipped on 2026-07-25, was
believed correct for two days, and was only caught when a scenario was written that stated the
condition semantically instead of restating the implementation.

No spec item was silently dropped. One item diverges of the 29: S-008, accepted with a stated reason.
The other 28 conform, 1 + 28 = 29.

## Test coverage of spec invariants

Flagged per `spec-conformance`'s non-goal (it does not write tests, but does say where an invariant
lacks one). Against [`tests/test_validate_skills.py`](../../tests/test_validate_skills.py):

| Scenario | Covering test | Note |
|---|---|---|
| S-009 through S-013 | present | one test each, plus negative cases for S-010 and S-012, each tagged with its scenario id |
| S-022 | present | added by `bug-0027`, six tests in `TestLinkChecksInsideCodeSpansAndFences`. Two positives, a fenced link and an inline span in both the single and the double backtick form. The negatives carry the weight, since the cheap way to remove a false positive is to switch the check off: a genuine broken link beside a *closed* fence and one below an *unterminated* fence must both still be reported. A fifth asserts the escape rule S-011 is skipped inside a fence too, which is the decision this scenario records rather than an accident, and a sixth runs `check_links()` over the real tree, so the exclusion is shown not to have changed what the kit's own skills report. **The tests predate the id and no longer carry the older tag**: `bug-0027` wrote them before any scenario stated the rule and tagged the class `Scenario S-009 refined`, `chore-0039` stated it as S-022 on 2026-08-19, and `chore-0045` retagged the class and all six cases on 2026-08-27, which is the follow-up this row previously deferred. Re-audited on that date against the retagged file: six tests, unchanged in what they assert, and the tags now name what they cover rather than less. **One clause of this row was wrong when it was written, and is corrected rather than carried**: it said the docstrings describe the amendment as the author's open call. They never did. Searching the file's whole history for that sentence, by `git log -S` on both "author's call" and "open call" over `tests/test_validate_skills.py`, returns no commit. The sentence belongs to the parallel `S-018` row in [`build-adapters.conformance.md`](build-adapters.conformance.md), whose class docstring did carry it until `chore-0045` removed it. Here the tag was the only stale thing, and the retag is the whole of what changed |
| S-014 | present | table-driven over all five contradiction phrasings and four negative cases. Confirmed to fail on four of the five against the pre-fix patterns, which is the bug population; the canonical phrasing always passed and proves nothing on its own, which is exactly how the original single-case test hid the divergence |
| S-015, S-016 | present | added 2026-07-27 once the contract was approved. Asserts the pair together: the absent directory must fail and must not report `Checked 0 skill`, the empty one must succeed |
| S-017 | present | two tests: over the limit errors with the measured length in the message, and exactly at the limit does not, so an off-by-one that rejected a legal description would fail |
| S-020, S-021 | present | added by `bug-0008`. Five tests: an angle bracket errors, a block-scalar description is not flagged for its own indicator, an unrecognised key (`version`) errors, all six permitted properties together pass, and both rules hold across the real nineteen. The two negative cases are the ones that keep the checks usable: flagging a block scalar would fail twelve valid skills, and rejecting a legal property would fail a valid skill while looking like a kit bug |
| S-019 | present | added by `bug-0007`. Six tests: the two positive constructs (a colon-space inside a plain scalar, and a value ending in a colon), three negative cases that must not fire (a block scalar, a quoted value, and a URL whose colon has no following space), and one that runs the check over all nineteen shipped skills, which is the assertion that would have caught the defect. The negative cases carry the weight: a false positive would push authors to contort a description to satisfy a checker rather than a parser |
| S-018 | present | three tests: a block scalar whose text is exactly at the limit must pass (it measured 3 over before the fix), every indicator form strips at the parser layer, and two negative cases hold, a plain scalar and prose containing angle brackets. The negative cases are the load-bearing ones, because over-eager stripping shortens a description silently instead of failing |

| S-023 | present | added by `feat-0048` and extended by `bug-0040`, twelve tests in `TestLensComposition`. Three positives, a declared lens with no inbound reference, one whose only mention is the bare subject word, and one whose only mention sits inside a fenced block, all of which must error. The other nine are negatives, and they carry the weight for the reason the class docstring gives: this rule reads files nobody asked it to lint, so a false positive lands on a document whose author never opted into being a lens and the cheap response is to delete the rule. They cover a referenced lens by link, a reference by prose naming the file, a plain rules document that never declares itself, and a declaration below the opening window. `bug-0040` added two more of the same shape, and they are the ones that keep the fence guard from switching the rule off: a genuine reference beside a *closed* fence and one below an *unterminated* fence must both still count, which is the pair S-022's tests already carry for links. The reference-by-prose test doubles as the pin on the span decision, since its fixture names the file inside an inline code span and must still pass. The last three run against the real tree: the opening window clears every shipped lens with margin (bounded in both directions rather than asserted as a bare number, per `bug-0026`), every shipped lens is composed, and `autonomy.md` is referenced by exactly the five skills it cites, no more and no fewer. **Nine of the twelve predate the scenario id**, as S-022's tests did: they are tagged `feat-0048` rather than `S-023`. `bug-0040`'s three are tagged `Scenario S-023` and did not retag their neighbours, so the gap is narrower than it was and still open. `chore-0045` item 4 makes exactly this correction for S-022 and does not cover S-023, which postdates it, so the S-023 retag remains a follow-up rather than an already-filed one |
| S-026 | present | added by `feat-0064`, six tests in `TestUniversalLensScope` plus four against the real tree in `TestLensComposition`. The six break down 2 + 4: two must fire, a universal lens one skill misses and one three skills miss, the second asserting the count, every name, and that the lens is reported once rather than once per skill. Four must not, and they are the ones that keep the rule from being deleted: a fully referenced universal lens, a topical lens with a single referrer, a marker inside a fence, and a non-lens document quoting the marker outside one. **Four of the six pass against the unfixed code**, because they assert an absence of error, which is stated here rather than counted as evidence |
| S-024 | present | added by `chore-0036` as characterization and repointed here by `chore-0054` now that a scenario states the rule, thirteen tests in `TestSupportingFileLinkChecks`. The thirteen break down 4 + 4 + 3 + 2. Four must fire: an unresolved link in a supporting file, one escaping the shipped tree, a `../beta/SKILL.md` link that must *not* be cleared by the sibling shortcut (the false negative the disapplication in S-024 exists to remove), and a markdown file inside a `templates/` directory that must still be checked, which is the pin on the exclusion being by suffix and not by directory name. Four must not, and they carry the weight as they do for S-022 and S-023: a `.tmpl` file and a non-markdown file must not be read, a link inside a fence must not be reported, and a supporting file whose links do resolve must pass. Three pin the counting rather than the checking: a byte cache is not counted, a skill with no supporting files reports zero, and the second summary line has the stated shape. Two run against the real tree: the classification of all fourteen shipped supporting files, and that every one of them that is read passes. Measured 2026-08-21 against the pre-change script: 8 fail and 2 error, which is what makes them tests of the change rather than a restatement of it, and the other 3 pass on both sides, which is what a negative case should do. **Extended by `chore-0055`** with four tests in `TestSupportingFileSuffixCase`, the first tests here tagged `S-024` at the time they were written. Two are unit tests on `classify_supporting_file()`, one per suffix family, so the two families are pinned together and cannot drift apart again in either direction; the template one is table-driven over every case variant, because a fix that special-cased the all-caps spelling would pass a single-variant test. Two run end to end and hold the bound from both ends: a `.TMPL` file carrying an unresolvable link and an escaping one is neither reported nor counted as non-markdown, and a `notes.MD` file carrying an unresolvable link is still reported by name, so the widened marker is shown not to have swallowed anything. Measured 2026-08-22 against the pre-change script: the two template-side tests fail and the two markdown-side tests pass, which is what makes the pair a test of the change rather than a restatement of it |
| S-025 | present | added by `chore-0058` as characterization and repointed here by `chore-0065` now that a scenario states the rule, fifteen tests in `TestPortableMarkdownOutsideTheSkillsTree`. The fifteen break down 4 + 4 + 5 + 2. Four must fire, and they pin the scenario's two halves as different findings: a dangling link in a rules file, a dangling link in the hooks README (the file both existing gates missed most completely, since nothing else in `scripts/` or `tests/` reads a link out of it), a link above the shipped tree whose oracle is the escape message *and* the absence of the not-found message, and a `../<name>/SKILL.md` link that must not be cleared by the sibling shortcut. Four must not: a link to the skills tree beside it, a `.tmpl` file, a link inside a fence, and a byte cache. Five pin the reporting rather than the checking. Four of those five hold the three renderings apart from one another: files found and checked with the counts by reason, files found and none checked, nothing shipped beside the skills tree, and a tree with no shipped layout around it. Three of the four assert the *absence* of a neighbouring rendering's wording as well as the presence of their own, which is what makes them tests of the distinction rather than of one sentence each. The fifth asserts the supporting-file and outside-skills counts together, so a walk covering the wrong half of the tree fails rather than passing on one number. Two run against the real tree, in the order that matters: the inventory of the four governed files by name first, then that every one of them passes, because "nothing dangles" is satisfied by an empty walk and the empty walk is the failure this rule is about. **All fifteen predate the id**, as S-022's and most of S-023's did: tagged to `chore-0058` and describing the amendment as owed, which this pass makes. Retagging joins the same follow-up of `chore-0045`'s shape, now covering four sets rather than three |

Every scenario except S-008 now has a covering test, including the code-span rule that had tests
before it had a scenario. S-008 remains deliberately untested, because a
passing test there would assert behavior the accepted divergence says does not exist.

**Every test in the file now maps to a scenario in this contract**, which was not true when the
previous pass wrote this section. The thirteen in `TestSupportingFileLinkChecks` were the exception it
recorded, tagged as characterization of `chore-0036` and carrying no `S-NNN` id because no scenario
stated the rule; S-024 states it, so they are mapped in the row above rather than counted as covering
nothing. Their tags are now stale in one direction only, naming less than they cover, which is the
same position S-022's six tests and nine of S-023's twelve are in. Retagging all three sets is a
follow-up of `chore-0045`'s shape, and is deliberately not done here because this task changes no file
under `tests/`.

`chore-0055` did change that file, and did not take the retag with it: its four new tests sit in their
own class, `TestSupportingFileSuffixCase`, tagged `S-024`, rather than being folded into the
thirteen. Retagging the existing thirteen stays the follow-up it already was, because that task is one
edit across three sets and doing a third of it in passing would leave the ledger above harder to read
rather than shorter.

**That claim was true when it was written and is not true today, and this pass restates it rather
than deleting it.** Two classes have been added to the file since: `chore-0058`'s fifteen tests in
`TestPortableMarkdownOutsideTheSkillsTree`, which S-025 now maps in the row above, and `chore-0064`'s
five in `TestTheCoverageLineTheAggregatorSelects`, which **no scenario in this contract states**.
Those five pin which of the two summary lines `run-checks.py` selects and that the selected line
moves when the gate's own scope moves. The first half is the `Output format` element's ordering
clause, which they exercise from the aggregator's side; the second half, that the second line names
the skill count, is stated by no scenario and by no surface element. That is the open decision
`chore-0064` recorded when it rejected amending the ordering clause, and this pass deliberately left
that clause alone, so the honest statement of coverage today is: every test in the file maps to a
scenario or to a surface element, and five of them pin a property this contract does not yet state.

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

The whole set is verified end to end, measured 2026-07-29: all nineteen skills pass Anthropic's
`quick_validate.py`, 19 of 19, alongside this repository's own validator reporting 0 errors and 0
warnings. Dated because the denominator moves whenever a skill is added, and an undated count reads as
a claim about now rather than as the record it is.

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
