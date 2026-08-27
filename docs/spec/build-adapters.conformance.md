---
title: build-adapters conformance
spec: docs/spec/build-adapters.md
audited: 2026-07-27
re_audited: 2026-07-27 (chore-0015), 2026-08-06 (feat-0034), 2026-08-19 (chore-0043),
  2026-08-22 (bug-0044, partial: S-009 and S-016 only),
  2026-08-27 (chore-0062, partial: S-019 only),
  2026-08-27 (chore-0068, partial: S-009, S-010, S-011, S-012, S-014, S-016 and the
  Emitted shared paths surface row only),
  2026-08-27 (chore-0045, partial: the S-018 test-coverage row only)
---

# build-adapters conformance matrix

Spec-vs-implementation audit of [`scripts/build-adapters.py`](../../scripts/build-adapters.py)
against [`build-adapters.md`](build-adapters.md). Evidence is by code location; this audit is
independent of test pass/fail.

Re-audited after `chore-0015` amended the contract to classify the two kinds of emitted shared
material. The "behavior found outside the contract" section this matrix carried is **retired**: the
behavior it described is now S-014.

Re-audited 2026-08-06 after `feat-0034` amended the contract with the `plugin` target, S-015 through
S-017. That amendment is itself **pending the author's re-approval**, which is stated in the spec's
header and repeated here so this matrix is not read as auditing an approved contract in full: the
three new rows audit code against paragraphs the author has authorized but not yet re-approved.

Re-audited 2026-08-19 after `chore-0043` amended the contract with S-018, the code-span and fence
exception `bug-0028` had already given `rewrite_links()` on 2026-08-18. That amendment is likewise
**pending the author's re-approval**, stated in the spec's header and repeated here for the same
reason. The six rewrite rows S-003 through S-008 were re-audited against the current function in the
same pass and all six remain `Conformed`: none of their branches changed, and each is now reached
only for a link the span and fence guard let through.

Re-audited 2026-08-22 by `bug-0044`, and **partially**: only `S-009` and `S-016` were re-checked,
because those are the two scenarios that task declares. Every other row below carries its previous
audit date and was not looked at in this pass. Both rows keep their `Conformed` classification, and
the reason they do is the finding: **the contract has no scenario about a rules file's own outbound
links**, so the defect `bug-0044` fixed diverged from nothing. `S-009` is a claim about the targets a
rewritten *skill body* points at, and its evidence holds unchanged. `S-016` is scoped to the plugin
target, where the geometry already resolved every one of these links, which is a large part of why
the defect survived a matrix that reports full coverage. The gap was in the contract rather than in
the audit of it, and what is owed is recorded in the coverage proof below rather than fixed by
amending the spec here, which `bug-0044` puts out of scope for the same reason `chore-0043` was a
separate chore.

Re-audited 2026-08-27 by `chore-0062`, and **partially**: only `S-019` was audited, because it is the
one scenario that task adds and the only one it declares. Every other row below carries its previous
audit date and was not looked at in this pass. That chore is the amendment `bug-0044` recorded as
owed, so the unreconciled item below moves from one back to none: the gap was a missing contract
sentence, and the sentence now exists as S-019. The behaviour it audits did not change in this pass
and no file under `scripts/` or `tests/` was touched. That amendment is **pending the author's
re-approval**, stated in the spec's header and repeated here for the same reason the paragraphs above
give: the row for `S-019` audits code against a paragraph the author has authorized but not yet
re-read.

Re-audited 2026-08-27 by `chore-0068`, and **partially**: six scenarios, `S-009`, `S-010`, `S-011`,
`S-012`, `S-014` and `S-016`, plus the `Emitted shared paths` surface row. Those seven are exactly the
rows whose evidence named the single function `bug-0025` split into `emit_rules_module()` and
`emit_skill_assets()` on 2026-08-08, so every one of them cited a symbol that no longer exists. That
dead name is deliberately not written anywhere in this document, not even to describe its own removal:
a name that resolves nowhere is what this pass exists to take out, and a checker of the kind
`chore-0049` proposes should find no occurrence here to have to reason about. `bug-0025`'s record
carries it. Every other row below carries its previous audit date and was not looked at in
this pass. Two passes now share the date 2026-08-27 and they are not one pass: `S-019` belongs to
`chore-0062` and this pass did not touch it.

