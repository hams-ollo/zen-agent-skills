# Roadmap

**Status:** living document | **Last updated:** 2026-07-27

The builder-facing execution plan: which skills get built and in what order. For the reader-facing narrative of what the kit offers, see [`docs/CATALOG.md`](docs/CATALOG.md). For atomic work in flight, see [`.tasks/`](.tasks/); for finished work, [`CHANGELOG.md`](CHANGELOG.md). Altitude model in the work-altitude-model section of [`AGENTS.md`](AGENTS.md).

Seeded 2026-07-23 from `docs/CATALOG.md`. Features here stay at the 10,000-foot layer until it is their turn; only then are they decomposed into `.tasks/` files.

---

## Current state

The kit exists and dogfoods itself. Shipped and verified:

- **`init-worktracking`** (hardened): tiered footprint, idempotent re-runs, seed-by-inspection, shipped `validate.py`, migration dry-run, decoupled house-style module.
- **`new-task`**: gold-standard task authoring, the upstream that feeds `fix-batch`.
- **`project-bootstrap`** (blessed 2026-07-24): the umbrella front door; stack-aware baseline (gitignore, editorconfig, linter/formatter from a swappable house code-style layer, license, README stub) that then calls `init-worktracking`.
- **`pr-describe`** (blessed 2026-07-24): the closing bookend; drafts a PR body and a changelog entry from a branch's diff (or the working tree), in the target repo's own format, without touching GitHub.
- **Tooling**: `scripts/install.py` (cross-platform installer), `build-adapters.py` (Cursor/VS Code adapters), `validate-skills.py` (kit-level lint).
- **This tracking system**: `AGENTS.md`, `.tasks/`, `ROADMAP.md`, `CHANGELOG.md`.
- **Documentation and handoffs**: `doc-author`, `doc-revise`, `agent-handoff`, and `human-handoff` (blessed 2026-07-24 after in-kit dogfooding and user sign-off).

The parallel-execution back half of the spine has been folded in from the author's global skill set (`~/.claude/skills`):

- **`fix-batch`** and **`reconcile-worktrees`** (blessed 2026-07-24): ported into the kit (`feat-0005`, `feat-0006`), adapted to house style, portability-gated, and wired into the `.tasks/` spine. Blessed after a live in-kit run dispatched two parallel worktree agents (`chore-0001`, `chore-0002`) and reconciled them into main.

---

## Forward plan

Ordered by effort-to-value. Each item is one skill (a Feature). Strike through when shipped.

### Epic A: broadly shareable (the public kit)

