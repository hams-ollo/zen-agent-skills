# Skill catalog

Every skill Zen Agent Skills ships, plus what is drafted, what is planned, and what is deliberately not built yet.

The kit is organized by how broadly a skill is worth sharing. The axis is deliberate: broadly-useful skills go in the public kit; hyper-specific personal skills stay out and serve as portfolio demos instead.

A skill is listed as **shipped** once it lives under [`.agents/skills/`](../.agents/skills/) and has been used and iterated on for real. A skill that is written and lives there but has not yet earned that is a **draft**, listed under [drafts](#drafts-built-but-not-blessed) rather than in a tier, because no install places it. A skill that is not written at all is **planned**, and stays planned until it has earned its place. This is the same "seed by inspection, not speculation" principle the skills themselves follow.

## Tier A: broadly shareable (the public kit)

| Skill | Status | What it does |
|---|---|---|
| `init-worktracking` | shipped | Scaffold a spec-driven, low-context work-tracking system (`AGENTS.md`, `.tasks/`, `ROADMAP.md`, `CHANGELOG.md`) into any repo, at a chosen footprint tier, seeded by inspecting the repo. |
| `new-task` | shipped | Turn a rough idea, bug, or roadmap Feature into one or more atomic, mechanically-verifiable task files at the gold-standard bar. The upstream that feeds `fix-batch`. |
| `fix-batch` | shipped | Dispatch a batch of independent task files to parallel worktree-isolated agents, with a mandatory verification pass. Every dispatched agent owes a fixed delegate report (including the validation command and its verbatim result), and a missing field blocks acceptance (`feat-0041`). Ported in-kit (`feat-0005`), blessed after a live run. |
| `reconcile-worktrees` | shipped | Safely consolidate isolated agent worktrees back into the main checkout without blind merges. A worktree whose delegate report does not meet `fix-batch`'s contract does not land (`feat-0041`). Ported in-kit (`feat-0006`), blessed after a live run. |
| `project-bootstrap` | shipped | The umbrella front door: language-aware scaffold (gitignore, editorconfig, linter/formatter from a swappable house code-style layer, license, README stub) that then calls `init-worktracking`. |
| `pr-describe` | shipped | Draft a PR body and a changelog entry from a branch's diff (or the working tree), in the target repo's own changelog format. Emits a GitHub closing reference for any task carrying an `external` issue id, so merging the PR closes the issue. Draft-only: never touches GitHub itself. |
| `house-review` | shipped | House-style code review with an explicit rubric and severities, composing the swappable `review-quality` lens (moonray's quality-lens pattern). An evidence gate drops any finding whose quoted code does not resolve against the file it cites, re-anchoring rather than dropping one whose quote has only moved, and every finding carries a stable signature so the same defect is countable across runs (`feat-0040`). Report-only. |
| `agent-handoff` | shipped | Turn the current session into a self-contained, execution-ready brief a fresh session or subagent can run cold. Dogfooded in the in-kit fold-in brief and blessed after user sign-off (`feat-0009`). |
| `human-handoff` | shipped | Package project state for a person (partner, client, or teammate) as a tuned document or message, with client-facing redaction. Dogfooded with the in-kit partner status update and blessed after user sign-off (`feat-0010`). |
| `doc-author` | shipped | Write new, code-grounded Markdown docs (READMEs, architecture with Mermaid, guides, ADRs) matched to a reader; composes with `project-bootstrap`/`init-worktracking`. Dogfooded by authoring the in-kit architecture guide and blessed after user sign-off (`feat-0011`). |
| `doc-revise` | shipped | Revise existing Markdown docs surgically: reconcile with code, fix cross-doc links, keep a doc set consistent, without flattening the author's voice. Dogfooded by the README and status-document consistency pass, then blessed after user sign-off (`feat-0012`). |
| `ci-scaffold` | planned (hold) | Generate CI (lint + test + build + release) matched to the detected stack. Hold until used twice. |
| `release-cut` | planned (hold) | Version bump, changelog roll-up, tag, notes. Hold until used twice. |

## The contract-driven delivery spine (Epic B, in progress)

These skills make the roadmap's contract-driven delivery spine real. All nine were dogfooded on real in-kit work before being blessed: seven on 2026-07-24, `doc-sync` on 2026-07-25, and `review-depth` on 2026-08-05. Four of them (`spec-quality`, `spec-plan-readiness`, `test-quality`, `spec-conformance`) were folded in from `repoprompt-workflows` (Balarama Bosch, MIT) and house-styled; provenance is recorded in [`NOTICE`](../NOTICE) and, since `feat-0043`, in a checkable provenance block inside each adapted file (see "What the kit borrows, and how you can check it" below). Four (`spec-author`, `test-author`, `verifier-agent`, `doc-sync`) were authored in the kit by extracting the discipline from the upstream workflows into portable skills. This is where the kit dogfoods its own spine, with specifications living under [`docs/spec/`](spec/) and the resulting tests under [`tests/`](../tests/).

With `verifier-agent` blessed, the core spec-to-reconcile loop is complete: an idea becomes a specification, the specification is gated, decomposed, implemented, tested, audited, and independently verified before anything lands. `doc-sync` closes the documentation half of that loop and `review-depth` decides how hard the review half looks. Where the spine goes next is no longer a single skill: it is about making its rules hold mechanically rather than by an agent remembering them. Two of those landed on 2026-08-05, an evidence gate so a finding must prove its citation (`feat-0040`) and a required evidence contract from every delegated agent (`feat-0041`). Repeat detection, so a review-fix loop cannot spin, is still open and waits on the finding signature the evidence gate now defines. Alongside them sits `user-testing`, which stays held until there is real user-facing work to author it against. The enforcement half of that shift already ships as the [hooks module](../.agents/hooks/README.md).

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
| `review-depth` | shipped (Epic B) | Chooses how hard to look before `house-review` looks: quick, standard, or deep, selected from a stated signal table (reviewable changed lines, directory spread, trust-boundary risk flags, blast radius, documentation-only scope) so two runs over the same diff reach the same depth and the reason is inspectable. An explicit user choice always overrides detection. Composes into `house-review` rather than duplicating its rubric, which lives in the `review-quality` lens. Blessed 2026-08-05; using it is what exposed the mode contradiction inside `house-review` that `chore-0024` then fixed. |

## Drafts: built but not blessed

A **draft** is written, lives under [`.agents/skills/`](../.agents/skills/), and is placed by no install profile, not even the one that asks for everything. That is the contribution bar made mechanical: a skill earns its place here only after it has been used and iterated on for real, so a freshly written one is held back until real work has exercised it, and `install.py` names what it withheld on every run rather than dropping it silently (`S-015` of [`docs/spec/install.md`](spec/install.md)).

Drafts are listed rather than omitted because both silent readings are wrong. A skill left out of this catalog reads as absent when it is in fact in the tree; the same skill listed in a tier beside the shipped ones reads as available when nothing will install it. What a draft still owes before it ships is tracked in [`ROADMAP.md`](../ROADMAP.md), which is builder-facing; this section only says that it exists and that you do not have it.

| Skill | Status | What it does |
|---|---|---|
| `agent-observatory` | draft | Answers questions that span more than one agent session (what is running, what a wave cost, which skills were used, what failed) by reading the local observatory store rather than one transcript at a time, and acts on a session only where the harness exposes the action. Never starts, resumes, interrupts, or ends one. A draft since 2026-08-29. |
| `systematic-debugging` | draft | Turns a reported defect into a named cause with the evidence that established it: reproduces the report first, localizes to the boundary where behavior diverges, then tests one hypothesis at a time and returns a deterministic verdict. Diagnoses and never repairs. A draft since 2026-08-29, and deliberately kept one at its first dogfood (`feat-0062`), where an independent check refuted the cause the run had reached. |

## Tier B: semi-scalable (great for teams and clients)

| Skill | Status | What it does |
|---|---|---|
| `repo-explainer` | planned | A "start here" guided tour of an unfamiliar codebase. Strong for client onboarding. |
| `sop-drafter` | planned | Turn a described workflow into a documented standard operating procedure. |
| `security-audit` | planned | Repeatable dependency and secret scan with a written summary. |
| `adr` | planned | Architecture decision records / decision log entries. |

## Tier C: hyper-specific (personal, stays out of the shared kit)

The author's Content OS pipeline: `produce`, `clip-machine`, `repurpose`, `video-editing`, `video-cutting`, `episode-brief`, `youtube-transcript`, `idea-discovery`. These are showcase and portfolio demos ("look what is possible"), not plug-and-play for others. They live in their own repo, not here.

## Hooks: the rules that do not depend on remembering

Every skill above is prose. An agent follows it for as long as it holds it in context, which is fine for a rule you consult on purpose and useless for a rule that has to fire when nobody is thinking about it.

The [hooks module](../.agents/hooks/README.md) is the answer to the second kind. A hook is a small program your harness runs at a lifecycle event, and it comes in exactly two shapes: a **reminder** injects context and never blocks, and a **gate** refuses, but only when the condition can be decided mechanically rather than interpreted.

| Hook | Shape | Fires when |
|---|---|---|
| `delegation-reminder` | reminder | a delegated agent reports back, to note that its summary is a claim and not evidence |
| `spec-conformance-gate` | gate | work a contract governs is closed with no audit of whether the implementation matches it |
| `skill-reachability-reminder` | reminder | a session starts with none of this kit's skills reachable at either scope, so work that assumes one would proceed without it and nothing else would say so. A library of somebody else's skills does not count, which is what `bug-0021` fixed after a cloud container's own 24 skills silenced it |
| `install-currency-reminder` | reminder | a session starts in the kit's own repository and its install record no longer agrees with the working tree, so the copies you are working with are stale, have no digest baseline to be checked against, or were never installed. `install.py --check` has always been able to answer this; nothing ever asked it, and eighteen stale skills went unreported for ten days as a result |

These are the only things the kit ships that run inside your session, so they are opt-in (`install.py --with-hooks`) and you activate them yourself.

## What the kit borrows, and how you can check it

Some of what is above came from somewhere else, chiefly Balarama Bosch's [repoprompt-workflows](https://github.com/moonray/repoprompt-workflows) (MIT): four of the Epic B lenses, the review lens, and both hooks. Attribution for all of it is in [`NOTICE`](../NOTICE).

Prose credit on its own decays, though. This kit's own roadmap once credited a skill to an upstream workflow that had never been vendored here, and by the time anyone noticed, the folder that would have settled it was gone. So since `feat-0043` every adapted file also carries a **provenance block**: the exact upstream file it came from, the author, the license, the date it was retrieved, and the SHA256 of the bytes that were retrieved. Running `scripts/check-provenance.py` re-fetches each recorded source and tells you whether upstream has moved since.

Two properties are worth knowing if you adopt this. The digest is of the *upstream* file, never of the adapted local one, which differs on purpose, so what the check answers is "has the thing we adapted from changed", not "has anyone edited our copy". And the check only ever reports: it never rewrites an adapted file, because overwriting a house-styled adaptation with upstream's current text would silently undo the adaptation. A source that genuinely cannot be located is recorded as unlocatable rather than given a plausible-looking guess, since a wrong digest reads as verified.

## The two building blocks the whole kit reuses

- **`AGENTS.md`** as the canonical, cross-tool instruction file.
- **A harness-agnostic `SKILL.md` body** plus thin generated per-harness adapters. This is what makes any skill above portable.