Each of the seven was re-derived against the function that now holds its evidence **before** its
citation was moved, because the split could have carried behaviour from one half to the other, and a
repointed citation nobody re-checked would read as audited while asserting a freshness it had not
established. That is why `chore-0062` declined to repair them. **All seven keep their `Conformed`
classification**, and the confirmation is by execution on 2026-08-27 rather than by reading alone: a
preview into an empty root wrote 0 files and reported the same 17 shared assets a real run into that
root then wrote (S-012); a run into the kit itself reported 0 (S-011); editing one emitted rules file
and one emitted skill asset and re-running preserved the first and replaced the second, reported as 14
rather than 17 (S-010, S-014); the 40 emitted adapters carried 66 rewritten links into `.agents/rules/`
and 16 into `.agents/skills/` with 0 dangling against the 17 files emitted there (S-009); and a plugin
tree resolved 128 relative links with 0 dangling and 0 leaving the root (S-016).

The split moved no behaviour, and it left one row more legible: `S-014` asserts a contrast between a
guarded rules copy and an unguarded skill-asset copy, and that contrast is now two functions rather
than two loops inside one. Two rows were stale in a way the function name alone did not show, and both
are corrected here. The `S-009` note read "called per skill from `main()`", which describes the call
site `bug-0025` removed: the rules half now runs once per distinct layout, hoisted out of the
per-skill loop, and only the skill-asset half is still per skill, so correcting the name alone would
have left the misdescribed mechanism in place. And `S-012`'s evidence covered only the first half of
its Then; the second half is the half `bug-0025` exists for, and that row's own history is now in its
note.

Re-audited 2026-08-27 by `chore-0045`, and **partially**: one row, the `S-018` row in the test
coverage section below. That task retags `TestRewriteLinksInsideCodeSpansAndFences` and all five of
its cases from the scenarios they refine to `S-018`, and deletes the paragraph in its class docstring
calling the amendment the author's open call, so this row's closing sentence described a state the
same change removed. No scenario row was re-derived and no file under `scripts/` was touched; every
row in the matrix proper carries its previous audit date. Three passes now share the date 2026-08-27
and they are three: `S-019` belongs to `chore-0062`, the seven rows citing `bug-0025`'s split belong
to `chore-0068`, and this pass looked at neither.

That row was re-derived against the retagged file **before** its citation moved, per the disposition
`chore-0062` and `chore-0068` both recorded. It keeps `present`, and the re-derivation found one
claim wrong independently of the retag: the row said all five tests run against both inlining
extensions, and four of them do. The fifth targets the plugin, which inlines nothing and has no
extension to vary, which is the reason for having it. Corrected in the row rather than left standing.

The reach of the new rule was measured rather than asserted, which is what makes it checkable. Across
the twenty shipped `SKILL.md` bodies, `bug-0028` measured 131 links matched by `LINK_RE` and 0 newly
suppressed by the guard, so every generated adapter is byte-identical before and after the fix.
Re-measured against this commit on 2026-08-19: 20 bodies, 133 links matched, 0 of them inside a code
span or a fence. The count moved from 131 because `bug-0032` added two links to
`test-author/SKILL.md` when it wrote the spec-approval gate, measured per body across
`e492b10..b950c9e`; `feat-0048` is still open and no skill references `autonomy.md`. And the second number is the load-bearing one: the exception currently fires on
nothing in this kit. It is a guard against a body that shows a link as an example, which the
documentation skills are the likeliest to want, rather than a rule with live occurrences today. A
matrix row asserting "conformed" without that number would not distinguish a working guard from a
dead one.

