---
name: init-worktracking
description: Scaffold a portable, agent-optimized spec-driven work-tracking system into the current repository - AGENTS.md (global rules + agent reading protocol), a .tasks/ directory of atomic task files, and (by tier) ROADMAP.md, CHANGELOG.md, a validate.py checker, and thin CLAUDE.md/Cursor/Copilot pointers. Choose a footprint tier (lite/standard/team) so small repos are not buried. Seeds AGENTS.md by inspecting the repo (package manager, test runner, CI, layout) instead of leaving blanks. Safe to re-run: detects its own prior scaffold and upgrades rather than clobbering, and seeds task ids from existing files so they never collide. Use when the user wants to set up work-item tracking, a backlog, a todo/changelog system, or task files that parallel subagents can pick up, or says things like "add work tracking here", "set up the task system", or "scaffold the backlog". Detects any pre-existing tracker first and offers a dry-run migration rather than scaffolding a parallel system. Feeds the new-task and fix-batch skills: one task file per worktree-isolated agent.
---

# init-worktracking

Scaffold a spec-driven, low-context-bloat work-tracking system into whatever repository this is invoked from. The system is separate files at four altitudes of work, so an assigned agent loads only what its task needs:

- **`AGENTS.md`** - global rules, including the agent reading protocol (read this file + your one task file + only its `touched_files`).
- **`.tasks/`** - atomic, agent-assignable task files, one per work item, with `done/` for completed ones and a shipped `validate.py`.
- **`ROADMAP.md`** - the strategic Epic/Feature layer.
- **`CHANGELOG.md`** - append-only ledger of finished tasks.
- **`CLAUDE.md`** and optional Cursor/Copilot files - thin pointers to `AGENTS.md`, the one canonical source every agent flavor reads.

Templates live in [`templates/`](templates/). Fill their `{{PLACEHOLDERS}}` from the actual repo and write them in, without clobbering anything that already exists.

## Why this shape

The point is context frugality for agents. A task file's `touched_files` frontmatter is a read/write whitelist, `depends_on` is a safe-dispatch guard for parallel agents, and the acceptance criteria are a mechanically checkable command the agent self-verifies against. That is exactly the unit the `fix-batch` skill consumes: one task file per parallel worktree-isolated agent, and the unit the `new-task` skill authors. So the scaffold is only as good as the honesty of those fields, which is why a validator ships with it.

## Footprint tiers

Do not dump the whole system on a 200-line project. Ask which tier fits, or infer from repo size and let the user correct:

| Tier | Writes | For |
|---|---|---|
| **lite** | `AGENTS.md`, `.tasks/` (README, `_TEMPLATE.md`, `done/`), `CLAUDE.md` pointer | small or solo repos that want task files without the ceremony |
| **standard** | lite + `ROADMAP.md` + `CHANGELOG.md` | most repos; the full altitude model |
| **team** | standard + `.tasks/validate.py` + a CI/pre-commit invocation + optional Cursor/Copilot pointers | repos with many contributors or agents, where drift must be caught mechanically |

At **lite**, also strike the `ROADMAP.md`/`CHANGELOG.md` references out of the `AGENTS.md` you write (sections 1 and 5 still describe the model, but the header links and lifecycle steps 4-5 should not point at files that do not exist).

## Procedure

### Step 1: survey the target repo

Do this before writing anything.

1. Confirm the working directory is a git repository (`git rev-parse --is-inside-work-tree`). If not, tell the user and ask whether to `git init` first: the parallel-agent workflow this feeds assumes git, and `.tasks/` must be tracked (see Step 6).
2. **Check for a prior run of this scaffold.** Look for `.tasks/.scaffold.json` (the manifest this skill writes). If it exists, this is a re-run: go to Step 5 (upgrade), do not scaffold fresh.
3. Check which target files already exist: `AGENTS.md`, `.tasks/`, `ROADMAP.md`, `CHANGELOG.md`, `CLAUDE.md`. **Never overwrite an existing file silently** (Step 4 handles each).
4. **Detect any pre-existing work tracker, including under a different name or shape.** Scaffolding a parallel system next to one that already exists is the worst outcome. Actively look for:
   - Alternative-named files: `TODO.md`/`TODO`/`TODOS.md`, `BACKLOG.md`, `TASKS.md`, `PLAN.md`, `HISTORY.md`/`NEWS.md`/`RELEASES.md` (changelog equivalents), `docs/` trackers (`dev-tracker`, `worklog`, `progress`, `planning`), a `tasks/`/`issues/` directory.
   - Embedded sections: a "TODO", "Backlog", "Work log", "Roadmap", "Changelog", or "Done" heading inside `README`, `CONTRIBUTING`, or a docs file (grep for those headings).
   - Out-of-repo trackers you cannot migrate but should acknowledge: GitHub Issues/Projects (an `ISSUE_TEMPLATE` dir or `.github/` config hints at this), a linked Linear/Jira/Notion board mentioned in the README.
   If one is found, Step 6 handles migration. Do not proceed to scaffold changelog/roadmap files as if the repo were empty when an equivalent already exists.

