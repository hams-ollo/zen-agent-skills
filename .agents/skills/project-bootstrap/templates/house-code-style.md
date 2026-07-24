# House code-style layer

This directory is `project-bootstrap`'s **house code-style layer**: the concrete
linter and formatter defaults the skill writes into a repo. It is the code-conventions
parallel to the kit's prose module [`house-style.md`](../../../rules/house-style.md).
That file governs writing (no em-dashes, sentence-case headings); this layer governs code
(line length, quote style, indentation).

Everything here is a **default, not a mandate**. It is designed to be edited, overridden,
or replaced wholesale.

## What it emits

| Template file (dotless) | Emitted into the target repo as | For |
|---|---|---|
| `ruff.toml` | `[tool.ruff]` in `pyproject.toml`, or `ruff.toml` if no manifest | Python lint + format |
| `prettierrc.json` | `.prettierrc` | JS/TS formatting |
| `eslint.config.mjs` | `eslint.config.mjs` (optional) | JS/TS linting |
| `editorconfig` | `.editorconfig` | whitespace, all files |

Template files are stored **dotless** so this kit's own editors and tools do not apply
them to the kit repo. The skill maps each one to its emitted (usually dot-prefixed) name.

## The house defaults

- **Python (ruff):** `line-length = 100`, `target-version = "py311"`, double-quote
  format, lint rule set `E, F, I, UP, B` (pycodestyle, pyflakes, isort, pyupgrade,
  bugbear).
- **JS/TS (prettier):** `printWidth: 100`, `semi: true`, `singleQuote: true`,
  `trailingComma: "all"`, `tabWidth: 2`.
- **eslint (optional):** recommended rules only; all formatting deferred to prettier so
  the two never fight.
- **.editorconfig:** UTF-8, LF, final newline, trimmed trailing whitespace; 4-space
  Python, 2-space web files.

`printWidth`/`line-length` are matched at 100 so Python and JS/TS wrap the same way.

## Three ways to adjust (in increasing durability)

1. **At bootstrap time.** The skill surfaces these values at its confirm step; change them
   for the current repo before anything is written.
2. **Per repo, after bootstrap.** The emitted config (`pyproject.toml`, `.prettierrc`, ...)
   is a normal file in the target repo. Edit it like any other config. And if a config
   already exists when you run the skill, it is **never overwritten** - your existing
   choices always win.
3. **Kit-wide, once.** Edit the template files in *this* directory. Every future
   `project-bootstrap` run then emits your baseline. This is the level that makes "adjust
   later" a one-place action instead of a per-repo chore. Power users can also drop in a
   replacement file to swap the layer entirely, the same way `house-style.md` is swappable.

## Configs only, never installs

The skill writes these files and nothing else. It does not run `ruff`, `prettier`,
`eslint`, or any package manager. It surfaces the install/setup commands for you to run
yourself, so it stays safe in any environment.
