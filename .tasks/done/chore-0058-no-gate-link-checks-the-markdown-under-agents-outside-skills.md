---
id: chore-0058
title: No gate link-checks the markdown under .agents/ outside .agents/skills/, so a dangling or escaping link in a lens passes all seven gates
type: chore
status: done
priority: P2
parent: "ROADMAP Epic A: distribution tooling"
depends_on: []
touched_files:
  - scripts/validate-skills.py
  - tests/test_validate_skills.py
created: 2026-08-22
---

## Problem

Four markdown files ship under `.agents/` outside `.agents/skills/`, and nothing checks their
links:

```text
.agents/hooks/README.md
.agents/rules/autonomy.md
.agents/rules/house-style.md
.agents/rules/review-quality.md
```

All four travel to an adopter. `install.py` places `.agents/rules/` as the sibling
`<base>/../rules` on every run, and `--with-hooks` places `.agents/hooks/`. So a link in one of
them is exactly as clickable, and exactly as breakable, as a link in a `SKILL.md`, which
[`validate-skills.py`](../../scripts/validate-skills.py) checks under three rules: the target
resolves, a `../<name>/SKILL.md` names a real skill, and the target does not escape the shipped
tree.

Neither of the two link gates reaches these files.

- `validate-skills.py` walks `SKILLS_DIR.iterdir()` and link-checks each skill's `SKILL.md` plus
  the markdown beside it. It reads `.agents/rules/` exactly once, in
  `check_lenses_are_composed(portable_root / "rules", skill_texts, errors)`, and that function asks
  only whether some skill names the file. It never reads a link out of it.
- The `doc links` gate in [`run-checks.py`](../../scripts/run-checks.py) passes the globs
  `"*.md"`, `".github/**/*.md"`, `"docs/**/*.md"`. None of them reaches `.agents/`.

Searched, to establish that no third checker covers them:
`grep -rn "agents/rules\|RULES_DIR\|rules_dir" scripts/*.py` returns 23 hits across
`build-adapters.py`, `install.py`, and `validate-skills.py`, and every one is a copy target, a
placement target, or the composition check named above. `grep -rn "hooks/README" scripts/ tests/`
returns two source hits, both in `tests/test_hooks.py`, and both cite that file as the source of
the module contract the tests assert; neither reads a link out of it.

Demonstrated against a clean clone of `developer` at `f8e304b`, by appending one line to a lens:

```text
$ printf '\nSee [the roadmap](../../ROADMAP.md) and [a file that is not there](does-not-exist.md).\n' \
    >> .agents/rules/house-style.md
$ python scripts/run-checks.py
ok          lint skills
ok          test suite
ok          backlog
ok          adapters dry run
ok          install dry run
ok          install cycle
ok          doc links

7 passed, 0 failed, 0 could not run.
```

Both halves of that probe matter, and the second is worse than the first. `does-not-exist.md` is an
ordinary broken link. `../../ROADMAP.md` is the escape class: it resolves in this repository, so it
looks correct to every reader here, and it dangles in every installed tree, because an install
places `rules/` beside `skills/` and nothing above. That is the failure the portability contract
exists for, enforced for a `SKILL.md` since the rule was written and never for the lenses shipped
next to it.

The four files resolve cleanly today. Every relative link in all four was resolved on disk during
this review and none dangles, so this is a missing gate rather than a live break. The live break of
the same class in the emitted adapter trees is
[bug-0044](bug-0044-rules-module-links-dangle-in-the-inlining-adapter-trees.md).

**This task is one of five in the same class**, grouped 2026-08-22 rather than worked as unrelated errands: a guard that does not guard. The other four are [`chore-0032`](../chore-0032-links-guard-fires-per-run-not-per-pattern.md), [`chore-0049`](../chore-0049-a-checker-for-conformance-matrix-citations.md), [`chore-0059`](../chore-0059-the-third-and-fourth-copies-of-the-link-helpers-are-unguarded.md), and [`chore-0060`](../chore-0060-the-scaffold-manifest-id-high-water-is-stale-and-unguarded.md). `bug-0045` was the sixth and is closed: it found six of seven gates reporting `ok` over a repository containing nothing. **What the grouping asks of whoever works this one**: when you fix it, look for the next member before you finish, because every member of this class so far was found only by looking after the previous one landed. The pattern behind the class is [`chore-0063`](chore-0063-the-repository-has-never-written-down-what-it-keeps-learning.md).

## Scope

**In scope:** extend `validate-skills.py` so the markdown under `.agents/` that is not inside a
skill directory is link-checked by the same rules a supporting file already gets.

- Reuse `check_links(..., portable_root=<the .agents tree>, sibling_shortcut=False)`. The shortcut
  must stay off for the same reason it is off for a supporting file: from `.agents/rules/`,
  `../skills/doc-sync/SKILL.md` is a path to resolve on disk, not a skill name to look up.