1. ~~**`project-bootstrap`.** The umbrella front door: language-aware scaffold (gitignore, editorconfig, linter/formatter, license, README stub) that then calls `init-worktracking`.~~ **Shipped** (`feat-0001` draft, `feat-0002` house code-style layer; blessed 2026-07-24).
2. ~~**`pr-describe`.** Draft a PR body and changelog entry from a branch's diff, in the target repo's own changelog format (draft-only, never touches GitHub).~~ **Shipped** (`feat-0003` draft, `feat-0004` working-tree fallback from field iteration; blessed 2026-07-24).
3. ~~**`house-review`.** House-style review with an explicit rubric and severities, composing the swappable [`review-quality`](.agents/rules/review-quality.md) lens (moonray's quality-lens pattern).~~ **Shipped** (`feat-0007`; blessed 2026-07-24 after dogfooding).
4. **`ci-scaffold`** (hold until used twice). Generate CI (lint + test + build + release) matched to the detected stack.
5. **`release-cut`** (hold until used twice). Version bump, changelog roll-up, tag, notes.
6. ~~**Fold in `doc-author` / `doc-revise`** from `zen-solutions-studio`.~~ **Shipped** (`feat-0011`, `feat-0012`; dogfooded on the in-kit architecture guide and documentation consistency pass, then blessed 2026-07-24 after user sign-off).
7. ~~**Fold in `agent-handoff` / `human-handoff`** (already portable by design).~~ **Shipped** (`feat-0009`, `feat-0010`; dogfooded with the fold-in brief and in-kit partner status update, then blessed 2026-07-24 after user sign-off).
8. **Kit-wide skill evaluation** (recurring). Systematically exercise and evaluate every shipped skill rather than trusting the one dogfood that blessed it, then refine from what the pass finds. Each skill was blessed on a single real use, which proves it works once but leaves whole branches unexercised: `verifier-agent`'s `blocked` verdict, `test-author`'s characterization mode, and `spec-plan-readiness`'s blocking paths have never fired on real work. Define what "evaluated" means (which behaviors must be observed, and what evidence counts), run the pass, and record per-skill findings as tasks. Decide as part of the work whether the result is a written evaluation protocol, a reusable `skill-eval` skill, or a fixture-based regression suite under `tests/`; do not presuppose the artifact. This is the natural consumer of the spine itself: specify it with `spec-author`, verify each skill with `verifier-agent`. A first read-only pass ran on 2026-07-25 and its findings are filed under [Kit hardening](#kit-hardening-from-the-2026-07-25-review-pass); that pass covered structure, status claims, and cross-references, and deliberately did not exercise any skill's behavior, which is the harder half still open.

### Epic B: contract-driven delivery (the agent-workflow spine)

1. ~~**`spec-quality`.** A reusable quality gate for scenario-based specifications: keep contracts observable, non-redundant, grounded in repository context, traceable through stable scenario IDs, and free of implementation planning. Report explicit blockers for ambiguity, uncovered goals or surfaces, and unresolved questions.~~ **Shipped** (`feat-0013`; folded in from `repoprompt-workflows` (Balarama Bosch, MIT), house-styled; blessed 2026-07-24 after dogfooding it on the new `docs/spec/spec-author.md` draft, where it caught five findings; user sign-off recorded).
2. ~~**`spec-author`.** Draft a persistent, executable `SPEC.md` from a raw idea before task decomposition: outcomes, anti-goals, architectural constraints, prior decisions, and mechanically testable verification criteria. It composes `spec-quality`; planning and specification work are read-only for implementation surfaces, and an explicit human approval state is required before `new-task` consumes a specification.~~ **Shipped** (`feat-0017`; authored 2026-07-24 by extracting the drafting discipline from the upstream RPCE Spec workflow into a portable skill that composes `spec-quality`; blessed 2026-07-24 after dogfooding it to draft `docs/spec/test-author.md`, where its `spec-quality` self-check caught six findings before returning a `ready` spec; user sign-off recorded).
3. ~~**`spec-plan-readiness`.** Gate implementation on an approved specification plus an ordered, repository-grounded plan. Block tests, code, and delegation until scenarios, tasks, validation, risks, rollback notes, task-to-scenario traceability, and a first safe task are all explicit.~~ **Shipped** (`feat-0014`; folded in from `repoprompt-workflows` (Balarama Bosch, MIT), house-styled and retargeted from RPCE "Deep Plan" to the kit's `.tasks/` model; blessed 2026-07-24 after gating the `spec-author` build (spec plus a two-task decomposition) to `implementable` with a scenario-to-test map; user sign-off recorded).
4. ~~**`test-quality`.** A reusable test-quality lens for choosing the lowest faithful test layer, naming the plausible defect each test protects, testing the real bug population, asserting meaningful observable outcomes, and handling fixtures, mocks, diagnostics, and trust boundaries deliberately.~~ **Shipped** (`feat-0015`; folded in from `repoprompt-workflows` (Balarama Bosch, MIT), house-styled; blessed 2026-07-24 after applying it to the untested `scripts/validate-skills.py`, producing a layer/oracle recommendation and surfacing a testability issue; user sign-off recorded).
5. ~~**`test-author`** (promoted from the former Epic B). Derive focused acceptance tests from approved specifications and task criteria, while retaining characterization-test support for legacy code with no coverage. Compose `test-quality` and run between implementation and reconciliation so test evidence is part of the core workflow.~~ **Shipped** (`feat-0018`; authored 2026-07-24 by extracting the discipline from the upstream RPCE Test workflow into a portable skill composing `test-quality` and `spec-quality`; blessed 2026-07-24 after dogfooding it to derive the `validate-skills.py` acceptance suite from `docs/spec/validate-skills.md` (11 passing tests, closing `chore-0003`), correctly omitting the accepted S-008 divergence rather than faking a pass; user sign-off recorded).
6. ~~**`spec-conformance`.** Audit every approved scenario and public-surface element against code and test evidence, producing a positive conformance matrix of `Conformed`, `Diverged`, or `Not-built` items and an explicit unreconciled set. It reports, never repairs, implementation divergence.~~ **Shipped** (`feat-0016`; folded in from `repoprompt-workflows` (Balarama Bosch, MIT), house-styled, composing into `fix-batch` verification rather than duplicating it; blessed 2026-07-24 after auditing `scripts/validate-skills.py` against `docs/spec/validate-skills.md` into a conformance matrix with one accepted divergence; user sign-off recorded).
7. ~~**`verifier-agent`.** Independently test an implementation against its approved specification and task acceptance criteria before reconciliation. It composes `spec-conformance`, produces structured pass, fail, or blocked evidence, runs the declared commands, and never edits the implementation it verifies.~~ **Shipped** (`feat-0019`; authored 2026-07-24 against `docs/spec/verifier-agent.md`, the first spec drafted by `spec-author` and explicitly approved before decomposition; blessed 2026-07-24 after dogfooding it on `scripts/validate-skills.py`, where it returned `pass` and caught a live defect neither the tests nor a fresh audit would surface: the conformance matrix's evidence citations had drifted +8 lines after the `chore-0003` refactor, with classifications still correct on stale pointers. It reported the drift rather than repairing it, and the skill was iterated from that evidence; `chore-0005` re-anchored the citations. User sign-off recorded. Completes the core spec-to-reconcile loop; the `blocked` verdict path is specified but not yet exercised on real work).
8. **`user-testing`** (conditional on user-facing work). Drive rendered UI workflows against throwaway data, inspect screenshots plus console and network state, and record user-visible defects that automated tests and contract conformance miss. Mark the closeout blocked when real workflow testing cannot run, rather than silently skipping it.
9. ~~**`doc-sync`.** Detect documentation drift caused by code changes or audit a documentation set, distinguishing current-state docs from human-owned contracts. Default to a code-grounded dry run; require explicit approval before updating current-state documentation and never silently rewrite contract documents. Keep it distinct from `doc-author` and `doc-revise`.~~ **Shipped** (`feat-0020`; authored in-kit 2026-07-25 against `docs/spec/doc-sync.md`, the second spec drafted by `spec-author` and explicitly approved before decomposition, after two open questions on approval auditability and vendored material were resolved into the contract. Dogfooded in dry-run mode across this repository's own documentation set: 38 documents audited, 29 skipped as ledger, 12 findings, nothing modified. It surfaced all three dangling references to a `document` skill that never existed here, plus five drift instances the known-answer set did not anticipate, and correctly declined to edit a contract document. The run's weakness was mechanical precision (13 heuristic hits for 1 true positive) and the skill was iterated from that evidence. Blessed 2026-07-25 after `chore-0006` exercised the apply path; user sign-off recorded. Earlier revisions of this line credited an upstream `document` workflow; no such skill was ever vendored here, and the only surviving trace of its contract is the dry-run-first instruction at `repoprompt-workflows-main/.agents/workflows/Loop.md:194`, so this skill was authored rather than folded in).
10. **`review-depth`.** Select quick, standard, or deep review from deterministic signals: change size, directory spread, severe risk flags, blast radius, and documentation-only scope. Compose it with `house-review` so review effort matches risk and an explicit user choice always overrides detection.
11. **`maintainability-review`** (hold until used twice). An optional, strict structural review lens for unnecessary indirection, file sprawl, spaghetti growth, boundary leaks, and missed simplification. Preserve upstream provenance and a reproducible sync process if a vendored lens is adopted.
12. **`telemetry-guard`.** Establish a portable `.agents/hooks/` runtime protocol and stdlib Python guardrail for agent runs: structured lifecycle events, retry and implementor/verifier-cycle limits, time or optional compute budgets, repeated-work detection, and a clear stop signal on a bound violation.
13. **`context-sync`** (hold until used against one real integration). Ground an agent in a narrowly defined live source, such as a schema or API contract, with recorded source, version or timestamp, authority level, failure behavior, and reproducible provenance for verification. Do not ship a generic MCP wrapper without field iteration.

### Epic C: semi-scalable (teams and clients)

1. **`repo-explainer`.** A "start here" guided tour of an unfamiliar codebase.
2. **`sop-drafter`.** Turn a described workflow into a documented SOP.
3. **`security-audit`.** Repeatable dependency and secret scan with a written summary.
4. **`adr`.** Architecture decision records / decision log.

### Epic D: personal (stays OUT of the shared kit)

The Content OS pipeline (`produce`, `clip-machine`, `repurpose`, `video-editing`, `video-cutting`, `episode-brief`, `youtube-transcript`, `idea-discovery`) stays in `zen-solutions-studio` as portfolio demos, not plug-and-play kit skills.

---

## Kit hardening (from the 2026-07-25 review pass)

A read of all 19 shipped skills on 2026-07-25, the first deliberate pass rather than a per-skill dogfood. It found four systemic issues and two gaps that need a decision before they can be decomposed. Filed rather than fixed, so each item can be dispatched to an isolated agent.

Ready to dispatch. Wave 1 is parallel-safe (disjoint `touched_files`); wave 2 waits on `bug-0002`, which touches the same files.

| Task | Wave | What |
|---|---|---|
| [`bug-0002`](.tasks/done/bug-0002-agents-section-references-by-name.md) | 1 | **Portability defect.** Skills reference `AGENTS.md` by section *number*, but the numbering differs between this repo and the repos `init-worktracking` scaffolds. `new-task` is correct for scaffolded repos and wrong here; `spec-plan-readiness` is correct here and wrong there. `.tasks/_TEMPLATE.md` propagates the wrong pointer into every task file. Reference sections by name. |
| [`chore-0007`](.tasks/done/chore-0007-clear-stale-skill-status-claims.md) | 1 | Seven stale status claims, including three skills (`house-review`, `pr-describe`, `project-bootstrap`) that call themselves a draft and shipped in the same file. |
| [`feat-0021`](.tasks/done/feat-0021-iterate-doc-sync-detection.md) | 1 | Iterate `doc-sync` from the four drift instances this review found that its own dogfood missed. Line-scoped matching and an incomplete staleness vocabulary were the causes. |
| [`chore-0008`](.tasks/done/chore-0008-cross-link-doc-trio.md) | 1 | `doc-author` and `doc-revise` have no reference to `doc-sync`; the documentation trio only links one way. |
| [`chore-0009`](.tasks/done/chore-0009-agent-handoff-harness-neutral.md) | 1 | `agent-handoff`'s description hardcodes "Claude Code", putting harness lock-in in the kit's most visible field. |
| [`feat-0023`](.tasks/done/feat-0023-extend-validate-skills-lint.md) | 1 | `validate-skills.py` catches none of the above. Extend it so this class of defect fails a command instead of waiting for a human read. |
| [`feat-0022`](.tasks/done/feat-0022-wire-verifier-agent-into-fix-batch.md) | 2 | Wire `verifier-agent` into `fix-batch` Step 6 and `reconcile-worktrees`. Deferred by `feat-0019` until the skill had been used; it has been. |
| [`chore-0010`](.tasks/done/chore-0010-spec-plan-readiness-compose-test-quality.md) | 2 | `spec-plan-readiness` restates `test-quality`'s layer taxonomy inline instead of composing it. Two copies free to drift. |

Decided on 2026-07-25 and now filed:

| Task | Decision |
|---|---|
| ~~[`chore-0011`](.tasks/done/chore-0011-document-skill-shapes-and-house-style-pointers.md)~~ | **Done.** All 19 skills now reference the house-style module and `AGENTS.md` documents both body shapes. The task's own premise was wrong: four skills needed target-repo-aware wording, not two, and `pr-describe` would have been given a paragraph contradicting a rule in its own body. |
| ~~[`feat-0024`](.tasks/done/feat-0024-exercise-verifier-blocked-branch.md)~~ | **Done.** The `blocked` branch fired on a real unapproved contract and matched S-005 on every clause. Produced `docs/spec/house-review.md` (11 scenarios) and the reusable evaluation-record format at `docs/spec/house-review.verification.md`. Two findings filed as `chore-0014`. |

## Kit mechanics hardening (from the 2026-07-27 review pass)

The second kit-wide pass, and the first to go at what each skill's procedure actually *does* when
run on a real repository rather than at its structure. It found two blockers, five majors, and
eight smaller issues, none visible to either validator. All thirteen were fixed the same day; see
the 2026-07-27 `CHANGELOG.md` entry for the full account. The headline two:

- **The installer shipped the skills without the lenses they compose.** 14 of 19 skills referenced
  `.agents/rules/`, which `install.py` never carried, so `house-review` arrived with no rubric at
  all. Fixed by installing the rules module as the sibling the existing links already assumed.
- **`reconcile-worktrees` silently dropped every new file an agent created.** Its `git diff | git
  apply` mechanism could not see untracked files, and `fix-batch` requires agents to leave work
  uncommitted, so the deliverable landed nowhere and the worktree holding the only copy was then
  deleted.

The pattern behind most of them: the kit is documentation and stdlib Python with no dependency
tree, no large diffs, and no binary assets, so procedures that assume a normal software repository
had never met one. That is the standing risk in dogfooding a tool on the repository that builds it,
and it is what `feat-0025` exists to close.

| Task | What |
|---|---|
| ~~[`feat-0025`](.tasks/done/feat-0025-exercise-batch-loop-on-dependency-bearing-repo.md)~~ | **Done.** Ran a real three-agent batch against `gaudiya-vaishnava-knowledge-wiki` (9 tests to 47). The reconciliation fix was load-bearing: all three deliverables were new files, so all three `git diff` patches were 0 bytes and the pre-fix mechanism would have lost the entire batch while reporting success. Six findings folded back into `fix-batch`, `reconcile-worktrees`, and `new-task`. The batch-loop hardening is no longer cold. |
| ~~[`chore-0012`](.tasks/done/chore-0012-decide-code-review-skill-name.md)~~ | **Done.** Renamed `code-review` to `house-review`, named for the rubric it applies rather than the act of reviewing. Both Open Questions in its contract resolved and re-approved. The rename exposed and fixed a defect in `.tasks/validate.py --strict`, which was checking completed tasks' `touched_files` and so broke permanently on any rename. |
| ~~[`chore-0013`](.tasks/done/chore-0013-amend-validate-skills-contract.md)~~ | **Done.** Amended the `validate-skills` contract to cover the four checks the implementation had outgrown it by, and the regenerated matrix caught a live divergence in `S-014` while doing it: the check had shipped on 2026-07-25, was believed correct for two days, and only surfaced once a scenario stated the condition semantically instead of restating the implementation. Fixed the same day. |
| ~~[`feat-0026`](.tasks/done/feat-0026-write-build-adapters-spec.md)~~ | **Done.** Wrote and approved `docs/spec/build-adapters.md` (13 scenarios), closed the five that had no test (30 to 35 tests), and restored the softened documentation claims. The audit surfaced one unstated contract decision: an existing rules file is preserved but an edited skill template is overwritten, an asymmetry invisible to both the spec and the tests. Recommendation recorded; the call is human. |

The evaluation-record format is now established by `feat-0024` and documented in
[`docs/spec/house-review.verification.md`](docs/spec/house-review.verification.md). The two remaining
branches reuse it and are ready to decompose:

- **`test-author`'s characterization mode**, never fired on real work.
- **`spec-plan-readiness`'s blocking paths**, never fired on real work.
- **The wider spec and test coverage question.** Even after `feat-0024`, 5 of 19 skills will have a contract and none will have behavioral tests. Whether that gap is worth closing skill by skill, or whether the targeted-branch approach is sufficient, is a judgment to make once there is evidence from the first three exercises.

---

## Out of scope by design

- No database or service dependency anywhere in the kit. Everything is markdown, `SKILL.md`, and stdlib Python. Portability is the whole point.
- No skill ships to the kit cold. A skill is drafted, used on real work, iterated, then blessed. Speculative skills stay at this roadmap altitude, not in `.agents/skills/`.
