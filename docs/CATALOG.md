# Skill catalog

The kit is organized by how broadly a skill is worth sharing. The axis is deliberate: broadly-useful skills go in the public kit; hyper-specific personal skills stay out and serve as portfolio demos instead.

A skill is only listed as **shipped** once it lives under [`.agents/skills/`](../.agents/skills/) and has been used and iterated on for real. Everything else is **planned**, and stays planned until it has earned its place. This is the same "seed by inspection, not speculation" principle the skills themselves follow.

## Tier A: broadly shareable (the public kit)

| Skill | Status | What it does |
|---|---|---|
| `init-worktracking` | shipped | Scaffold a spec-driven, low-context work-tracking system (`AGENTS.md`, `.tasks/`, `ROADMAP.md`, `CHANGELOG.md`) into any repo, at a chosen footprint tier, seeded by inspecting the repo. |
| `new-task` | shipped | Turn a rough idea, bug, or roadmap Feature into one or more atomic, mechanically-verifiable task files at the gold-standard bar. The upstream that feeds `fix-batch`. |
| `fix-batch` | shipped | Dispatch a batch of independent task files to parallel worktree-isolated agents, with a mandatory verification pass. Ported in-kit (`feat-0005`), blessed after a live run. |
| `reconcile-worktrees` | shipped | Safely consolidate isolated agent worktrees back into the main checkout without blind merges. Ported in-kit (`feat-0006`), blessed after a live run. |
| `project-bootstrap` | shipped | The umbrella front door: language-aware scaffold (gitignore, editorconfig, linter/formatter from a swappable house code-style layer, license, README stub) that then calls `init-worktracking`. |
| `pr-describe` | shipped | Draft a PR body and a changelog entry from a branch's diff (or the working tree), in the target repo's own changelog format. Draft-only: never touches GitHub. |
| `house-review` | shipped | House-style code review with an explicit rubric and severities, composing the swappable `review-quality` lens (moonray's quality-lens pattern). Report-only. |
| `agent-handoff` | shipped | Turn the current session into a self-contained, execution-ready brief a fresh session or subagent can run cold. Dogfooded in the in-kit fold-in brief and blessed after user sign-off (`feat-0009`). |
| `human-handoff` | shipped | Package project state for a person (partner, client, or teammate) as a tuned document or message, with client-facing redaction. Dogfooded with the in-kit partner status update and blessed after user sign-off (`feat-0010`). |
| `doc-author` | shipped | Write new, code-grounded Markdown docs (READMEs, architecture with Mermaid, guides, ADRs) matched to a reader; composes with `project-bootstrap`/`init-worktracking`. Dogfooded by authoring the in-kit architecture guide and blessed after user sign-off (`feat-0011`). |
| `doc-revise` | shipped | Revise existing Markdown docs surgically: reconcile with code, fix cross-doc links, keep a doc set consistent, without flattening the author's voice. Dogfooded by the README and status-document consistency pass, then blessed after user sign-off (`feat-0012`). |
| `ci-scaffold` | planned (hold) | Generate CI (lint + test + build + release) matched to the detected stack. Hold until used twice. |
| `release-cut` | planned (hold) | Version bump, changelog roll-up, tag, notes. Hold until used twice. |

## The contract-driven delivery spine (Epic B, in progress)

These skills make the roadmap's contract-driven delivery spine real. All eight were dogfooded on real in-kit work before being blessed: seven on 2026-07-24 and `doc-sync` on 2026-07-25. Four of them (`spec-quality`, `spec-plan-readiness`, `test-quality`, `spec-conformance`) were folded in from `repoprompt-workflows` (Balarama Bosch, MIT) and house-styled; provenance is recorded in [`NOTICE`](../NOTICE). Four (`spec-author`, `test-author`, `verifier-agent`, `doc-sync`) were authored in the kit by extracting the discipline from the upstream workflows into portable skills. This is where the kit dogfoods its own spine, with specifications living under [`docs/spec/`](spec/) and the resulting tests under [`tests/`](../tests/).

With `verifier-agent` blessed, the core spec-to-reconcile loop is complete: an idea becomes a specification, the specification is gated, decomposed, implemented, tested, audited, and independently verified before anything lands. `doc-sync` closes the documentation half of that loop, and the spine continues at the roadmap level with `user-testing`, which is not built yet.

| Skill | Status | What it does |
|---|---|---|
| `spec-author` | shipped (Epic B) | Drafts a persistent behavioral spec from a raw idea, composes `spec-quality` to self-check to `ready`, writes it under `docs/spec/` as `status: draft`, and stops for human approval before `new-task` decomposes it. |
| `spec-quality` | shipped (Epic B) | Report-only lens keeping scenario-based specs contract-level, observable, non-redundant, grounded in repo context, and free of implementation planning. Composed by `spec-author` and `test-author`. |
| `spec-plan-readiness` | shipped (Epic B) | Deterministic go/no-go gate: blocks tests, code, and delegation until an approved spec plus an ordered, repo-grounded `.tasks/` plan are implementable. |
| `test-quality` | shipped (Epic B) | Report-only lens for choosing the lowest faithful test layer, naming the plausible defect each test protects, and asserting real observable outcomes. Composed by `test-author`. |
| `spec-conformance` | shipped (Epic B) | Audits an implementation against its spec into a positive Conformed/Diverged/Not-built matrix. Composes into `fix-batch` verification, and is composed by `verifier-agent`. |
| `test-author` | shipped (Epic B) | Derives runnable tests from an approved spec's scenarios (tagged by `S-NNN`), matching the repo's own test framework and composing `test-quality` for layer and oracle. Acceptance and characterization modes; writes tests, never production code. |
| `verifier-agent` | shipped (Epic B) | Independently verifies an implementation before reconciliation: runs the declared commands, composes `spec-conformance` so a contract divergence fails the run even when tests pass, maps each acceptance criterion to evidence, and returns a deterministic pass, fail, or blocked verdict. Verifies and reports; never edits what it verifies. |
| `doc-sync` | shipped (Epic B) | Detects documentation drift by checking prose claims against repository facts, classifying every document as current-state (correctable with approval), contract (report-only, human-owned) or ledger (skipped). Dry run is the default and detection never changes a file. Composes `doc-revise` for editing discipline. Authored in-kit against `docs/spec/doc-sync.md`, dogfooded on this repository's own documentation (`feat-0020`), and blessed after its apply path repointed three dangling references (`chore-0006`). |

## Tier B: semi-scalable (great for teams and clients)

| Skill | Status | What it does |
|---|---|---|
| `repo-explainer` | planned | A "start here" guided tour of an unfamiliar codebase. Strong for client onboarding. |
| `sop-drafter` | planned | Turn a described workflow into a documented standard operating procedure. |
| `security-audit` | planned | Repeatable dependency and secret scan with a written summary. |
| `adr` | planned | Architecture decision records / decision log entries. |

## Tier C: hyper-specific (personal, stays out of the shared kit)

The author's Content OS pipeline: `produce`, `clip-machine`, `repurpose`, `video-editing`, `video-cutting`, `episode-brief`, `youtube-transcript`, `idea-discovery`. These are showcase and portfolio demos ("look what is possible"), not plug-and-play for others. They live in their own repo, not here.

## The two building blocks the whole kit reuses

- **`AGENTS.md`** as the canonical, cross-tool instruction file.
- **A harness-agnostic `SKILL.md` body** plus thin generated per-harness adapters. This is what makes any skill above portable.
