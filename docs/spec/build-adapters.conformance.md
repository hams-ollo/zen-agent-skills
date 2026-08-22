---
title: build-adapters conformance
spec: docs/spec/build-adapters.md
audited: 2026-07-27
re_audited: 2026-07-27 (chore-0015), 2026-08-06 (feat-0034), 2026-08-19 (chore-0043),
  2026-08-22 (bug-0044, partial: S-009 and S-016 only)
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
| Scenarios | S-009 the material the links point at is emitted | Conformed | `emit_shared_assets()` / both copy loops, called per skill from `main()` | rules module and each skill's non-`SKILL.md` files |
| Scenarios | S-010 an existing rules file is never overwritten | Conformed | `emit_shared_assets()` / `or dest.exists(): continue` in the rules loop | confirmed by execution: an edited rules file survives a re-run unchanged |
| Scenarios | S-014 a re-run refreshes derived assets and preserves adopted ones | Conformed | `emit_shared_assets()` / the rules loop's `or dest.exists(): continue`, contrasted with the skill-asset loop which has no such guard | added by `chore-0015`. Confirmed by execution: after editing both and re-running, the rules file kept its content and the skill template was replaced by the kit's version |
| Scenarios | S-011 generating into the kit is a no-op | Conformed | `emit_shared_assets()` / `dest.resolve() == src.resolve(): continue` in both loops | confirmed by execution: a run against the repo root reports `plus 0 shared asset file(s)` |
| Scenarios | S-012 a preview run writes nothing | Conformed | `_write()` / `if dry: return`, and the `if not dry` guards in `emit_shared_assets()` | confirmed by execution: zero files written into a temp root |
| Scenarios | S-013 an unrecognized target is rejected | Conformed | `main()` / the `bad` check returning 2 | the check precedes any emission, so nothing partial is written; confirmed by execution (exit 2, zero files) |
| Scenarios | S-015 the plugin target emits an installable plugin tree | Conformed | `emit_plugin()` / `dest = out / "skills" / src.name / "SKILL.md"`, and `emit_plugin_manifests()` / the `marketplace` literal and the `for fname, obj in ...` write loop, dispatched from `main()` by `if "plugin" in targets` | added by `feat-0034`. Both manifests are derived from the single `PLUGIN` mapping, so the marketplace entry cannot name a plugin other than the one emitted beside it. The destination uses `src.name`, the source *directory* name, because `../<dir>/SKILL.md` is what a sibling link names. Confirmed by execution: `claude plugin validate --strict` passes against the generated tree |
| Scenarios | S-016 nothing in an emitted plugin tree points outside it | Conformed | `LAYOUTS["plugin"] = Layout("rules", "skills")`, consumed by `emit_shared_assets()` / `out / layout.rules_dir` and `out / layout.assets_dir`; and `emit_plugin()`, which copies the source `SKILL.md` verbatim and calls no rewriter | added by `feat-0034`, and the reason the target exists. The layout, not a rewrite, is what makes the links resolve: `skills/<name>/` reaching `../../rules/<file>` lands on `rules/<file>`, the same geometry `.agents/skills/<name>/` has to `.agents/rules/<file>` with the `.agents/` parent dropped. Confirmed by execution: 117 relative links resolved on disk from the emitted root, none broken and none leaving it, with one copy of `review-quality.md` at `rules/review-quality.md`. Confirmed to **fail** when the plugin layout is given the inlining targets' `.agents/rules`, which dangles all 28 rules links, so it is an oracle over the layout decision rather than a restatement of it |
| Scenarios | S-017 the plugin target is opt-in | Conformed | `main()` / the `--target` `default="cursor,vscode"`, and the `if "plugin" in targets` guard on `emit_plugin_manifests()` | added by `feat-0034`. Confirmed to **fail** when `plugin` is added to the default, which also breaks the pre-existing S-011 test, since a default run into the kit would then write `rules/` and `skills/` trees the no-op guard does not cover |
| Proposed Surface | Invocation and its three flags | Conformed | `main()` / the `argparse` definitions for `--target`, `--out`, `--dry-run` | `--target` defaults to `cursor,vscode` and `--out` to the working directory. Amended by `feat-0034`: the default is the two inlining targets rather than every supported one, per S-017 |
| Proposed Surface | Emitted per-skill paths | Conformed | `emit_cursor()`, `emit_vscode()` and `emit_plugin()` `dest` expressions | `.cursor/rules/<name>.mdc`, `.github/prompts/<name>.prompt.md`, `skills/<name>/SKILL.md` |
| Proposed Surface | Emitted per-plugin-run paths | Conformed | `emit_plugin_manifests()` / `dest = out / ".claude-plugin" / fname` | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, written once per run rather than per skill |
| Proposed Surface | Emitted shared paths | Conformed | `emit_shared_assets()` / both `dest` expressions, over `layout.rules_dir` and `layout.assets_dir`, with the distinct-layout loop in `main()` | `.agents/rules/<file>` and `.agents/skills/<name>/<path>` for the inlining targets, `rules/<file>` and `skills/<name>/<path>` for the plugin. `cursor` and `vscode` share one layout, so requesting both still emits one copy |
| Proposed Surface | Exit code | Conformed | `main()` / `return 2` for a bad target, `return 0` otherwise | |
| Proposed Surface | Output | Conformed | `main()` / the per-emission print, the manifest print, the closing summary and its manifest-count line | the summary names the shared roots actually written, so a plugin run reports `under rules/, skills/.` where an inlining run reports `under .agents/.` |