S-002 re-audited 2026-07-28 (`bug-0006`) and found diverged, the first divergence this contract has
recorded. It is worth reading the row for how it hid: `bug-0001` had already fixed a defect in the same
field, JSON-serialising the description so a colon or quote could not break the adapter's own
frontmatter. That made the output well-formed, which is what both the tests and a reader check, so the
remaining defect became valid YAML holding the wrong value. The pre-existing S-002 test asserted that
`description:` was present, never what followed it.

First audit of this contract, produced immediately after its approval (`feat-0026`). Because the spec
is retrospective, written against an implementation that already existed and was verified, a clean
matrix here is weaker evidence than a clean matrix on a contract written first: the spec was authored
by reading the same code it audits. Its value was therefore concentrated in what it found outside the
scenarios, which was the shared-asset re-run behavior: unstated at the time, and now S-014.

## Matrix

| Section | Item | Status | Evidence | Note |
|---|---|---|---|---|
| Scenarios | S-001 one adapter per skill per requested target | Conformed | `main()` / the `for d in skills` loop over `targets`, with the summary print and `return 0` | only requested targets are dispatched, via `EMITTERS[t]` |
| Scenarios | S-002 harness frontmatter and do-not-edit banner | Conformed | `emit_cursor()` and `emit_vscode()` content strings, with `BANNER`, and `split_frontmatter()` / `BLOCK_SCALAR_RE.sub("", value, count=1)` | cursor gets `description` plus `alwaysApply: false`, vscode gets `mode: agent` plus `description`; both prepend the banner naming the source `SKILL.md`. **Diverged when re-audited 2026-07-28 and fixed the same day (`bug-0006`)**: `split_frontmatter()` captured a YAML block-scalar indicator as part of the value, so the four skills writing `description: >-` emitted `description: ">- Turns ..."`, eight of the 38 files a full run produces. The scenario says the adapter opens with the skill's `description`, and that string is the scalar's serialisation rather than its value, so the contract already covered it and no amendment was needed |
| Scenarios | S-003 sibling link points at the adapter beside it | Conformed | `rewrite_links()` / `SIBLING_RE` branch | emits `<sibling><ext>`, a same-directory reference. Re-audited 2026-08-19 (`chore-0043`): unchanged, and now reached only for a link outside every code span and fence (S-018) |
| Scenarios | S-004 anchor survives the rewrite | Conformed | `rewrite_links()` / `SIBLING_RE` branch, `sibling.group(2)` | the captured anchor is reattached. Re-audited 2026-08-19 (`chore-0043`): unchanged, and now reached only outside a code span or fence (S-018) |
| Scenarios | S-005 link title survives the rewrite | Conformed | `rewrite_links()` / `LINK_RE` group 2, reattached by the inner `out()` | the title is carried through every rewrite path, not just the sibling one. Re-audited 2026-08-19 (`chore-0043`): unchanged, and now reached only outside a code span or fence (S-018) |
| Scenarios | S-006 rules-module link points at the shared location | Conformed | `rewrite_links()` / `RULES_RE` branch, with the `SHARED` prefix | Re-audited 2026-08-19 (`chore-0043`): unchanged, and now reached only outside a code span or fence (S-018) |
| Scenarios | S-007 skill-local asset points at the shared location | Conformed | `rewrite_links()` / the final return, `SHARED/skills/<name>/<target>` | reached only after the span and fence guard (S-018) and then the external, anchor, sibling, rules and escaping branches. Re-audited 2026-08-19 (`chore-0043`): unchanged, with the guard now first in that order |
| Scenarios | S-008 external and same-page links unchanged | Conformed | `rewrite_links()` / the `target.startswith("#")` and `EXTERNAL_PREFIXES` guard returning `m.group(0)` | returns the original match object's text, so the link is byte-for-byte preserved. Re-audited 2026-08-19 (`chore-0043`): unchanged. S-018 now sits ahead of it and governs a different question, whether the text is a link at all, where this row governs the link's kind |
| Scenarios | S-018 a link that renders as literal text is not a link | Conformed | `rewrite_links()` / `spans = code_span_ranges(body) + fenced_block_ranges(body)` and the `any(start <= m.start() < end ...)` guard at the top of `repl`, returning `m.group(0)`; the two helpers `code_span_ranges()` and `fenced_block_ranges()` above it | added by `chore-0043`, writing down what `bug-0028` built. The guard is keyed to the position of `](`, the bracket closing the link *text*, so a link whose text is itself a code span is still rewritten, which is how nearly every link in this kit is written. The ranges are computed once per body rather than once per match, because `re.sub()` calls the replacement for every match. An unterminated fence yields no range, so it suppresses nothing below it. Confirmed by measurement against this commit: 20 shipped bodies, 133 links matched, 0 inside a span or fence, so no adapter changes today and the row is a guard rather than a live rewrite |
| Scenarios | S-009 the material the links point at is emitted | Conformed | `emit_rules_module()` / its `shutil.copy2(src, dest)` loop over `RULES_DIR`, called once per distinct layout from `main()`; and `emit_skill_assets()` / its `shutil.copy2(src, dest)` loop, called once per skill per distinct layout | rules module and each skill's non-`SKILL.md` files. Re-audited 2026-08-27 (`chore-0068`), which is where the citation moved: the behaviour is unchanged and now spans the two functions `bug-0025` split the original one into. **The note this replaces was stale twice over.** It read "called per skill from `main()`", which is the call site `bug-0025` removed on 2026-08-08: the rules half ran once per skill and short-circuited on `dest.exists()` from the second skill onward, and it is now hoisted out of the per-skill loop and runs once per distinct layout. Only the skill-asset half is still per skill. Re-confirmed by execution: a default run into an empty root emits 17 shared files, and its 40 adapters carry 66 rewritten links into `.agents/rules/` and 16 into `.agents/skills/`, 0 dangling |
| Scenarios | S-019 every relative link inside an emitted lens resolves | Conformed | `emit_rules_module()` / the `shutil.copy2(src, dest)` copy loop, which passes no body through `rewrite_links()`, and its docstring's `bug-0044` paragraph recording that as a decision; and the source lenses under `.agents/rules/`, whose only relative links are sibling-lens links resolving inside the module's own directory | added by `chore-0062`, writing down what `bug-0044` built on 2026-08-22. The layout, not a rewrite, is what makes these resolve, the same shape as S-016: a lens's siblings sit beside it in every layout, so one link text is correct in all of them and no per-target case exists. Confirmed by execution on 2026-08-27 across all four distribution paths, each emitted into a directory of its own: `--target cursor`, `--target vscode`, `--target plugin`, and an `install.py --home <tmp> --mode copy --profile all` run, which places the module twice, once per tool, at `.claude/rules/` and `.agents/rules/`. Five relative links per emitted module in every one of those five directories, three lenses walked each time, **0 dangling**. The adopter residual is not closed and is stated in the scenario: an existing rules file is preserved unread (S-010, S-014), so a copy taken before the links were corrected keeps them and no run says so |
| Scenarios | S-010 an existing rules file is never overwritten | Conformed | `emit_rules_module()` / the `or dest.exists()` half of its skip guard | confirmed by execution: an edited rules file survives a re-run unchanged. Re-audited 2026-08-27 (`chore-0068`): the guard travelled into `emit_rules_module()` with `bug-0025`'s split and is otherwise unchanged, and it is the whole of this scenario's evidence, because `emit_skill_assets()` deliberately carries no counterpart (S-014). Re-confirmed by execution on that date: an emitted rules file edited by hand kept its content across a re-run |
| Scenarios | S-014 a re-run refreshes derived assets and preserves adopted ones | Conformed | `emit_rules_module()` / the `or dest.exists()` half of its skip guard, contrasted with `emit_skill_assets()`, whose skip is `dest.resolve() == src.resolve()` and nothing more | added by `chore-0015`. Confirmed by execution: after editing both and re-running, the rules file kept its content and the skill template was replaced by the kit's version. Re-audited 2026-08-27 (`chore-0068`): neither guard changed, and `bug-0025`'s split made this row's contrast two functions rather than two loops in one, which is more legible rather than less. Re-confirmed by execution on that date, where the asymmetry shows in the count as well as in the files: a second run into the same root reported 14 shared assets rather than 17, the three rules files skipped and the fourteen derived assets rewritten |
| Scenarios | S-011 generating into the kit is a no-op | Conformed | `emit_rules_module()` / `dest.resolve() == src.resolve() or dest.exists()` and `emit_skill_assets()` / `dest.resolve() == src.resolve()`, the same-file test in each | confirmed by execution: a run against the repo root reports `plus 0 shared asset file(s)`. Re-audited 2026-08-27 (`chore-0068`): `bug-0025`'s split left the same-file guard in each function rather than twice in one, and both halves of the Then still hold, since a skipped file is also one never appended to the returned list `main()` sums. Re-confirmed by execution on that date |
| Scenarios | S-012 a preview run writes nothing | Conformed | `_write()` / its `if dry:` early return, `emit_plugin()` / its `if dry:` early return of an unwritten `dest`, and the `if not dry:` guards in `emit_rules_module()` and `emit_skill_assets()`; and, for the count half of the Then, `main()` / its `assets` accumulator, a `sum()` over `layouts` calling `emit_rules_module()` once per distinct layout, hoisted out of the per-skill loop | confirmed by execution: zero files written into a temp root. Re-audited 2026-08-27 (`chore-0068`), and this is the row the re-derivation changed most, because **its Then has two halves and the evidence named only the first**. Nothing writes on a preview, and that held throughout. The second half, that the reported counts describe what would have been produced, was false when this row was first audited on 2026-07-27 and nothing in the row named it: a preview counted the rules module once per skill and reported 74 shared assets against the 17 a real run writes, which `bug-0025` measured and fixed on 2026-08-08 with the hoist now cited above. The verdict is correct today and the evidence now covers both halves rather than one. Re-confirmed by execution on 2026-08-27: a preview into an empty root wrote 0 files and reported the same 17 shared assets a real run into that root then wrote |
| Scenarios | S-013 an unrecognized target is rejected | Conformed | `main()` / the `bad` check returning 2 | the check precedes any emission, so nothing partial is written; confirmed by execution (exit 2, zero files) |
| Scenarios | S-015 the plugin target emits an installable plugin tree | Conformed | `emit_plugin()` / `dest = out / "skills" / src.name / "SKILL.md"`, and `emit_plugin_manifests()` / the `marketplace` literal and the `for fname, obj in ...` write loop, dispatched from `main()` by `if "plugin" in targets` | added by `feat-0034`. Both manifests are derived from the single `PLUGIN` mapping, so the marketplace entry cannot name a plugin other than the one emitted beside it. The destination uses `src.name`, the source *directory* name, because `../<dir>/SKILL.md` is what a sibling link names. Confirmed by execution: `claude plugin validate --strict` passes against the generated tree |
| Scenarios | S-016 nothing in an emitted plugin tree points outside it | Conformed | `LAYOUTS` / its `"plugin": Layout("rules", "skills")` entry, consumed by `emit_rules_module()` / `out / layout.rules_dir` and `emit_skill_assets()` / `out / layout.assets_dir`; and `emit_plugin()`, which copies the source `SKILL.md` verbatim and calls no rewriter | added by `feat-0034`, and the reason the target exists. The layout, not a rewrite, is what makes the links resolve: `skills/<name>/` reaching `../../rules/<file>` lands on `rules/<file>`, the same geometry `.agents/skills/<name>/` has to `.agents/rules/<file>` with the `.agents/` parent dropped. Confirmed by execution: 117 relative links resolved on disk from the emitted root, none broken and none leaving it, with one copy of `review-quality.md` at `rules/review-quality.md`. Confirmed to **fail** when the plugin layout is given the inlining targets' `.agents/rules`, which dangles all 28 rules links, so it is an oracle over the layout decision rather than a restatement of it. Re-audited 2026-08-27 (`chore-0068`): the two `dest` expressions now sit in the two functions `bug-0025` split the original one into, neither changed, and the layout rather than a rewrite is still what makes the links resolve. Re-measured by execution on that date, resolving each link from the directory of the skill holding it: 128 relative links, 0 dangling and 0 leaving the plugin root, still exactly one copy of `review-quality.md` at `rules/review-quality.md` |
| Scenarios | S-017 the plugin target is opt-in | Conformed | `main()` / the `--target` `default="cursor,vscode"`, and the `if "plugin" in targets` guard on `emit_plugin_manifests()` | added by `feat-0034`. Confirmed to **fail** when `plugin` is added to the default, which also breaks the pre-existing S-011 test, since a default run into the kit would then write `rules/` and `skills/` trees the no-op guard does not cover |
| Proposed Surface | Invocation and its three flags | Conformed | `main()` / the `argparse` definitions for `--target`, `--out`, `--dry-run` | `--target` defaults to `cursor,vscode` and `--out` to the working directory. Amended by `feat-0034`: the default is the two inlining targets rather than every supported one, per S-017 |
| Proposed Surface | Emitted per-skill paths | Conformed | `emit_cursor()`, `emit_vscode()` and `emit_plugin()` `dest` expressions | `.cursor/rules/<name>.mdc`, `.github/prompts/<name>.prompt.md`, `skills/<name>/SKILL.md` |
| Proposed Surface | Emitted per-plugin-run paths | Conformed | `emit_plugin_manifests()` / `dest = out / ".claude-plugin" / fname` | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, written once per run rather than per skill |
| Proposed Surface | Emitted shared paths | Conformed | `emit_rules_module()` / `dest = out / layout.rules_dir / src.relative_to(RULES_DIR)` and `emit_skill_assets()` / `dest = out / layout.assets_dir / skill_dir.name / rel`, with the distinct-layout loop in `main()` | `.agents/rules/<file>` and `.agents/skills/<name>/<path>` for the inlining targets, `rules/<file>` and `skills/<name>/<path>` for the plugin. `cursor` and `vscode` share one layout, so requesting both still emits one copy. Re-audited 2026-08-27 (`chore-0068`): both `dest` expressions survive `bug-0025`'s split unchanged, one to each function, and the emitted paths are identical. What did change is the mechanism behind that last sentence, recorded because the surface it describes did not move: one copy used to be the *result* of the rules loop running once per skill and short-circuiting on `dest.exists()` after the first, and it is now produced by construction, since `Layout` is a namedtuple and `LAYOUTS["cursor"] == LAYOUTS["vscode"]`, so the dedupe in `main()` yields a single `emit_rules_module()` call. Confirmed by execution on that date: a default `cursor,vscode` run emits exactly three files under `.agents/rules/` |
| Proposed Surface | Exit code | Conformed | `main()` / `return 2` for a bad target, `return 0` otherwise | |
| Proposed Surface | Output | Conformed | `main()` / the per-emission print, the manifest print, the closing summary and its manifest-count line | the summary names the shared roots actually written, so a plugin run reports `under rules/, skills/.` where an inlining run reports `under .agents/.` |