### Step 2: choose the footprint tier

Pick from the table above. Default to **standard** for a typical repo, **lite** for something small or single-purpose, **team** when the user mentions multiple contributors, CI, or parallel agents. State your choice and let the user override before writing.

### Step 3: seed content by inspection (do not leave blanks)

Gather what fills the placeholders from the repo itself, not from assumptions. Turn a blank scaffold into a roughly 70%-done draft:

- **Project name**: the repo directory name, or a name from `package.json`/`pyproject.toml`/`Cargo.toml`/`go.mod`/README.
- **Overview** (`{{OVERVIEW}}`): 2-4 sentences on what the project is and its top-level layout. Read the README and glance at the top-level tree. Keep it to the 30,000 ft view.
- **Commands** (`{{COMMANDS}}`): the real setup, test, and build commands. Detect them:
  - Package manager and test runner from the manifest: `package.json` scripts + lockfile (`package-lock.json` -> npm, `pnpm-lock.yaml` -> pnpm, `yarn.lock` -> yarn), `pyproject.toml` (`uv.lock` -> uv, `poetry.lock` -> poetry) with pytest, `Cargo.toml` -> cargo, `go.mod` -> go.
  - CI from `.github/workflows/*.yml`: the lint/test/build invocations there are ground truth, mirror them.
  - Monorepo layout: workspaces (`package.json` `workspaces`, `pnpm-workspace.yaml`, uv `[tool.uv.workspace]` members, Cargo workspace). If per-package test commands are needed, list them.
  - If you genuinely cannot determine a command, write a clearly marked `<!-- TODO: fill in the test command -->` rather than guessing.
- **Conventions** (`{{CONVENTIONS}}`): only conventions you can actually observe (a linter config, `.editorconfig`, a formatter, an existing style). Do not invent house rules and do not import another project's voice (no em-dash bans, no specific test runner) unless the repo shows it. The `AGENTS.md` template already frames section 4 as "edit freely," so seed it thin and let the user add their own.
- **File map** (`{{FILE_MAP}}`): 3-8 of the most load-bearing files an agent would repeatedly need, one line of purpose each.
- **Current state** (`{{CURRENT_STATE}}`, standard/team): a short description of what exists today, organized by theme or subsystem. This is the roadmap's 30,000 ft layer.

### Step 4: fill the templates and write them, never clobbering

Fill each template for the chosen tier and write it. Use today's date (ISO `YYYY-MM-DD`) for `{{DATE}}` and `created:` examples. Keep prose in sentence case with relative markdown links.

| Template | Writes to | Tier | Placeholders |
|---|---|---|---|
| `AGENTS.md.tmpl` | `AGENTS.md` | all | `{{OVERVIEW}}`, `{{COMMANDS}}`, `{{CONVENTIONS}}`, `{{FILE_MAP}}` |
| `tasks-README.md.tmpl` | `.tasks/README.md` | all | none |
| `_TEMPLATE.md.tmpl` | `.tasks/_TEMPLATE.md` | all | none (it is the blank template) |
| `validate.py` | `.tasks/validate.py` | team (copy verbatim) | none |
| `ROADMAP.md.tmpl` | `ROADMAP.md` | standard, team | `{{DATE}}`, `{{CURRENT_STATE}}` |
| `CHANGELOG.md.tmpl` | `CHANGELOG.md` | standard, team | `{{PROJECT_NAME}}` |
| `CLAUDE.md.tmpl` | `CLAUDE.md` | all | none |
| `copilot-instructions.md.tmpl` | `.github/copilot-instructions.md` | opt-in | none |
| `cursor-rule.mdc.tmpl` | `.cursor/rules/agents.mdc` | opt-in | none |

Handle each case:

- **New file**: write the filled template.
- **`.tasks/` directory**: create `.tasks/`, `.tasks/done/`, `.tasks/README.md`, `.tasks/_TEMPLATE.md`, and an empty `.tasks/done/.gitkeep` so the empty dir is committable. At team tier also copy `validate.py` in verbatim.
- **A target file already exists** (`AGENTS.md`, `ROADMAP.md`, `CHANGELOG.md`): do not overwrite. Show what the scaffold would add and offer to merge the missing sections into their file, or write the new version alongside as `AGENTS.scaffold.md` for them to reconcile. Let them choose.
- **`CLAUDE.md` already exists**: if it already points at `AGENTS.md`, leave it. If it has real content, offer to prepend a one-line pointer to `AGENTS.md`. Only write the pointer-only `CLAUDE.md` when none exists.
- **Pointer pick-list**: `AGENTS.md` is canonical and Cursor, Codex, and OpenCode read it natively, so most repos need only the `CLAUDE.md` pointer. Do not reflexively create `.cursorrules` (legacy). Offer `.github/copilot-instructions.md` and `.cursor/rules/agents.mdc` only if the user uses those tools; mention them as available.

