---
title: validate-skills conformance
spec: docs/spec/validate-skills.md
audited: 2026-07-27
supersedes: 2026-07-24 audit (S-001 through S-008 only)
re_audited: 2026-07-28 (feat-0032), 2026-08-19 (chore-0039), 2026-08-20 (chore-0047), 2026-08-20 (bug-0040), 2026-08-21 (chore-0036)
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
| Scenarios | S-014 contradictory status claim warns | Conformed | `check_status_contradiction()` with the widened `DRAFT_STATUS_RE` and `SHIPPED_STATUS_RE` | diverged when first audited on 2026-07-27 and was fixed the same day. The patterns now cover assertion forms (`is`/`remains`/`stays` a draft, a `status: draft` line, `draft pending`) and provenance forms (a `shipped`/`blessed` list item, or either word before an ISO date). Re-probed against the five phrasings that produced the original finding: all five flag. Four negative cases produce no finding, including prose that merely discusses drafts and a skill whose `status: draft` refers to a spec it authors rather than to itself. |
| Scenarios | S-015 skills directory does not exist | Conformed | `main()` / `if not skills_dir.is_dir()` guard | prints the missing-directory error and returns 1; confirmed by execution (exit 1, `ERROR no skills directory at ...`) |
| Scenarios | S-016 skills directory exists but is empty | Conformed | `main()` / `if not skills:` guard after `skills_dir.iterdir()` | prints `No skills found under ...` and returns 0; confirmed by execution (exit 0) |
| Scenarios | S-017 description over the harness limit fails | Conformed | `main()` / `elif len(desc) > MAX_DESC_CHARS` branch, with `MAX_DESC_CHARS = 1024` | appends to `errors`, so the run exits non-zero; the message carries both the measured length and the limit. Confirmed by execution against a copy of the real skills tree with one description padded over the bound: exit 1, `description is 1173 chars, over the 1024-char limit`. The boundary is `>`, so a description of exactly 1024 produces no finding |
| Scenarios | S-018 description measured by value, not YAML syntax | Conformed | `parse_frontmatter()` / `BLOCK_SCALAR_RE.sub("", value, count=1)` on the field-line branch | the indicator is stripped at the head of the field line only and once, so `>`, `>-`, `>+`, `\|`, `\|-`, and `\|+` are removed while a plain scalar and any angle bracket inside the prose are untouched. The four block-scalar descriptions in the kit each measure 3 fewer characters than before the fix, which is the defect this closes |
| Scenarios | S-019 unparseable frontmatter fails | Conformed | `check_frontmatter_is_parseable()`, called from `main()` after `check_links()` | errors on a plain unquoted scalar containing `": "` or ending in `":"`, and skips a block scalar or a fully quoted value. Confirmed by execution: a copy of the real `.agents/` tree with `house-review`'s description put back into the single-line plain form that shipped exits 1 with the nested-mapping error. The message states that it checks one known construct rather than YAML validity, which is the honest limit of a standard-library check |
| Scenarios | S-020 angle bracket in a description fails | Conformed | `main()` / the `if desc and ("<" in desc or ">" in desc)` branch | reads the parsed value, so the twelve block-scalar descriptions are not flagged for the `>` in their own indicator. `human-handoff` was violating this in the field and is fixed |
| Scenarios | S-021 unrecognised frontmatter property fails | Conformed | `main()` / the `for key in sorted(set(fm) - ALLOWED_FRONTMATTER_KEYS)` loop, with the `ALLOWED_FRONTMATTER_KEYS` constant | an allow-list of the schema's six properties, commented with its source and the date it was read. `version` is deliberately excluded: the reference implementation rejects it even though Anthropic's own example skill documents it as optional |
| Scenarios | S-023 a self-declared lens no skill references fails | Conformed | `check_lenses_are_composed()`, called from `main()` after the per-skill loop with `portable_root / "rules"` and the `skill_texts` dict `main()` accumulates; declaration by `declares_itself_a_lens()` over `LENS_DECLARATION_RE` and `LENS_DECLARATION_LINES` | added by `chore-0047`, writing down what `feat-0048` built. One error per unreferenced lens, not one per skill, because the call sits outside the loop. A reference is `_names_file_outside_fences(skill_text, rules_file.name)`, so a relative link and a prose mention naming the file both satisfy it and the bare subject word does not, which is what the scenario states. The declaration is read only in the opening (10 lines), keyed to a self-declaration rather than a filename list, so the rule fires for the next lens too. Re-measured 2026-08-20 (`bug-0040`): 3 files in `.agents/rules/`, all 3 declare themselves lenses inside the window, and all 3 are referenced, by 20, 5 and 4 skills respectively, unchanged by the fence guard, so the rule reports nothing today and is a guard rather than a live exclusion. **The asymmetry the `chore-0047` audit recorded here is closed** and no longer appears in this row: a body whose only mention of a lens filename sits inside a fenced block no longer satisfies the rule, which is the same refinement S-022 makes for the link rules. **S-023's wording is unchanged and still holds**: the scenario says the filename appears in a `SKILL.md`, and the fence guard changes which appearances count rather than what the scenario asserts, exactly as S-022 does for S-009 through S-013. The guard stops at fences and does not extend to inline code spans, argued in the extension note above |
| Proposed Surface | Invocation `python scripts/validate-skills.py` | Conformed | module `__main__` guard | `if __name__ == "__main__": raise SystemExit(main())` |
| Proposed Surface | What it reads: skills plus the sibling rules module | Conformed | `main()` / `portable_root = skills_dir.parent.resolve()` and the `check_lenses_are_composed(portable_root / "rules", ...)` call | added by `chore-0047`. `portable_root` already existed to serve the S-011 portability guard; the lens rule is the first use that reads a file under it. Nothing outside the skills directory and its sibling `rules/` is opened. Re-derived 2026-08-21 (`chore-0036`): still conformed, and the surface sentence "every skill directory under the target skills directory" is now true of the whole directory rather than of its `SKILL.md` alone. `check_supporting_files()` walks each skill directory and opens the markdown it finds there, which is inside the pair this element names, so the boundary the element draws is unmoved. The wording is nonetheless weaker than it reads, because it was written when only one file per directory was ever opened; the amendment owed below asks for it to say so |
| Proposed Surface | Exit non-zero on error only | Conformed | `main()` / final `return 1 if errors else 0` | warnings do not affect the exit code |
| Proposed Surface | Output format | Diverged | spec: the `Proposed Surface` "Output" row; code: `main()` / the second `print` following the `Checked ...` summary print | the contract states the run ends at the `Checked N skill(s): E error(s), W warning(s).` summary. `chore-0036` prints a further line, `Link-checked N supporting file(s) beside them; skipped ... template(s) ... and ... non-markdown file(s).`, on every run that reaches the summary. Everything the element does state is unchanged: the `WARN`/`ERROR` loops, the summary line itself verbatim, and the two early-return prints that replace it. The divergence is an addition the contract does not mention, not a contradiction of anything in it |