## Coverage proof

- **audited**: the spec now carries 19 scenarios and six Proposed Surface elements, and every one of
  the 25 items has a row below. The arithmetic, stated rather than asserted: the 2026-08-19 pass
  checked all 18 scenarios then in the spec plus all 6 surface elements, 24 items; `chore-0062` adds
  `S-019` and audits it; 18 + 1 = 19 scenarios, and 19 + 6 = 25 rows. S-018 is numbered
  after S-017 and placed beside S-008 in both documents, because it is the exception those rewrite
  rows are read against; `S-019` is numbered after S-018 and placed beside S-009 for the same kind of
  reason, since it is the outbound half of the pair S-009 opens.
- **not re-audited in this pass**: 13 of the 19 scenarios and 5 of the 6 surface elements. The
  `chore-0068` pass re-audited **6 scenarios**, `S-009`, `S-010`, `S-011`, `S-012`, `S-014` and
  `S-016`, plus **1 surface element**, `Emitted shared paths`, which are the seven rows that cited the
  function `bug-0025` removed, and nothing else. The arithmetic, stated rather than asserted:
  19 - 6 = 13 scenarios and 6 - 1 = 5 surface elements stand on the dates they carry and are not
  re-asserted here, and 6 audited now + 13 standing = 19, which is the whole scenario set and is the
  only sense in which this document covers it. Two passes share the date 2026-08-27 and they are
  distinct: `chore-0062` audited **1**, `S-019`, and this pass did not look at it. The 2026-08-22 pass
  re-audited **2**, `S-009` and `S-016`, and this pass re-derived both again, because both cited the
  removed function and neither that pass nor its date is what made the citation stale.