## Coverage proof

- **audited**: S-001 through S-018, and all six Proposed Surface elements, as of the 2026-08-19
  pass. Every spec item was checked then. S-018 is numbered after S-017 and placed beside S-008 in
  both documents, because it is the exception those rewrite rows are read against. The 2026-08-22
  pass re-audited **2 of those 18 scenarios**, `S-009` and `S-016`, and no Proposed Surface element;
  the other 16 rows stand on the earlier pass and are not re-asserted by this one.
- **unreconciled**: one, and it is an owed amendment rather than a divergence. **No scenario states
  what a file in the rules module may link to.** Every link rule in this contract, `S-003` through
  `S-008` and `S-018`, is about a *skill body* passing through `rewrite_links()`; `S-009` covers the
  targets those rewritten links land on; `S-010` and `S-014` cover the module's placement and its
  survival across a re-run; `S-016` covers escape, and only for the plugin target. A lens's own
  outbound links are named by none of them, which is how seven `../skills/<name>/SKILL.md` links
  shipped dangling in every emitted cursor and vscode tree while this matrix read `unreconciled:
  none` (`bug-0044`). **What is owed**: a scenario stating that the rules module is emitted verbatim
  and that a lens may therefore link only what sits beside it in every layout, its sibling lenses,
  naming a skill in prose instead. The behavior now exists and is held by a test; only the contract
  sentence is missing. `bug-0044` scopes writing it out, deliberately, in the shape of `chore-0043`,
  which amended this same spec for `S-018` after `bug-0028` had already shipped the behavior. Until
  that chore is filed and closed, the rule is enforced by
  `TestEmittedRulesModuleResolves` alone.

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
| S-009, S-016 | present | added by `bug-0044`: `TestEmittedRulesModuleResolves` emits each target into a directory of its own and resolves every relative link inside every emitted `.agents/rules/*.md` (or `rules/*.md`) file, asserting the three lenses were walked before asserting nothing dangled. It covers the two scenarios only in the extended sense the unreconciled item above describes, since the rule it holds is not yet stated by either. Confirmed to **fail** against the pre-fix module, 7 dangling links per inlining target and none for the plugin, so it distinguishes the defect rather than restating the current tree. It walks the lenses because both older filesystem walks structurally cannot: one globs the adapters, the other globs `skills/*/SKILL.md`, and a lens is neither |
| S-016 | present | added by `feat-0034`, two tests: one resolving every relative link in every emitted skill on disk and asserting none is broken and none escapes the plugin root, one on `house-review` reaching its rubric and finding `blocker` in the file it lands on, with exactly one copy of the module in the tree. This is the invariant `claude plugin validate` cannot check, so these tests are the only thing holding it |
| S-017 | present | added by `feat-0034`. Asserts both halves, since asserting the absence alone would pass against a target that emitted nothing |
| S-018 | present | added by `bug-0028`, five tests in `TestRewriteLinksInsideCodeSpansAndFences`, each run against both inlining extensions. Two positives use whole-string equality rather than a substring, because "emitted unchanged" is a claim about the whole body. The negatives carry the weight, since the cheap way to remove a false rewrite is to stop rewriting: a real link beside a *closed* fence and one below an *unterminated* fence must both still be repointed. The fenced case holds all three rewritten classes at once (S-003, S-006, S-007), because one surviving proves nothing about the other two. A fifth test asserts the plugin target copies a body byte for byte, so the criterion "unchanged in every target" is asserted rather than assumed. **The tests predate the id**: written when no scenario stated the rule, they are tagged with the scenarios they refine and their docstring says an `S-018` is the author's call. That call is now made, so the tags are stale in one direction only, naming less than they cover |

Every scenario has a covering test, including the shared-asset re-run behavior that had neither a
scenario nor a test when this matrix was first written, and the code-span rule that had tests before
it had a scenario.

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