## Coverage proof

- **audited**: S-001 through S-023, and all four Proposed Surface elements (invocation, what it
  reads, exit code, output format). Every spec item was checked. S-022 is numbered after S-021 and
  placed beside S-013 in both documents, because it is the exception the link rows are read against.
  S-023 is placed last in both, because it is the only rule whose subject is not a skill and it is
  read against nothing above it.
- **re-derived in the 2026-08-21 (`chore-0036`) pass**: two Proposed Surface elements only, `Output
  format` and `What it reads`. The twenty-three scenario rows and the other two surface elements are
  carried forward from the passes named in the header, unchanged and not re-checked. Stated because a
  partial audit is not a whole one. They are safe to carry because the change added two functions no
  row cites and left every branch and message body of `check_links()`, the one function any row
  cites, as it was.
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
  - **Output format (Diverged)**, and the supporting-file rule behind it: disposition **amend the
    spec**. `chore-0036` gave the validator a rule this contract states nowhere: the markdown a skill
    ships beside its `SKILL.md` is link-checked under the same three rules S-009 through S-013 carry,
    resolved from where the supporting file sits, and a file whose name ends in `.tmpl` is excluded
    because its links are authored for the repository it is written into. The run reports the checked
    and skipped counts on a second summary line. **No scenario is claimed for it here**, deliberately:
    `chore-0036` declares `scenarios: []`, its tests are characterization rather than acceptance, and
    inventing an id at closeout would let a matrix assert coverage of a contract clause nobody wrote.
    What is owed is one scenario in the spec (the sibling of S-009 for a supporting file, with the
    `.tmpl` exclusion and the `../<name>/SKILL.md` shortcut being off for such a file), a widened
    `Output` element, and a `What it reads` element that says the whole skill directory rather than
    leaving "every skill directory" to be read as its `SKILL.md`. Until then the rule is pinned only
    by `TestSupportingFileLinkChecks` in
    [`tests/test_validate_skills.py`](../../tests/test_validate_skills.py), which is the same position
    S-022 and S-023 were in before `chore-0039` and `chore-0047` wrote them down.

S-014 was the second unreconciled item when this matrix was first regenerated on 2026-07-27, carrying
disposition **fix**. The author chose to widen rather than to narrow the scenario, the patterns were
widened the same day, and the row above is the re-audit. It is recorded here rather than erased
because the divergence is the useful part of the history: the check had shipped on 2026-07-25, was
believed correct for two days, and was only caught when a scenario was written that stated the
condition semantically instead of restating the implementation.

No spec item was silently dropped. Two items diverge: S-008, accepted with a stated reason, and the
`Output format` element, which awaits the amendment named above. Everything else conforms.

## Test coverage of spec invariants

Flagged per `spec-conformance`'s non-goal (it does not write tests, but does say where an invariant
lacks one). Against [`tests/test_validate_skills.py`](../../tests/test_validate_skills.py):

