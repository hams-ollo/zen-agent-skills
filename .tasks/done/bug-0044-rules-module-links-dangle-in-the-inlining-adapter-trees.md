---
id: bug-0044
title: Six links in the rules module dangle in every cursor and vscode adapter tree, because the lenses are copied verbatim while only skill bodies are rewritten
type: bug
status: done
priority: P2
parent: "ROADMAP Epic A: distribution tooling"
depends_on: []
spec: "docs/spec/build-adapters.md"
scenarios: ["S-009", "S-016"]
touched_files:
  - scripts/build-adapters.py
  - tests/test_build_adapters.py
  - .agents/rules/autonomy.md
  - .agents/rules/review-quality.md
created: 2026-08-22
---

## Problem

[`build-adapters.py`](../../scripts/build-adapters.py) rewrites a skill body's relative links so they
resolve from wherever the adapter lands. It does not rewrite the rules module, which it copies byte
for byte. Six links in that module therefore resolve in this repository and dangle in every
`cursor` and `vscode` tree the tool emits.

The six, all of the form `../skills/<name>/SKILL.md`:

```text
.agents/rules/autonomy.md:28    ../skills/doc-sync/SKILL.md
.agents/rules/autonomy.md:59    ../skills/fix-batch/SKILL.md
.agents/rules/autonomy.md:116   ../skills/spec-conformance/SKILL.md
.agents/rules/autonomy.md:127   ../skills/verifier-agent/SKILL.md
.agents/rules/autonomy.md:162   ../skills/pr-describe/SKILL.md
.agents/rules/review-quality.md:5   ../skills/house-review/SKILL.md
```

The mechanism is two functions apart in the same file. `rewrite_links()` maps a sibling link onto
the adapter beside it:

```python
        sibling = SIBLING_RE.match(target)
        if sibling:
            # The sibling's adapter is generated into this same directory.
            return out(f"{sibling.group(1)}{ext}{sibling.group(2) or ''}")
```

`emit_rules_module()` in the same file calls no rewriter at all:

```python
        if not dry:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
```

The links then land in a tree that holds no `SKILL.md` where they point. `emit_skill_assets()`
skips it deliberately: `if not src.is_file() or src.name == "SKILL.md": continue`. For the two
inlining layouts, `Layout(".agents/rules", ".agents/skills")`, the emitted `.agents/skills/<name>/`
directories hold supporting files only, and the bodies live in `.cursor/rules/<name>.mdc` or
`.github/prompts/<name>.prompt.md`.

Reproduced against a clean clone of `developer` at `f8e304b`:

```text
$ python scripts/build-adapters.py --out <tmp> --target cursor
Generated 20 adapter file(s) for 20 skill(s), plus 17 shared asset file(s) under .agents/.

resolving every ../skills/... link under <tmp>/.agents/rules/ on disk:
  DANGLES autonomy.md -> ../skills/doc-sync/SKILL.md
  DANGLES autonomy.md -> ../skills/fix-batch/SKILL.md
  DANGLES autonomy.md -> ../skills/pr-describe/SKILL.md
  DANGLES autonomy.md -> ../skills/spec-conformance/SKILL.md
  DANGLES autonomy.md -> ../skills/verifier-agent/SKILL.md
  DANGLES review-quality.md -> ../skills/house-review/SKILL.md
```

The same probe over the `plugin` target reports all six `OK`, because `Layout("rules", "skills")`
puts a real `SKILL.md` at `skills/<name>/SKILL.md` and the geometry lines up. `install.py`'s layout
resolves them too, since its base directory is itself named `skills`. The defect is specific to the
two inlining targets, which is part of why it has survived every gate.

`review-quality.md:5` is the sharpest instance, because it is the pointer from the rubric back to
the skill the rubric is for. The portability contract in AGENTS.md names this exact failure shape:
the body still reads correctly and only the target is absent, "which is how `house-review` once
shipped with no rubric".