### Step 5: re-run (upgrade, do not clobber)

If Step 1.2 found `.tasks/.scaffold.json`, this is an upgrade, not a fresh scaffold. Read the manifest (its `tier`, `version`, `files`). Then:

1. Report what tier and version the repo is on versus this skill's version.
2. Offer **repair/upgrade** (default) or **fresh**:
   - **repair/upgrade**: add only the files that are missing or belong to a higher tier the user now wants; refresh `.tasks/_TEMPLATE.md` and `.tasks/validate.py` to the current version if they are unmodified from a prior scaffold; never touch task files the user has authored, and never rewrite `AGENTS.md` prose the user has edited (offer a diff of new template sections instead).
   - **fresh**: only if the user explicitly wants to start over; back up existing files first.
3. Show a concrete diff of what will change before writing.

### Step 6: migrate a pre-existing tracker (dry-run first)

If Step 1.4 found a tracker, do not silently create a parallel system. Present the proposed migration as a **dry run** and get confirmation before writing:

1. **Show the mapping** as a diff/plan: which existing items become `.tasks/` files, which completed items become `CHANGELOG.md` lines, and how groupings map to `ROADMAP.md` Features. Preserve wording; note provenance (e.g. "Seeded YYYY-MM-DD from the former `TODO.md`").
2. **Archive the source before writing**: copy the original to `<name>.archived.md` (or leave a one-line pointer redirecting to the new location). Never delete the source until its content is confirmed migrated, and only delete with explicit user say-so.
3. Offer the three outcomes and let the user pick, one tracker per repo being the goal:
   - **Migrate** (usually best): port contents in, then retire the old file.
   - **Adopt**: keep the existing file as canonical and point `AGENTS.md` at it by its real name instead of forcing `ROADMAP.md`/`CHANGELOG.md`.
   - **Coexist**: scaffold anyway and leave the old one, only if the user explicitly wants both. Warn that two trackers drift.
   For an out-of-repo tracker (GitHub Issues, Linear, Jira, Notion), you cannot migrate it: acknowledge it, ask whether this file-based system replaces or complements it, and record that boundary in `AGENTS.md` so agents know which is authoritative.

### Step 7: write the manifest and make it git-safe

1. **Write `.tasks/.scaffold.json`** so future runs are idempotent. Seed `id_high_water` from any tasks that already exist (scan `.tasks/` and `.tasks/done/` for the highest `NNNN` per type), so ids never collide on adoption:

   ```json
   {
     "generator": "init-worktracking",
     "version": "1.0.0",
     "tier": "standard",
     "created": "YYYY-MM-DD",
     "files": ["AGENTS.md", "CLAUDE.md", ".tasks/README.md", ".tasks/_TEMPLATE.md", "ROADMAP.md", "CHANGELOG.md"],
     "id_high_water": {"bug": 0, "feat": 0, "chore": 0, "epic": 0}
   }
   ```

2. **Git-safety**: `.tasks/` must be tracked by git, or parallel worktree-isolated agents silently diverge from the main checkout. Check `.gitignore` does not exclude `.tasks/`, `ROADMAP.md`, `CHANGELOG.md`, or `AGENTS.md`. If any is ignored, flag it and offer a negating rule. Do not commit anything yourself unless the user asks.
3. **team tier CI/pre-commit**: offer to wire `python .tasks/validate.py` into the repo's existing CI (add a step to the lint/test workflow) or a pre-commit hook. Do not force it; show the snippet and let the user place it.

### Step 8: report and offer a first task

Summarize what was created and what was skipped because it existed. Then offer, but do not automatically do, the natural next step: author one or two real task files for this repo. Prefer handing off to the `new-task` skill, which authors them at the gold-standard bar (honest `touched_files`, a real acceptance command, collision-safe ids). If `new-task` is not available, copy `_TEMPLATE.md` and fill it for a known bug or feature so the user sees the format applied to their actual work. Run `python .tasks/validate.py` to confirm the seed is clean.

## Notes

- This skill scaffolds structure. It does not invent work items unless asked.
- It pairs with `new-task` (author task files upstream), `fix-batch` (spin up parallel agents over a batch of task files), and `reconcile-worktrees` (merge their results back). Mention these if the user's goal is parallel execution.
- Everything is markdown and file-based, plus one stdlib-only Python checker. No database, no service dependency: that portability is the whole point.
- The `AGENTS.md` section 4 conventions are deliberately labeled "edit freely" so an adopter is never saddled with rules they did not choose. Do not hardcode your own house style into a scaffolded repo.
