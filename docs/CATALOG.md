# Skill catalog

The kit is organized by how broadly a skill is worth sharing. The axis is deliberate: broadly-useful skills go in the public kit; hyper-specific personal skills stay out and serve as portfolio demos instead.

A skill is only listed as **shipped** once it lives under [`.agents/skills/`](../.agents/skills/) and has been used and iterated on for real. Everything else is **planned**, and stays planned until it has earned its place. This is the same "seed by inspection, not speculation" principle the skills themselves follow.

## Tier A: broadly shareable (the public kit)

| Skill | Status | What it does |
|---|---|---|
| `init-worktracking` | shipping (Phase 1) | Scaffold a spec-driven, low-context work-tracking system (`AGENTS.md`, `.tasks/`, `ROADMAP.md`, `CHANGELOG.md`) into any repo, at a chosen footprint tier, seeded by inspecting the repo. |
| `new-task` | shipping (Phase 2) | Turn a rough idea, bug, or roadmap Feature into one or more atomic, mechanically-verifiable task files at the gold-standard bar. The upstream that feeds `fix-batch`. |
| `fix-batch` | shipped (external) | Dispatch a batch of independent task files to parallel worktree-isolated agents, with a mandatory verification pass. Lives in the author's existing skill set. |
| `reconcile-worktrees` | shipped (external) | Safely consolidate isolated agent worktrees back into the main checkout without blind merges. |
| `project-bootstrap` | draft (needs iteration) | The umbrella front door: language-aware scaffold (gitignore, editorconfig, linter/formatter, license, README stub) that then calls `init-worktracking`. First draft landed (`feat-0001`); not yet blessed as shipped. |
| `pr-describe` | planned | Draft a PR body and a changelog entry from the diff, in the kit's changelog format. |
| `code-review` | planned | House-style code review with an explicit rubric and severities. Composable, mirroring the quality-lens pattern (a review-quality lens a workflow inlines). |
| `ci-scaffold` | planned (hold) | Generate CI (lint + test + build + release) matched to the detected stack. Hold until used twice. |
| `release-cut` | planned (hold) | Version bump, changelog roll-up, tag, notes. Hold until used twice. |

## Tier B: semi-scalable (great for teams and clients)

| Skill | Status | What it does |
|---|---|---|
| `repo-explainer` | planned | A "start here" guided tour of an unfamiliar codebase. Strong for client onboarding. |
| `sop-drafter` | planned | Turn a described workflow into a documented standard operating procedure. |
| `security-audit` | planned | Repeatable dependency and secret scan with a written summary. |
| `test-author` | planned | Characterization tests for legacy code with no coverage. |
| `adr` | planned | Architecture decision records / decision log entries. |

## Tier C: hyper-specific (personal, stays out of the shared kit)

The author's Content OS pipeline: `produce`, `cut`, `clips`, `edit`, `brief`, `idea-discovery`. These are showcase and portfolio demos ("look what is possible"), not plug-and-play for others. They live in their own repo, not here.

## The two building blocks the whole kit reuses

- **`AGENTS.md`** as the canonical, cross-tool instruction file.
- **A harness-agnostic `SKILL.md` body** plus thin generated per-harness adapters. This is what makes any skill above portable.