**Why nothing caught it.** `tests/test_build_adapters.py` does resolve every emitted link on disk,
twice, and both walks exclude the rules module:

- `test_every_relative_link_in_every_adapter_resolves` walks `self._adapters()`, defined as
  `self.out.glob(".cursor/rules/*.mdc")` plus `self.out.glob(".github/prompts/*.prompt.md")`.
- `test_every_link_in_the_emitted_tree_resolves_inside_the_plugin_root` walks
  `root.glob("skills/*/SKILL.md")`.

Searched: `grep -c "rules" tests/test_build_adapters.py` returns 28. The hits that touch an
emitted rules file assert that it exists (`test_the_review_rubric_is_emitted_with_its_content`),
that its content carries the word `blocker`, that an adopter's copy is not clobbered
(`test_an_existing_rules_file_is_not_clobbered`, `test_an_adopted_rules_file_is_left_alone_and_counted_in_neither_run`),
and that the emitted inventory holds each rules file exactly once. None reads a link out of one.

The contract has the same shape. `S-009` requires that the material the rewritten links point at is
emitted, which is a claim about targets rather than about a lens's own outbound links. `S-016`
requires that nothing points outside the tree, and is scoped to the plugin target, the one target
where these six links already resolve.

## Scope

**In scope:** make the six links resolve in the `cursor` and `vscode` trees, and add a test that
would have failed.

Two routes, and choosing between them is the work rather than a detail of it:

1. **Rewrite them.** Give `emit_rules_module()` the treatment `rewrite_links()` gives a body, with
   a rule for a lens's position: from `<out>/.agents/rules/`, a sibling skill is
   `../../.cursor/rules/<name>.mdc` for cursor and `../../.github/prompts/<name>.prompt.md` for
   vscode. This keeps the cross-references live and makes the rewrite layout-dependent for the
   first time.
2. **De-link them.** Name the skills in prose in the two lenses, as `autonomy.md` already does for
   files outside the shipped tree, and leave `emit_rules_module()` a plain copy. This costs six
   clickable links in this repository and in an `install.py` tree, and buys a rule with no
   per-layout special case.

Prefer route 2 unless the cross-references are judged load-bearing. `autonomy.md` already states
the principle it would be applying to itself: references to files outside the installed skill tree
are named in prose rather than linked, because a link that escapes resolves here and dangles
everywhere it actually runs. A lens sits one directory further out than a skill, so more of the
tree is outside it than that file currently assumes.

**Out of scope:**

- Amending `docs/spec/build-adapters.md`. No scenario covers a rules file's own outbound links, and
  writing one is a separate chore in the shape of
  [chore-0043](chore-0043-amend-build-adapters-spec-for-the-code-span-exception.md). Record
  what is owed at closeout.
- The repository-side lint gap that let this through, which is a different fix in a different tool.
  See [chore-0058](../chore-0058-no-gate-link-checks-the-markdown-under-agents-outside-skills.md).
- `install.py`'s layout and the plugin layout, both of which already resolve these links. Do not
  change either to accommodate a fix for the other two.

## Implementation notes

`SIBLING_REF_RE` in [`install.py`](../../scripts/install.py) reads the same `](../../<name>/SKILL.md`
syntax as a profile edge, so route 2 raises the question of whether removing these links changes an
install profile. It does not: `resolve_profile()` expands over `sibling_refs(skill_dir)`, which
reads only `<skill_dir>/SKILL.md`, and the rules module is not a skill directory and is never
walked. Confirm that before relying on it rather than taking it from this paragraph.

If route 1 is taken, note that `SHARED = "../../.agents"` is a module constant precisely because it
is the same string for both inlining targets, whose adapter directories are two deep. A lens sits
two deep as well, so the mirror-image constant is derivable rather than guessed.

