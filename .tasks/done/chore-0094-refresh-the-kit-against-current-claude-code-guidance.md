---
id: chore-0094
title: Refresh the kit against current Claude Code guidance, starting with what every session loads
type: chore
status: done
priority: P1
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - .agents/rules/core.md
  - .agents/rules/autonomy.md
  - .agents/rules/house-style.md
  - .agents/rules/review-quality.md
  - .agents/hooks/worktree-boundary-reminder.py
  - .agents/hooks/delegation-reminder.py
  - .agents/hooks/README.md
  - .agents/skills/
  - .claude/settings.json
  - .codex/hooks.json
  - .opencode/plugins/zen-hooks.mjs
  - AGENTS.md
  - CLAUDE.md
  - README.md
  - CHANGELOG.md
  - .tasks/.scaffold.json
  - docs/rationale/
  - docs/ARCHITECTURE.md
  - docs/CATALOG.md
  - docs/GETTING-STARTED.md
  - docs/INSTALL.md
  - scripts/install.py
  - scripts/validate-skills.py
  - tests/test_hooks.py
  - tests/test_hooks_worktree_boundary.py
  - tests/test_install.py
  - tests/test_validate_skills.py
created: 2026-10-20
---

## Problem

The [2026-10 kit refresh audit](../../docs/reviews/2026-10-kit-refresh-audit.md) found the kit's
skills inside current guidance and its always-on footprint far outside it. `install.py` places the
lenses in `~/.claude/rules/` so skill links resolve, and Claude Code loads every file there into every
session: 488 lines of lens text plus the user `CLAUDE.md`, about 9,000 tokens, most of the largest
file citation and history (findings 1.1 to 1.4). The repository's `CLAUDE.md` was a prose pointer to
`AGENTS.md`, the exact shape the memory docs say Claude follows only when it decides to (6.1), and
the kit shipped the same pointer to every scaffolded repository. The delegation reminder fired on
background launches and never on their reports (4.6), nothing reminded an agent of `A1` when a shell
command wrote out of a worktree (4.2), descriptions averaged well over what a crowded skill listing
keeps (2.1, 3.2), and no rule said which changes skip the spec chain (5.1).

## Scope

**In scope:** the audit's ranks 2 to 4, 6 to 8, and 11 to 14: on-demand lenses
and a compact always-loaded core, history moved verbatim to `docs/rationale/`, the `@AGENTS.md` import
here and in the template, `AGENTS.md` under 200 lines, the `worktree.baseRef` and `attribution`
settings, the delegation fix, a worktree-boundary reminder hook, tightened descriptions, the light
path, and validator rules and tests for the new conventions.

**Out of scope, kept as proposals for the maintainer:** retiring or folding `review-depth` (rank 10),
the evaluation slice (rank 9), the `A8` deny rule (rank 15, since no configuration here is used only by
unattended runs), the observatory's scope (rank 16), both parts of rank 17 (the stale line sits in an
approved contract, `sitrep.md`), the user `CLAUDE.md` link conflict (rank 5, the maintainer's own file),
and running `/doctor prompt-audit` (rank 1, which needs the maintainer's sign-in). No skill was
deleted and no safety rule was removed; `A1`, `A3`, `A8`, and `A10` keep their full text in
`autonomy.md` and a line each in `core.md`.

## Decisions

- **Rejected: renaming `.agents/rules/` to a directory Claude Code does not auto-load.** It would have
  kept the lenses out of every session too, but it touches every skill's lens link, the adapter
  builder, the installer's migration of existing installs, and three approved specs that pin the
  layout. `paths` frontmatter is documented to work at user scope ("Rules with `paths:` load when
  Claude reads, writes, or edits a matching file", per the `.claude` directory page) and changes no
  contract.
- **Rejected: an em-dash hook.** The rule belongs to the swappable house-style lens, and a hook that
  hardcodes it would impose this kit's voice on every repository a session opens, which `AGENTS.md`
  calls a defect. The validator enforces it over the kit's own skills and lenses instead, and only
  while the house-style lens in that tree states the rule.
- **Seam left open: a background agent's report.** The delegation reminder now stays silent on a
  background launch, but no documented event fires in the delegating session when a background
  report arrives, so that case is covered by `fix-batch` Step 6 rather than by a hook.
- **Found by independent verification, and fixed.** The first pass wrapped descriptions with a
  wrapper that broke on hyphens, so three `>-` scalars read "doc- author", "current- state", and
  "docs- only" to any YAML parser; `validate-skills.py` now rejects that shape. The same pass found
  dropped "distinct from" pointers and trigger phrases (restored), two rule clauses lost from
  `AGENTS.md` (restored), a sentence lost from `autonomy.md` (restored), three `core.md` lines that
  omitted part of their rule (completed), and the new hook reading `https://` as a drive (fixed).
- **Seam left open: the validate-skills spec.** `docs/spec/validate-skills.md` has no scenarios for
  the three new checks. It is an approved contract, so it is not edited here; amending it is the
  maintainer's call.

## Risks and rollback

Touches more than one module (the rules, the hooks, the validator, the installer's registration, and
every skill's description). An adopter who edited a lens keeps their copy on re-install and so keeps
loading it every session until they add the `paths` frontmatter themselves; `docs/INSTALL.md` says so.
The committed settings now carry two non-hook keys that older Claude Code versions might not know;
if one rejects the file, the committed `SessionStart` hook stops firing there. Rollback is reverting
the commit; nothing persisted changes format.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] New tests for the worktree-boundary hook, the delegation fix, and the validator's on-demand,
  always-loaded budget, em-dash, folded-hyphen, and description-advisory rules.
- [x] Existing tests still pass.
- [x] `validate-skills.py` reports 0 errors, and no description is over the 700-character advisory.
- [x] `AGENTS.md` is under 200 lines, and the always-loaded rules files are under 40.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run by hand over the reader-facing documents (a search of each for the pointer
  wording, the rules placement, and the description figures), and its findings applied to
  `README.md`, `docs/INSTALL.md`, `docs/ARCHITECTURE.md`, `docs/CATALOG.md`, and
  `docs/GETTING-STARTED.md`.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing
  this task id.