- **unreconciled**: none. The single item this section carried from 2026-08-22 is now closed rather
  than dropped, and it is worth saying how, because it was a contract gap presenting as a clean
  matrix. It read: **no scenario states what a file in the rules module may link to**, since every
  link rule here, `S-003` through `S-008` and `S-018`, is about a *skill body* passing through
  `rewrite_links()`, `S-009` covers the targets those rewritten links land on, `S-010` and `S-014`
  cover the module's placement and its survival across a re-run, and `S-016` covers escape and only
  for the plugin target. That is how seven `../skills/<name>/SKILL.md` links shipped dangling in every
  emitted cursor and vscode tree while this matrix honestly read `unreconciled: none` (`bug-0044`).
  `S-019` is the sentence that was owed. It is stated as a property, every relative link in an emitted
  lens resolves where the lens landed, rather than as the fix `bug-0044` chose, so a future layout
  that made more forms resolve would not have to amend the contract to use them. Between 2026-08-22
  and this amendment the rule was held by `TestEmittedRulesModuleResolves` alone.

## Test coverage of spec invariants

Flagged per `spec-conformance`'s non-goal: it does not write tests, but does say where an invariant
lacks one. Against [`tests/test_build_adapters.py`](../../tests/test_build_adapters.py):

| Scenario | Covering test | Note |
|---|---|---|
| S-001 | present | asserts the requested target's count, the other target's absence, exit zero, and the summary |
| S-002 | present | both harnesses' frontmatter keys and the banner |
| S-003 through S-008 | present | one unit test each on `rewrite_links` |
| S-003 through S-009 | present | plus one filesystem test resolving all 194 emitted links on disk, which is the layer the original defect lived at |
| S-010 | present | the contract rule with no other enforcement, so this test is the only thing holding it |
| S-011 | present | asserted through a preview run, so the test cannot write into the repository even if the no-op regressed |
| S-012, S-013 | present | each asserts both the exit code and that no file was written |
| S-014 | present | added by `chore-0015`. Asserts both halves in one test, because the contrast is the requirement. Confirmed to fail against the rejected symmetric alternative, so it distinguishes the chosen contract rather than merely restating current behavior |
| S-015 | present | added by `feat-0034`. Asserts the emitted skill count, the absence of any inlined adapter, and the manifest *values* (source, and the marketplace entry's name and version matching the plugin manifest), not that the keys exist |
| S-019 | present | added by `bug-0044`: `TestEmittedRulesModuleResolves` emits each target into a directory of its own and resolves every relative link inside every emitted `.agents/rules/*.md` (or `rules/*.md`) file, asserting the three lenses were walked before asserting nothing dangled. **The test predates the id**: `bug-0044` wrote it when no scenario stated the rule and tagged it `S-009` and `S-016` in the extended sense that pass's unreconciled item described. `chore-0062` states the rule as `S-019`, so the test is retagged to the scenario it actually holds and its two original tags name less than it covers rather than more. Confirmed to **fail** against the pre-fix module, 7 dangling links per inlining target and none for the plugin, so it distinguishes the defect rather than restating the current tree. It walks the lenses because both older filesystem walks structurally cannot: one globs the adapters, the other globs `skills/*/SKILL.md`, and a lens is neither. **It covers three of the four paths S-019 names**, the three targets this tool emits; the fourth, the sibling `<base>/../rules` that `install.py` places, is walked by no test here. `tests/test_install.py` asserts that the module lands where a *skill's* `../../rules/<file>` reference resolves and never reads a link out of a lens, and the only markdown-link regex in the suite is `tests/test_build_adapters.py`'s `LINK`. That gap is flagged rather than filled, per this section's non-goal, and the fourth path was resolved by hand on 2026-08-27 instead |
| S-016 | present | added by `feat-0034`, two tests: one resolving every relative link in every emitted skill on disk and asserting none is broken and none escapes the plugin root, one on `house-review` reaching its rubric and finding `blocker` in the file it lands on, with exactly one copy of the module in the tree. This is the invariant `claude plugin validate` cannot check, so these tests are the only thing holding it |
| S-017 | present | added by `feat-0034`. Asserts both halves, since asserting the absence alone would pass against a target that emitted nothing |
| S-018 | present | added by `bug-0028`, five tests in `TestRewriteLinksInsideCodeSpansAndFences`. The four on `rewrite_links()` each run against both inlining extensions; the fifth targets the plugin, which inlines nothing and has no extension to vary. Two positives use whole-string equality rather than a substring, because "emitted unchanged" is a claim about the whole body. The negatives carry the weight, since the cheap way to remove a false rewrite is to stop rewriting: a real link beside a *closed* fence and one below an *unterminated* fence must both still be repointed. The fenced case holds all three rewritten classes at once (S-003, S-006, S-007), because one surviving proves nothing about the other two. That fifth test asserts the plugin target copies a body byte for byte, so the criterion "unchanged in every target" is asserted rather than assumed. **The tests predate the id and no longer carry the older tags**: `bug-0028` wrote them before any scenario stated the rule, `chore-0043` stated it on 2026-08-19, and `chore-0045` retagged the class and all five cases to `S-018` on 2026-08-27, deleting the docstring paragraph that called the amendment the author's open call. Re-audited on that date against the retagged file: five tests, unchanged in what they assert, and the tags now name what they cover rather than less |

Every scenario has a covering test, including the shared-asset re-run behavior that had neither a
scenario nor a test when this matrix was first written, and the code-span rule that had tests before
it had a scenario. `S-019` is the third of that kind: a test held it from 2026-08-22, and the
contract sentence arrived on 2026-08-27.

The S-015 through S-017 tests were each confirmed to fail against a mutation of the decision they
protect: pointing the plugin layout at the inlining targets' `.agents/rules` (which dangles all 28
rules links and is exactly the failure an `npx skills` run reproduced against this repository on
2026-07-28), and adding `plugin` to the default target set. Neither mutation is caught by
`claude plugin validate`, which passes against the first one.

One note on what the S-014 test is worth. It was confirmed to **fail** when the skill-asset loop is
guarded the way the rules loop is, which is the alternative `chore-0015` considered and rejected. That
makes it an oracle over the decision rather than a restatement of whatever the code happens to do: a
future editor who makes the two loops symmetric will see this test fail and be sent to the contract,
which is the entire point of writing the asymmetry down.