The new test belongs beside the two that already exist, and must walk the emitted rules directory
rather than the adapters, so the new walk cannot be satisfied by the old one. Assert on the named
files as well as on a count: a count over an empty glob passes.

## Decisions

**Rejected: route 1, rewriting the links in `emit_rules_module()`.** Not a preference, a structural
impossibility. `LAYOUTS["cursor"] == LAYOUTS["vscode"]` as namedtuples, `main()` dedupes layouts, and
`emit_rules_module()` receives a `Layout` rather than a target, so a default run emits **one**
`.agents/rules/autonomy.md` for both targets while their adapters sit at `.cursor/rules/<name>.mdc`
and `.github/prompts/<name>.prompt.md`. Measured: a `--target cursor,vscode` run emits one copy of
`autonomy.md` and two `doc-sync` adapters. No single rewritten link text resolves for both, and
whichever was chosen would dangle for anyone building the other target alone. The task's suggested
constant `SHARED` mirror is derivable but has nothing to point at.

**Rejected: emitting a `SKILL.md` per skill into the inlining trees** so the existing link form
resolves. It contradicts the reason those layouts inline at all, and doubles the emitted footprint to
make six citations clickable.

**Chosen: route 2, naming the skills in prose.** Seven links, not six, replaced with backticked
names. It costs clickable citations in this repository, the plugin tree, and an `install.py` tree,
and it buys one rule with no per-layout case: a lens may link what sits beside it in every layout
(its sibling lenses) and names anything else. `autonomy.md` already stated that rule about itself
seven lines above the first violation of it, so this is the file being made to follow its own
citation convention rather than a new constraint.

**Premise corrected: there are seven dangling link instances, not six.** The task body lists six
line numbers and omits `autonomy.md:189`, a second `fix-batch` link inside the fourth held-candidate
bullet. The pre-fix test run reports 7 per inlining target.

**Confirmed, not assumed: de-linking changes no install profile.** Two independent reasons.
`SIBLING_REF_RE` is `\]\(\.\./([^/)]+)/SKILL\.md`, which does not match `](../../skills/<name>/SKILL.md`
at all, since the captured segment is `skills` and the next characters are `/<name>/` rather than
`/SKILL.md`. And `sibling_refs()` reads only `<skill_dir>/SKILL.md` for directories from
`discover_skills()`, which never walks `.agents/rules/`. `resolve_profile()` after the change still
returns core 3, spine 18, all 20.

**Seam left open deliberately: the contract still says nothing about a lens's outbound links.** The
behavior is now held by `TestEmittedRulesModuleResolves` and by nothing in
`docs/spec/build-adapters.md`. Amending the spec is out of scope here by the task's own scope
section; what is owed is written into the conformance matrix's unreconciled set, which moves from
`none` to one item.

## Risks and rollback

Required: `touched_files` spans the generator, its tests, and two shipped lenses, which is more than
one module.

Route 2 edits two files an adopter is invited to rewrite. An adopter who has already taken the
kit's copy of `autonomy.md` keeps their edited copy on re-install, by the adopted-file rule in
`_place_adopted`, so they keep the dangling links and get no signal. That is acceptable and worth
naming at closeout rather than solving here.

Reversible by reverting one commit. `build-adapters.py` writes a tree and holds no state across
runs, so nothing persists to migrate back.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] A new test resolves every relative link inside every emitted `.agents/rules/*.md` file, for
      both the cursor and the vscode target, and asserts none dangles.
- [x] That test fails against the current `emit_rules_module()`, proven by running it before the
      fix and recording the verbatim output in the closeout.
- [x] The plugin target's six links still resolve, so the fix did not trade one layout for another.
- [x] `python scripts/build-adapters.py --out <tmp> --target cursor`, followed by resolving every
      link under `<tmp>/.agents/rules/`, reports zero broken links, and that run is recorded.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] The `build-adapters` conformance matrix updated over `S-009` and `S-016`, or the deferral recorded with what is owed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