| Scenario | Covering test | Note |
|---|---|---|
| S-009 through S-013 | present | one test each, plus negative cases for S-010 and S-012, each tagged with its scenario id |
| S-022 | present | added by `bug-0027`, six tests in `TestLinkChecksInsideCodeSpansAndFences`. Two positives, a fenced link and an inline span in both the single and the double backtick form. The negatives carry the weight, since the cheap way to remove a false positive is to switch the check off: a genuine broken link beside a *closed* fence and one below an *unterminated* fence must both still be reported. A fifth asserts the escape rule S-011 is skipped inside a fence too, which is the decision this scenario records rather than an accident, and a sixth runs `check_links()` over the real tree, so the exclusion is shown not to have changed what the kit's own skills report. **The tests predate the id**: written when no scenario stated the rule, they are tagged `Scenario S-009 refined` and their docstrings describe the amendment as the author's open call. That call is now made, so the tags are stale in one direction only, naming less than they cover; retagging them is `chore-0045`'s follow-up and deliberately not done here |
| S-014 | present | table-driven over all five contradiction phrasings and four negative cases. Confirmed to fail on four of the five against the pre-fix patterns, which is the bug population; the canonical phrasing always passed and proves nothing on its own, which is exactly how the original single-case test hid the divergence |
| S-015, S-016 | present | added 2026-07-27 once the contract was approved. Asserts the pair together: the absent directory must fail and must not report `Checked 0 skill`, the empty one must succeed |
| S-017 | present | two tests: over the limit errors with the measured length in the message, and exactly at the limit does not, so an off-by-one that rejected a legal description would fail |
| S-020, S-021 | present | added by `bug-0008`. Five tests: an angle bracket errors, a block-scalar description is not flagged for its own indicator, an unrecognised key (`version`) errors, all six permitted properties together pass, and both rules hold across the real nineteen. The two negative cases are the ones that keep the checks usable: flagging a block scalar would fail twelve valid skills, and rejecting a legal property would fail a valid skill while looking like a kit bug |
| S-019 | present | added by `bug-0007`. Six tests: the two positive constructs (a colon-space inside a plain scalar, and a value ending in a colon), three negative cases that must not fire (a block scalar, a quoted value, and a URL whose colon has no following space), and one that runs the check over all nineteen shipped skills, which is the assertion that would have caught the defect. The negative cases carry the weight: a false positive would push authors to contort a description to satisfy a checker rather than a parser |
| S-018 | present | three tests: a block scalar whose text is exactly at the limit must pass (it measured 3 over before the fix), every indicator form strips at the parser layer, and two negative cases hold, a plain scalar and prose containing angle brackets. The negative cases are the load-bearing ones, because over-eager stripping shortens a description silently instead of failing |

| S-023 | present | added by `feat-0048` and extended by `bug-0040`, twelve tests in `TestLensComposition`. Three positives, a declared lens with no inbound reference, one whose only mention is the bare subject word, and one whose only mention sits inside a fenced block, all of which must error. The other nine are negatives, and they carry the weight for the reason the class docstring gives: this rule reads files nobody asked it to lint, so a false positive lands on a document whose author never opted into being a lens and the cheap response is to delete the rule. They cover a referenced lens by link, a reference by prose naming the file, a plain rules document that never declares itself, and a declaration below the opening window. `bug-0040` added two more of the same shape, and they are the ones that keep the fence guard from switching the rule off: a genuine reference beside a *closed* fence and one below an *unterminated* fence must both still count, which is the pair S-022's tests already carry for links. The reference-by-prose test doubles as the pin on the span decision, since its fixture names the file inside an inline code span and must still pass. The last three run against the real tree: the opening window clears every shipped lens with margin (bounded in both directions rather than asserted as a bare number, per `bug-0026`), every shipped lens is composed, and `autonomy.md` is referenced by exactly the five skills it cites, no more and no fewer. **Nine of the twelve predate the scenario id**, as S-022's tests did: they are tagged `feat-0048` rather than `S-023`. `bug-0040`'s three are tagged `Scenario S-023` and did not retag their neighbours, so the gap is narrower than it was and still open. `chore-0045` item 4 makes exactly this correction for S-022 and does not cover S-023, which postdates it, so the S-023 retag remains a follow-up rather than an already-filed one |

Every scenario except S-008 now has a covering test, including the code-span rule that had tests
before it had a scenario. S-008 remains deliberately untested, because a
passing test there would assert behavior the accepted divergence says does not exist.

**Thirteen tests in the file cover no scenario in this contract**, and that is stated here rather
than left for a reader to notice a table row missing. `TestSupportingFileLinkChecks` pins the
supporting-file rule `chore-0036` added on 2026-08-21, tagged as characterization and carrying no
S-NNN id because no scenario states the rule; the amendment owed is in the unreconciled section
above. They are the same shape as the rest of the link tests, positives for an unresolved link, an
escaping link, and the sibling-shortcut false negative, and negatives for the exclusions, a `.tmpl`
file, a non-markdown file, a byte cache, and a link inside a fence. Measured 2026-08-21 against the
pre-change script: 8 fail and 2 error, which is what makes them tests of the change rather than a
restatement of it. The other 3 pass on both sides, which is what a negative case should do and is why
they are not counted as evidence of the change: a supporting file whose links resolve, a `.tmpl` file
that must not be read, and a non-markdown file that must not be read.

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
