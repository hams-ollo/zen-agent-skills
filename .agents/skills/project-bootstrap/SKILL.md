---
name: project-bootstrap
description: Bootstrap a new or bare repository with a sane, stack-matched baseline, then hand off to init-worktracking for work tracking. Detects the language and package manager, then lays down .gitignore, .editorconfig, a linter/formatter config, a LICENSE, and a README stub, without clobbering anything that already exists. Use when the user says "set up a new repo", "scaffold this project", "fire up my harness", "give me a starting point", "bootstrap this", or points at an empty or nearly-empty directory they want turned into a real project. This is the front door of the Zen Starter Kit: it calls init-worktracking so the repo comes up already tracked.
---

# project-bootstrap

The umbrella "fire up my harness" skill. Turn a new or bare repository into a real project with a sane baseline, then bring up work tracking. It does not reimplement tracking; it calls `init-worktracking` for that. Think of it as the front door and `init-worktracking` as the room behind it.

## What it lays down

A minimal, widely-agreed baseline, matched to the detected stack. Never a heavy opinionated framework:

- **`.gitignore`** for the detected language(s), plus OS/editor cruft.
- **`.editorconfig`** for consistent whitespace across editors.
- **Linter/formatter config**: for Python, `ruff` (lint + format); for JS/TS, `prettier` + `eslint`. Emitted from the [house code-style layer](#house-code-style-layer), only the config, not an install.
- **`LICENSE`**: ask which; default MIT with the user's name/handle.
- **`README.md`** stub: project name, one-line purpose, setup and test placeholders.
- Then it **calls `init-worktracking`** to add `AGENTS.md`, `.tasks/`, and (by tier) `ROADMAP.md`/`CHANGELOG.md`.

## Design choices

These decisions are settled (resolved with the author); these four are not up for re-litigation:

- **First-class stacks are Python and JavaScript/TypeScript.** Everything else gets a generic baseline plus a clearly marked `<!-- TODO -->`. Add stacks as real need appears, not speculatively.
- **Configs, not installs.** The skill writes config files; it does not run `npm install`, `uv add`, or `pre-commit install`. It offers those commands for the user to run.
- **pre-commit is opt-in**, not default, so small repos are not burdened.
- **Linter/formatter configs come from the house code-style layer** in [`templates/`](templates/), not bare tool defaults. They are opinionated but documented, adjustable at three levels (confirm-time, per-repo, kit-wide), and never overwrite a config the repo already has. See [House code-style layer](#house-code-style-layer).

## House code-style layer

The linter/formatter defaults live in [`templates/`](templates/) as a swappable house
layer, the code-conventions parallel to the kit's prose module
[`.agents/rules/house-style.md`](../../rules/house-style.md). Full detail and rationale are
in [`templates/house-code-style.md`](templates/house-code-style.md); the essentials:

- **Templates are stored dotless** so the kit's own tooling does not apply them. Each maps
  to an emitted filename: `ruff.toml` -> `[tool.ruff]` in `pyproject.toml` (or `ruff.toml`
  if no manifest); `prettierrc.json` -> `.prettierrc`; `eslint.config.mjs` ->
  `eslint.config.mjs`; `editorconfig` -> `.editorconfig`.
- **The house defaults** are: ruff `line-length = 100`, `target-version = "py311"`,
  double-quote format, lint set `E, F, I, UP, B`; prettier `printWidth: 100`, `semi: true`,
  `singleQuote: true`, `trailingComma: "all"`, `tabWidth: 2`; editorconfig UTF-8/LF/final
  newline/trim, 4-space Python and 2-space web.
- **Three ways to adjust**, in increasing durability: (1) at the confirm step, for this
  repo; (2) per repo, by editing the emitted config afterward, or simply by having a config
  already present, which is never overwritten; (3) kit-wide, by editing the template files
  once so every future run inherits it. Power users can replace a template outright.

The layer is defaults, not mandates. It is opinionated so repos come up consistent, and
editable so no one is stuck with a choice they dislike.

## Procedure

### Step 1: survey

1. Confirm the working directory is a git repository (`git rev-parse --is-inside-work-tree`). If not, offer to `git init`.
2. List what already exists. **Never overwrite**: any file below that is already present is left alone and reported, or offered as an alongside `*.bootstrap` version for the user to reconcile.
3. Detect the stack from what is present, or ask if the directory is truly empty:
   - Python: `pyproject.toml`, `setup.py`, `requirements.txt`, `*.py`. Package manager from lockfile (`uv.lock` -> uv, `poetry.lock` -> poetry, else pip).
   - JS/TS: `package.json`, `tsconfig.json`, `*.ts`/`*.js`. Package manager from lockfile (`pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`).
   - Other or empty: ask the user what they intend to build; fall back to a generic baseline.

### Step 2: confirm choices

State what you will generate and the detected stack, and confirm: the LICENSE type (default MIT) and copyright name, whether to include pre-commit, and whether to proceed to `init-worktracking` afterward (and at which tier). Surface the [house code-style](#house-code-style-layer) values (line length, quote style, indent) so the user can adjust them for this repo before writing (adjustment Level 1). Let the user adjust before writing.

### Step 3: write the baseline (never clobbering)

For each baseline file that does not already exist, write it matched to the stack:

- `.gitignore`: language patterns (for Python: `__pycache__/`, `.venv/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`; for JS/TS: `node_modules/`, `dist/`, `.turbo/`, build output) plus OS/editor entries.
- `.editorconfig`: emitted from the house layer's [`editorconfig`](templates/editorconfig) template (`root = true`, UTF-8, LF, final newline, trimmed trailing whitespace, 4-space Python and 2-space web).
- Linter/formatter config: emitted from the [house code-style layer](#house-code-style-layer), not written inline. For Python, apply [`templates/ruff.toml`](templates/ruff.toml) as a `[tool.ruff]` block in `pyproject.toml` (or as `ruff.toml` if no manifest); for JS/TS, emit [`templates/prettierrc.json`](templates/prettierrc.json) as `.prettierrc` and, if the user wants linting, [`templates/eslint.config.mjs`](templates/eslint.config.mjs) as `eslint.config.mjs`. Apply the values as confirmed in Step 2.
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
- Linter/formatter opinions live in the [house code-style layer](#house-code-style-layer), edit-once and swappable, never clobbering a repo's existing config.
- It is the front door of the kit: `project-bootstrap` -> `init-worktracking` -> `new-task` -> `fix-batch` -> `reconcile-worktrees`.
