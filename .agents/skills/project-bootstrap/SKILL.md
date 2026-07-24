---
name: project-bootstrap
description: Bootstrap a new or bare repository with a sane, stack-matched baseline, then hand off to init-worktracking for work tracking. Detects the language and package manager, then lays down .gitignore, .editorconfig, a linter/formatter config, a LICENSE, and a README stub, without clobbering anything that already exists. Use when the user says "set up a new repo", "scaffold this project", "fire up my harness", "give me a starting point", "bootstrap this", or points at an empty or nearly-empty directory they want turned into a real project. This is the front door of the Zen Starter Kit: it calls init-worktracking so the repo comes up already tracked. First-draft skill, iterate before treating as final.
---

# project-bootstrap

The umbrella "fire up my harness" skill. Turn a new or bare repository into a real project with a sane baseline, then bring up work tracking. It does not reimplement tracking; it calls `init-worktracking` for that. Think of it as the front door and `init-worktracking` as the room behind it.

## What it lays down

A minimal, widely-agreed baseline, matched to the detected stack. Never a heavy opinionated framework:

- **`.gitignore`** for the detected language(s), plus OS/editor cruft.
- **`.editorconfig`** for consistent whitespace across editors.
- **Linter/formatter config**: for Python, `ruff` (lint + format); for JS/TS, `prettier` + `eslint`. Only the config, not an install.
- **`LICENSE`**: ask which; default MIT with the user's name/handle.
- **`README.md`** stub: project name, one-line purpose, setup and test placeholders.
- Then it **calls `init-worktracking`** to add `AGENTS.md`, `.tasks/`, and (by tier) `ROADMAP.md`/`CHANGELOG.md`.

## Design choices this draft makes (flagged for iteration)

These are deliberate first-draft decisions. Revisit them as the skill is used:

- **First-class stacks are Python and JavaScript/TypeScript.** Everything else gets a generic baseline plus a clearly marked `<!-- TODO -->`. Add stacks as real need appears, not speculatively.
- **Configs, not installs.** The skill writes config files; it does not run `npm install`, `uv add`, or `pre-commit install`. It offers those commands for the user to run.
- **pre-commit is opt-in**, not default, so small repos are not burdened.
- **Opinionation is low.** ruff/prettier defaults, no exotic rules. The generated files are meant to be edited.

## Procedure

### Step 1: survey

1. Confirm the working directory is a git repository (`git rev-parse --is-inside-work-tree`). If not, offer to `git init`.
2. List what already exists. **Never overwrite**: any file below that is already present is left alone and reported, or offered as an alongside `*.bootstrap` version for the user to reconcile.
3. Detect the stack from what is present, or ask if the directory is truly empty:
   - Python: `pyproject.toml`, `setup.py`, `requirements.txt`, `*.py`. Package manager from lockfile (`uv.lock` -> uv, `poetry.lock` -> poetry, else pip).
   - JS/TS: `package.json`, `tsconfig.json`, `*.ts`/`*.js`. Package manager from lockfile (`pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`).
   - Other or empty: ask the user what they intend to build; fall back to a generic baseline.

### Step 2: confirm choices

State what you will generate and the detected stack, and confirm: the LICENSE type (default MIT) and copyright name, whether to include pre-commit, and whether to proceed to `init-worktracking` afterward (and at which tier). Let the user adjust before writing.

### Step 3: write the baseline (never clobbering)

For each baseline file that does not already exist, write it matched to the stack:

- `.gitignore`: language patterns (for Python: `__pycache__/`, `.venv/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`; for JS/TS: `node_modules/`, `dist/`, `.turbo/`, build output) plus OS/editor entries.
- `.editorconfig`: `root = true`, UTF-8, LF, final newline, trimmed trailing whitespace, and per-language indent (4 spaces Python, 2 spaces JS/TS/JSON/MD).
- Linter/formatter config: for Python a `[tool.ruff]` block in `pyproject.toml` (or `ruff.toml` if no manifest); for JS/TS a `.prettierrc` and a minimal `eslint` config appropriate to the version present. Keep rules close to defaults.
- `LICENSE`: the chosen license text with year and holder filled.
- `README.md`: project name (repo dir or manifest name), a one-line purpose the user provides or a placeholder, and setup/test sections seeded from the detected commands (mirror what `init-worktracking` would detect).

For any file that already exists, do not touch it; report it as skipped and, if it materially differs from what you would generate, offer an alongside version.

### Step 4: hand off to init-worktracking

Invoke the `init-worktracking` skill to add the work-tracking system, passing the tier chosen in Step 2 (default `standard`). Do not duplicate its logic here. If `init-worktracking` is not available in this environment, say so and point the user to it rather than scaffolding a partial tracking system by hand.

### Step 5: report and offer next commands

Summarize what was written and what was skipped. Then surface, but do not run, the install/setup commands the user should execute themselves, for example:

- Python (uv): `uv sync`
- JS/TS (pnpm): `pnpm install`
- pre-commit (if chosen): `pre-commit install`

Offer, as the natural next step, to author the repo's first task with `new-task`.

## Notes

- This skill only writes config and calls `init-worktracking`. It installs nothing and runs no package manager, so it is safe in any environment.
- It is the front door of the kit: `project-bootstrap` -> `init-worktracking` -> `new-task` -> `fix-batch` -> `reconcile-worktrees`.
- Draft status: the stack list, config opinions, and pre-commit default are all first-guess decisions. Iterate them against real projects before treating this skill as final.
