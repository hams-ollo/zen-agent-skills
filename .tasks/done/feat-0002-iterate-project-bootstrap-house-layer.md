---
id: feat-0002
title: Iterate project-bootstrap with a swappable house code-style layer
type: feat
status: done
priority: P1
parent: "ROADMAP Epic A #1 project-bootstrap"
depends_on: [feat-0001]
touched_files:
  - .agents/skills/project-bootstrap/SKILL.md
  - .agents/skills/project-bootstrap/templates/house-code-style.md
  - .agents/skills/project-bootstrap/templates/ruff.toml
  - .agents/skills/project-bootstrap/templates/prettierrc.json
  - .agents/skills/project-bootstrap/templates/eslint.config.mjs
  - .agents/skills/project-bootstrap/templates/editorconfig
created: 2026-07-24
---

## Problem

The `project-bootstrap` draft (`feat-0001`) left four design questions open. The user
resolved them: first-class stacks stay Python + JS/TS only; the skill stays configs-only
(offers install commands, runs nothing); pre-commit stays opt-in; and, the substantive
change, the generated linter/formatter configs should reflect the user's **house style
as the default** rather than bare tool defaults, while remaining easy to customize,
especially for power users.

Three answers confirm the current draft. The fourth requires new structure: a documented,
swappable house code-style layer so that editing one place changes every future bootstrap
(a kit-wide default), the values are still adjustable at confirm-time and per-repo, and
any config already present in the target repo is never clobbered.

## Scope

**In scope:** add a `templates/` house code-style layer to the skill (ruff, prettier,
eslint, editorconfig, plus a doc explaining the layer and its three adjustment levels);
revise `SKILL.md` to fold in the three settled decisions and emit the linter/formatter
configs from the house layer with never-clobber preserved.

**Out of scope:** blessing the skill or changing its "draft" status in `ROADMAP.md` /
`docs/CATALOG.md` (that waits for explicit user sign-off after review); adding Go/Rust or
any other stack; running installs; making pre-commit default-on; modifying the two blessed
skills, `AGENTS.md`, `README.md`, or `.agents/rules/house-style.md`.

## Implementation notes

- House layer templates use dotless names; `SKILL.md` maps each to its emitted filename.
- Approved starter values: ruff `line-length = 100`, `target-version = "py311"`,
  `[format] quote-style = "double"`, `[lint] select = ["E","F","I","UP","B"]`; prettier
  `printWidth: 100`, `semi: true`, `singleQuote: true`, `trailingComma: "all"`,
  `tabWidth: 2`; editorconfig unchanged from the draft (4-space Python / 2-space web).
- `.gitignore` stays stack-generated inline in the body (factual, not taste).
- The house code-style layer is the code-conventions parallel to the kit's prose module
  `.agents/rules/house-style.md`.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py
    python .tasks/validate.py --strict

- [ ] `templates/` exists with `ruff.toml`, `prettierrc.json`, `eslint.config.mjs`,
      `editorconfig`, and `house-code-style.md`.
- [ ] `ruff.toml` parses as TOML and `prettierrc.json` parses as JSON.
- [ ] `SKILL.md` documents the house layer, the three adjustment levels, and never-clobber,
      and maps each template to its emitted filename.
- [ ] `scripts/validate-skills.py` exits 0; `.tasks/validate.py --strict` exits 0.
- [ ] SKILL.md body stays under the 500-line progressive-disclosure guideline.

## Definition of done

- [ ] Acceptance commands pass locally.
- [ ] Conventions in AGENTS.md section 6 followed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
- [ ] Skill left as a draft; ROADMAP/CATALOG status unchanged pending user sign-off.