- Report the count of files checked on the existing coverage line, or on one beside it, so a walk
  that stops matching is visible. "0 rules files checked" and "no rules files exist" must not read
  the same.
- Keep `check_lenses_are_composed` as it is. It answers a different question and its skip-when-no-
  rules-directory branch is correct for a skills tree without one.

**Out of scope:**

- Fixing anything the new check reports. It reports clean on the current tree; if it does not, that
  is a finding to file, not work to fold in here.
- Widening the CI `--links` globs to `.agents/**/*.md` as the fix. That routes a skill-tree rule
  through the backlog validator, which has a different link rule (it permits `file://` and absolute
  targets, and knows nothing about the portable root), so the two would disagree about the same
  file. The rule that governs `.agents/` already lives in `validate-skills.py`.
- The per-pattern reporting question in the `--links` mode, which is
  [chore-0032](../chore-0032-links-guard-fires-per-run-not-per-pattern.md).
- `.agents/skills/**`, already covered by
  [chore-0036](chore-0036-link-check-skill-supporting-files.md).
- Amending `docs/spec/validate-skills.md`. This rule reaches outside `.agents/skills/` for the
  second time and no scenario describes it, so a contract amendment is owed in the shape of
  [chore-0054](chore-0054-amend-validate-skills-spec-for-the-supporting-file-rule.md). File it
  at closeout rather than folding it in; that is why this task declares no `spec`.

## Implementation notes

Prior art to mirror exactly: `check_supporting_files()` and its classification helper, added by
`chore-0036` for the same reason one level down. The two decisions that function already made apply
unchanged here, which is the argument for extending it rather than writing a second walker:
`.tmpl` files are destination-bound and must stay skipped, and the skipped counts are reported
beside the checked one so a coverage number is comparable across runs.

The walk is `.agents/**/*.md` minus everything under `.agents/skills/`. Deriving the exclusion from
`SKILLS_DIR` rather than from the literal string `skills` keeps one source of truth for where the
skills live.

One edge worth deciding rather than discovering: `main()` currently computes `portable_root` as
`skills_dir.parent.resolve()` and passes it around. A file at `.agents/rules/x.md` reaching
`../skills/y/SKILL.md` stays inside that root, so the escape rule needs no new constant.

## Decisions

- **A premise that turned out false: the demonstration transcript no longer reproduces.** It was
  recorded at `f8e304b`. Re-run at this task's base `e4f04f2`, appending those two links to
  [`house-style.md`](../../.agents/rules/house-style.md) fails the `test suite` gate, not passes it:
  `TestEmittedRulesModuleResolves` in [`test_build_adapters.py`](../../tests/test_build_adapters.py)
  walks the emitted lenses and reports both links as dangling for all three targets. That test
  landed with `bug-0044` in `e8c956b`, after this task was written. The gap is real but narrower
  than stated: the identical probe appended to
  [`hooks/README.md`](../../.agents/hooks/README.md) still passed all seven gates at exit 0, because
  that walk globs only the emitted rules directory. Two of the four files this task names were
  already covered incidentally, in the emitted trees only and only as "dangling", never as an
  escape.
- **A rejected alternative: reporting the new count on a line of its own.** `coverage_line()` in
  [`run-checks.py`](../../scripts/run-checks.py) shows the last line of a gate's output containing a
  digit, which for `lint skills` is already the supporting-file line. A third line would take its
  place, so the acceptance command would silently stop reporting the coverage `bug-0045` and
  `chore-0036` put there. The count is appended to that line instead, which is what makes "the run
  reports how many it checked" true of `validate-skills.py` and of `run-checks.py` at once.
- **A rejected alternative: walking `skills_dir.parent` unconditionally.** `main()` is callable
  against any directory of skill folders, and roughly forty existing fixtures pass a bare temporary
  directory, whose parent is the system temp directory: 20,203 entries and 51 markdown files on the
  machine this ran on, so the walk would have link-checked unrelated files and reported their broken
  links as this kit's. The walk runs only where the skills directory carries `SKILLS_DIR.name`,
  which is how every layout `install.py` places names it.
- **A seam left open: a renamed skills tree loses the check.** `check_portable_markdown` declines
  where the geometry is not a shipped one and says so in words rather than counting zero, so the
  decline is visible. Closing it would mean an explicit walk-root parameter on `main()`, which no
  caller has a use for today.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] A test writes a rules file carrying a link to a file that does not exist and asserts the run
      reports it and exits non-zero.
- [x] A test writes a rules file carrying a link that resolves above the `.agents/` tree and
      asserts the run reports it as an escape, not merely as resolving.
- [x] The run reports how many non-skill `.agents/` markdown files it link-checked, and a test
      asserts that number against a fixture tree rather than only that the run passed.
- [x] Run over the current tree, the new check reports zero errors, and that output is recorded in
      the closeout.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
