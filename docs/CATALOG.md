# Skill catalog

The kit is organized by how broadly a skill is worth sharing. The axis is deliberate: broadly-useful skills go in the public kit; hyper-specific personal skills stay out and serve as portfolio demos instead.

A skill is only listed as **shipped** once it lives under [`.agents/skills/`](../.agents/skills/) and has been used and iterated on for real. Everything else is **planned**, and stays planned until it has earned its place. This is the same "seed by inspection, not speculation" principle the skills themselves follow.

## Tier A: broadly shareable (the public kit)

| Skill | Status | What it does |
|---|---|---|
| `init-worktracking` | shipping (Phase 1) | Scaffold a spec-driven, low-context work-tracking system (`AGENTS.md`, `.tasks/`, `ROADMAP.md`, `CHANGELOG.md`) into any repo, at a chosen footprint tier, seeded by inspecting the repo. |
| `new-task` | shipping (Phase 2) | Turn a rough idea, bug, or roadmap Feature into one or more atomic, mechanically-verifiable task files at the gold-standard bar. The upstream that feeds `fix-batch`. |
| `fix-batch` | shipped | Dispatch a batch of independent task files to parallel worktree-isolated agents, with a mandatory verification pass. Ported in-kit (`feat-0005`), blessed after a live run. |
| `reconcile-worktrees` | shipped | Safely consolidate isolated agent worktrees back into the main checkout without blind merges. Ported in-kit (`feat-0006`), blessed after a live run. |
| `project-bootstrap` | shipped | The umbrella front door: language-aware scaffold (gitignore, editorconfig, linter/formatter from a swappable house code-style layer, license, README stub) that then calls `init-worktracking`. |
| `pr-describe` | shipped | Draft a PR body and a changelog entry from a branch's diff (or the working tree), in the target repo's own changelog format. Draft-only: never touches GitHub. |
| `code-review` | shipped | House-style code review with an explicit rubric and severities, composing the swappable `review-quality` lens (moonray's quality-lens pattern). Report-only. |
| `agent-handoff` | shipped | Turn the current session into a self-contained, execution-ready brief a fresh session or subagent can run cold. Dogfooded in the in-kit fold-in brief and blessed after user sign-off (`feat-0009`). |
| `human-handoff` | shipped | Package project state for a person (partner, client, or teammate) as a tuned document or message, with client-facing redaction. Dogfooded with the in-kit partner status update and blessed after user sign-off (`feat-0010`). |
| `doc-author` | shipped | Write new, code-grounded Markdown docs (READMEs, architecture with Mermaid, guides, ADRs) matched to a reader; composes with `project-bootstrap`/`init-worktracking`. Dogfooded by authoring the in-kit architecture guide and blessed after user sign-off (`feat-0011`). |
| `doc-revise` | shipped | Revise existing Markdown docs surgically: reconcile with code, fix cross-doc links, keep a doc set consistent, without flattening the author's voice. Dogfooded by the README and status-document consistency pass, then blessed after user sign-off (`feat-0012`). |
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

The author's Content OS pipeline: `produce`, `clip-machine`, `repurpose`, `video-editing`, `video-cutting`, `episode-brief`, `youtube-transcript`, `idea-discovery`. These are showcase and portfolio demos ("look what is possible"), not plug-and-play for others. They live in their own repo, not here.

## The two building blocks the whole kit reuses

- **`AGENTS.md`** as the canonical, cross-tool instruction file.
- **A harness-agnostic `SKILL.md` body** plus thin generated per-harness adapters. This is what makes any skill above portable.
