# Roadmap

**Status:** living document. Dated per entry rather than per file: a whole-file `Last updated` header was removed on 2026-08-27 (`chore-0066`) after twenty days reading 2026-08-07 over content that ran to 2026-08-27, with nothing checking it. Every claim below carries its own date, which is the date that can be checked against the thing it describes, and `git log -1 ROADMAP.md` answers what the header was answering without being able to drift.

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
8. **Kit-wide skill evaluation** (recurring). Systematically exercise and evaluate every shipped skill rather than trusting the one dogfood that blessed it, then refine from what the pass finds. Each skill was blessed on a single real use, which proves it works once and leaves other branches unexercised. The three named at the outset, `verifier-agent`'s `blocked` verdict, `test-author`'s characterization mode, and `spec-plan-readiness`'s blocking paths, were all exercised on real triggers on 2026-07-27 (`feat-0024`, `feat-0027`, `feat-0028`) and each run is recorded. The recurring question is what to exercise next. Define what "evaluated" means (which behaviors must be observed, and what evidence counts), run the pass, and record per-skill findings as tasks. Decide as part of the work whether the result is a written evaluation protocol, a reusable `skill-eval` skill, or a fixture-based regression suite under `tests/`; do not presuppose the artifact. This is the natural consumer of the spine itself: specify it with `spec-author`, verify each skill with `verifier-agent`. A first read-only pass ran on 2026-07-25 and its findings are filed under [Kit hardening](#kit-hardening-from-the-2026-07-25-review-pass); that pass covered structure, status claims, and cross-references and deliberately did not exercise any skill's behavior. A second pass on 2026-07-27 did exactly that, going at what each procedure does when run, and found two blockers no reading pass had; its findings are filed under [Kit mechanics hardening](#kit-mechanics-hardening-from-the-2026-07-27-review-pass). **Absorbed 2026-08-07 by [Epic E](#epic-e-delegated-execution-cloud-and-unattended-work) item 6**, which answers the artifact question this item deliberately left open: a fixture-based regression suite under `tests/`, rather than a written protocol or a `skill-eval` skill. The reason it can be answered now is that the consumer arrived. An unattended batch has no human reading each run, so "exercise a skill and judge the result" stops being available and the only evaluation that survives delegation is one a command can run. The recurring question of what to exercise next stays live here; the mechanism moves there.

9. ~~**`tracker-links`: GitHub issue linking.**~~ **Shipped** (`feat-0030`, `feat-0031`; blessed 2026-07-28 after a real dogfood: issue #1 opened, task linked, PR #2 merged, issue closed itself. Coverage honestly recorded at two of seven scenarios in [`docs/spec/tracker-links.verification.md`](docs/spec/tracker-links.verification.md).) Let a task file name the upstream GitHub issue it serves, and have `pr-describe` carry that into the pull request description so merging closes it. Specified in [`docs/spec/tracker-links.md`](docs/spec/tracker-links.md) (`status: approved`, 9 scenarios). The value is not the plumbing but the silent-failure surface around it: GitHub ignores a closing keyword in a pull request title and in comments, ignores it entirely unless the pull request targets the default branch, and closes only the first issue when one keyword is followed by a list. Each failure produces a pull request that looks right, merges cleanly, and leaves the tracker wrong. Dogfooded on this repository's own issues.
10. **Azure DevOps work-item linking** (hold until an ADO board has been used on real work). The same idea against Azure Boards, which uses `AB#{ID}` and supports state transitions (`Fixed AB#1234` moves the item to the Resolved category). Deliberately deferred rather than built alongside GitHub: the kit has no ADO project to exercise it against, and shipping an unexercised integration is the cold ship the contribution bar forbids. Two things make it cheaper than it looks when its turn comes. The `external` field holds the platform's own token verbatim, so an `AB#1234` value needs no new field or translation layer. And the hierarchy already matches: Azure's Epic to Feature to User Story to Task is the work-altitude model this repo already uses. Note before building: Microsoft ships a supported [Azure DevOps MCP server](https://github.com/microsoft/azure-devops-mcp), so the right shape may be composing what an adopter already has rather than shelling out to `az boards`. Decide that with evidence, not in advance.

### Epic B: contract-driven delivery (the agent-workflow spine)

1. ~~**`spec-quality`.** A reusable quality gate for scenario-based specifications: keep contracts observable, non-redundant, grounded in repository context, traceable through stable scenario IDs, and free of implementation planning. Report explicit blockers for ambiguity, uncovered goals or surfaces, and unresolved questions.~~ **Shipped** (`feat-0013`; folded in from `repoprompt-workflows` (Balarama Bosch, MIT), house-styled; blessed 2026-07-24 after dogfooding it on the new `docs/spec/spec-author.md` draft, where it caught five findings; user sign-off recorded).
2. ~~**`spec-author`.** Draft a persistent, executable `SPEC.md` from a raw idea before task decomposition: outcomes, anti-goals, architectural constraints, prior decisions, and mechanically testable verification criteria. It composes `spec-quality`; planning and specification work are read-only for implementation surfaces, and an explicit human approval state is required before `new-task` consumes a specification.~~ **Shipped** (`feat-0017`; authored 2026-07-24 by extracting the drafting discipline from the upstream RPCE Spec workflow into a portable skill that composes `spec-quality`; blessed 2026-07-24 after dogfooding it to draft `docs/spec/test-author.md`, where its `spec-quality` self-check caught six findings before returning a `ready` spec; user sign-off recorded).
3. ~~**`spec-plan-readiness`.** Gate implementation on an approved specification plus an ordered, repository-grounded plan. Block tests, code, and delegation until scenarios, tasks, validation, risks, rollback notes, task-to-scenario traceability, and a first safe task are all explicit.~~ **Shipped** (`feat-0014`; folded in from `repoprompt-workflows` (Balarama Bosch, MIT), house-styled and retargeted from RPCE "Deep Plan" to the kit's `.tasks/` model; blessed 2026-07-24 after gating the `spec-author` build (spec plus a two-task decomposition) to `implementable` with a scenario-to-test map; user sign-off recorded).
4. ~~**`test-quality`.** A reusable test-quality lens for choosing the lowest faithful test layer, naming the plausible defect each test protects, testing the real bug population, asserting meaningful observable outcomes, and handling fixtures, mocks, diagnostics, and trust boundaries deliberately.~~ **Shipped** (`feat-0015`; folded in from `repoprompt-workflows` (Balarama Bosch, MIT), house-styled; blessed 2026-07-24 after applying it to the untested `scripts/validate-skills.py`, producing a layer/oracle recommendation and surfacing a testability issue; user sign-off recorded).
5. ~~**`test-author`** (promoted from the former Epic B). Derive focused acceptance tests from approved specifications and task criteria, while retaining characterization-test support for legacy code with no coverage. Compose `test-quality` and run between implementation and reconciliation so test evidence is part of the core workflow.~~ **Shipped** (`feat-0018`; authored 2026-07-24 by extracting the discipline from the upstream RPCE Test workflow into a portable skill composing `test-quality` and `spec-quality`; blessed 2026-07-24 after dogfooding it to derive the `validate-skills.py` acceptance suite from `docs/spec/validate-skills.md` (11 passing tests, closing `chore-0003`), correctly omitting the accepted S-008 divergence rather than faking a pass; user sign-off recorded).
6. ~~**`spec-conformance`.** Audit every approved scenario and public-surface element against code and test evidence, producing a positive conformance matrix of `Conformed`, `Diverged`, or `Not-built` items and an explicit unreconciled set. It reports, never repairs, implementation divergence.~~ **Shipped** (`feat-0016`; folded in from `repoprompt-workflows` (Balarama Bosch, MIT), house-styled, composing into `fix-batch` verification rather than duplicating it; blessed 2026-07-24 after auditing `scripts/validate-skills.py` against `docs/spec/validate-skills.md` into a conformance matrix with one accepted divergence; user sign-off recorded).
7. ~~**`verifier-agent`.** Independently test an implementation against its approved specification and task acceptance criteria before reconciliation. It composes `spec-conformance`, produces structured pass, fail, or blocked evidence, runs the declared commands, and never edits the implementation it verifies.~~ **Shipped** (`feat-0019`; authored 2026-07-24 against `docs/spec/verifier-agent.md`, the first spec drafted by `spec-author` and explicitly approved before decomposition; blessed 2026-07-24 after dogfooding it on `scripts/validate-skills.py`, where it returned `pass` and caught a live defect neither the tests nor a fresh audit would surface: the conformance matrix's evidence citations had drifted +8 lines after the `chore-0003` refactor, with classifications still correct on stale pointers. It reported the drift rather than repairing it, and the skill was iterated from that evidence; `chore-0005` re-anchored the citations. User sign-off recorded. Completes the core spec-to-reconcile loop; the `blocked` verdict path is specified but not yet exercised on real work).
8. **`user-testing`** (hold, conditional on user-facing work; reasoning restated 2026-08-05). Drive rendered UI workflows against throwaway data, inspect screenshots plus console and network state, and record user-visible defects that automated tests and contract conformance miss. Mark the closeout blocked when real workflow testing cannot run, rather than silently skipping it. **Reviewed against the upstream skill on 2026-08-05 and still held.** Its transferable content is two ideas: run only against a throwaway data location, never real environment data, and mark a closeout blocked rather than silently skipping when workflow testing cannot run. Both are worth having and neither justifies a skill for a kit whose users are mostly not building UI. The calculus that changed is tooling availability, not need. **Trigger to revisit:** the first piece of real user-facing work built with this kit, at which point author it against that work rather than in the abstract.
9. ~~**`doc-sync`.** Detect documentation drift caused by code changes or audit a documentation set, distinguishing current-state docs from human-owned contracts. Default to a code-grounded dry run; require explicit approval before updating current-state documentation and never silently rewrite contract documents. Keep it distinct from `doc-author` and `doc-revise`.~~ **Shipped** (`feat-0020`; authored in-kit 2026-07-25 against `docs/spec/doc-sync.md`, the second spec drafted by `spec-author` and explicitly approved before decomposition, after two open questions on approval auditability and vendored material were resolved into the contract. Dogfooded in dry-run mode across this repository's own documentation set: 38 documents audited, 29 skipped as ledger, 12 findings, nothing modified. It surfaced all three dangling references to a `document` skill that never existed here, plus five drift instances the known-answer set did not anticipate, and correctly declined to edit a contract document. The run's weakness was mechanical precision (13 heuristic hits for 1 true positive) and the skill was iterated from that evidence. Blessed 2026-07-25 after `chore-0006` exercised the apply path; user sign-off recorded. Earlier revisions of this line credited an upstream `document` workflow; no such skill was ever vendored here, and the only surviving trace of its contract is the dry-run-first instruction at `repoprompt-workflows-main/.agents/workflows/Loop.md:194`, so this skill was authored rather than folded in).
10. ~~**`review-depth`.** Select quick, standard, or deep review from deterministic signals: change size, directory spread, severe risk flags, blast radius, and documentation-only scope. Compose it with `house-review` so review effort matches risk and an explicit user choice always overrides detection.~~ **Shipped** (`feat-0035`; authored 2026-07-31, blessed 2026-08-05 on author sign-off. Dogfooded against six in-repository changesets and one external Python repository with a real lockfile, and iterated from what those runs found: the blanket-escalation rule was replaced after four of six changesets tripped it, a prose carve-out was added to `blast_radius` after nineteen referencing files sent a four-line fix to `deep`, and the exclusion classes were proven on a 6512-line `uv.lock` and 938 lines of generated schema. Two dogfood criteria remain unticked and are accepted rather than claimed: the per-changeset depth records were not kept and cannot be reconstructed, so the evidence is recorded as conclusions in the skill body rather than as a per-run table. Using it is also what exposed the mode contradiction inside `house-review`, closed by `chore-0024`).
11. **`maintainability-review`** (hold; reasoning replaced 2026-08-05). An optional, strict structural review lens for unnecessary indirection, file sprawl, spaghetti growth, boundary leaks, and missed simplification. **"Hold until used twice" is no longer the binding reason.** Two better ones replace it. First, upstream does not author this lens either: it syncs it from `cursor/plugins` (the "thermo-nuclear" code-quality review, MIT), so adopting it makes this kit a third-hand vendor, which `NOTICE` already anticipates. Second, and decided by inspection rather than assumed now that `feat-0035` has landed: **`review-depth`'s `deep` tier absorbs most of the need.** It sets three knobs and states it sets nothing else, and one of them is that every category in the `review-quality` lens is considered explicitly and recorded as applied or as one line of "not applicable, and why". Category 5 of that lens is already readability and maintainability (naming, structure, dead code, duplicated logic, needless complexity). So a `deep` review already sweeps this ground and cannot silently skip it. What a dedicated lens would add is strictness beyond one rubric line, not coverage where there was none. **Concrete trigger to revisit:** a real `deep` review whose findings show category 5 is too coarse for the structural problem in front of it. Until that happens the marginal value is small and the vendoring cost is real. If it does happen, author one against the observed gap rather than vendoring a third-hand lens.
12. ~~**Decision log (v1, task-file only).** Have each worktree agent record its non-recoverable decisions (rejected alternatives, deliberately open seams, falsified task premises) in its own task file, and have `pr-describe` surface them. Deliberately excludes the spec-sibling rollup (`docs/spec/<name>.decisions.md`, consumed by `new-task`) until v1 proves the entries are worth reading, and carries an explicit kill criterion so the convention cannot survive by default.~~ **Shipped** ([`feat-0037`](.tasks/done/feat-0037-task-file-decision-log-v1.md); 2026-08-05, in a four-item parallel batch). An optional `## Decisions` section in the task template, defined once there with a four-item exclusion list, referenced in prose by `fix-batch` and `pr-describe` rather than restated, since a link from a skill body into `.tasks/` escapes the installed skill tree. The `fix-batch` item names itself the exception that proves the closeout-bookkeeping rule: `done/`, `CHANGELOG.md`, and `ROADMAP.md` are the same files for every item in a batch, while an agent's own task file is the one file exactly one agent owns. Composes with item 16's mechanical contract in the same file rather than adding a tenth field to it. Kept distinct from item 13's phase 2 (telemetry: retries, budgets, stop signals), which covers mechanical run-state rather than semantic continuity; building them together would conflate the two. Triggered by observed loss rather than by plan: two of three agents in the `feat-0025` batch found their task file's premise factually wrong about the code, and nothing in the system captured it. **Kill criterion, first data point:** the implementing agent wrote three entries into its own task file and all three are unrecoverable from the diff, the verification record, or the spec. Review again after the next batch of three or more agents before deciding whether the rollup is worth building.
13. **Enforcement hooks, then telemetry** (was `telemetry-guard`; reframed 2026-08-05). The original item was scoped as run-state telemetry, and reading the upstream sources showed that was second in line rather than wrong. Every rule this kit enforced was prose, which holds only while the model keeps it in context and fails for rules that must fire when nobody is thinking about them, so the higher-leverage first move was enforcing the spine already built.
    - ~~**Phase 1: the `.agents/hooks/` module.** A portable stdlib-Python guardrail protocol with two shapes, a *reminder* that injects context and never blocks and a *gate* that blocks only when the condition is decidable from the payload rather than interpreted from prose.~~ **Shipped** (`feat-0038` established the module, its contract, three-harness wiring and opt-in installation, seeded with `delegation-reminder`; `feat-0039` added `spec-conformance-gate`, the first gate. Both adapted from `repoprompt-workflows` (Balarama Bosch, MIT). Two findings worth carrying forward: the dogfood caught the hook silently inert on `Agent` delegations and a `python3` registration that on Windows resolves to the Store alias and fails forever without surfacing, both being the same failure shape, installed and correct-looking and doing nothing; and the faithful port of the gate would have been inert here, since this kit's spec lifecycle is `draft` then `approved` and stops, so it gained a second trigger on task closure. A guardrail that cannot fire in the repository that ships it is one nobody has ever seen work).
    - **Phase 2: telemetry and bounds** (not built; **absorbed 2026-08-07 by [Epic E](#epic-e-delegated-execution-cloud-and-unattended-work) item 7**). Structured lifecycle events, retry and implementor/verifier-cycle limits, time or optional compute budgets, repeated-work detection, and a clear stop signal on a bound violation. Phase 1 deliberately shipped none of it, because none is needed to make a reminder fire or a gate block, and the repeated-work half now has its own item below (`feat-0042`) since it depends on a finding signature rather than on run state. The reason it stayed unbuilt is the reason it moves: telemetry has no consumer while a human is watching every run, and Epic E item 5 is what first creates batches nobody is watching. It is held behind that item there rather than sequenced here.
    - **Deferred within phase 1: `test-quality-reminder`.** Upstream's Stop-gate hook, which blocks stopping when a test file was edited without both a suite run and a `test-quality` invocation after it. The edit-run-vet-stop ordering is worth having. Its implementation carries several hundred lines of shell-command parsing to decide whether a `Bash` call was a test run, with wrapper-word stripping and package-manager subcommand exclusion, and that heuristic pile is not worth importing before the module has proven itself. Revisit once a gate has run unattended for a while.
    - **Deferred within phase 1: the lifecycle coverage gaps** (audited 2026-08-27, none built). A stage-by-stage audit found that of ten lifecycle stages, exactly one has a hook firing at it, and that the module's only *gate* is registered for Codex and OpenCode and not in this repository's own [`.claude/settings.json`](.claude/settings.json). Four candidates came out of it and **all four are held deliberately, because a module with one gate that has never fired in anger here does not need four more at once**: registering the existing `spec-conformance` gate for Claude Code (no new code, and reserved to the author by the committed-hook exception in `AGENTS.md`); a `PreToolUse` **gate** on a destructive `git reset --hard` or `git checkout --` inside an agent worktree, decidable from the payload, with the `merge --ff-only` recovery as its stated escape; a `PreToolUse` **gate** on a commit message carrying a `Co-Authored-By` trailer, the one rule here with a measured cost in hours; and a dispatch-time **reminder** injecting the nine-field report contract, which must be a reminder because whether a prompt carries the contract is not decidable from the payload. **Trigger to revisit:** the first of these registered and run for several real waves, measured rather than assumed. Coverage of the path that ships them is [`chore-0067`](.tasks/done/chore-0067-the-with-hooks-placement-path-is-covered-by-no-test-and-no-gate.md).
14. **`context-sync`** (hold until used against one real integration). Ground an agent in a narrowly defined live source, such as a schema or API contract, with recorded source, version or timestamp, authority level, failure behavior, and reproducible provenance for verification. Do not ship a generic MCP wrapper without field iteration.
15. ~~**Evidence gate and stable finding signature.** Require every review finding to carry a resolvable citation (path, line range, symbol, and an exact quote of the cited code), and drop any finding whose quote does not resolve against the file on disk. Give each finding a stable signature (severity, normalized path, summary, area id) so findings can be deduplicated across lenses and counted across runs.~~ **Shipped** ([`feat-0040`](.tasks/done/feat-0040-evidence-gate-and-finding-signature.md); 2026-08-05, in a four-item parallel batch). The evidence shape, the gate's five-branch disposition table, and the signature live in the `review-quality` lens; `house-review` applies them as a named step and `verifier-agent` cites code the same way. Two design points were forced by the work rather than planned: a quote found at a shifted line is **re-anchored and reported, not dropped**, since the finding is real and only the pointer moved, and a finding whose evidence is an **absence** (a missing test, an unhandled branch) has its own citable form, or the gate would have silently suppressed the whole test-coverage category. Dogfooded against `b50cc76`, a commit the implementing agent did not write: 3 candidates, 1 dropped for a quote resolving nowhere, 1 re-anchored 49 to 74, 1 absence finding kept. Building it also exposed that the `review-depth` composition was one-directional, since `house-review` had never named it back. Not speculative: `verifier-agent`'s own dogfood found a conformance matrix whose classifications were correct and whose line citations had drifted eight lines after a refactor, caught only because a human looked. `review-quality` rule 2 already asks for validation before reporting; this makes it mechanical. Taken from `repoprompt-workflows`' Deep Review governance without taking the workflow.
16. ~~**Delegate evidence contract for `fix-batch`.** Require a fixed field set from every worktree agent's report (task id, covered scenarios, files changed, tests, the validation command **and** its verbatim result, findings in the evidence shape above, recommended next step), and block acceptance when a field is missing. Reject transcript-style reports.~~ **Shipped** ([`feat-0041`](.tasks/done/feat-0041-delegate-evidence-contract-for-fix-batch.md); 2026-08-05, in a four-item parallel batch). Nine fields, each checkable by the orchestrator in one pass and answerable from inside a single worktree, enforced at both ends: `fix-batch` quotes the list into every dispatched prompt and gates Step 6 on it, and `reconcile-worktrees` refuses to land a worktree whose report does not meet it. The dogfood was unusually direct, since the batch that implemented this task was dispatched by the pre-contract `fix-batch` with a hand-rolled report shape: seven of that draft's nine fields survived verbatim, it had **missed** "tests added, changed, or run" and "blockers and assumptions" (both places where an agent's silence is indistinguishable from a clean result), and its `decisions` field was correctly refused as belonging to item 12's decision log rather than to the mechanical contract. The value is not the ceremony: "the validation command and its result" cannot be answered in prose without either running it or lying. Kept distinct from the decision log in item 12, which carries semantic continuity while this carries mechanical evidence. Taken from `repoprompt-workflows`' Loop workflow, without its ledger and budget machinery, which assumes a persistent orchestrator this kit does not have.
17. **Repeat detection and futility classification.** After N failed fix attempts or M observations sharing a finding signature, force a classification into `false_positive`, `core_issue`, or `futility`, and defer a futile finding as its own task rather than retrying it. Scoped as [`feat-0042`](.tasks/feat-0042-repeat-and-futility-classification.md). It was genuinely blocked on item 15, since without a stable signature there is nothing to count; item 15 shipped on 2026-08-05, so the signature now exists and this is unblocked. **The only preventive item in this group**: unlike 15 and 16, which each fix a failure this repository has already observed, this one fixes a predicted one, so it carries an explicit kill criterion. If no batch trips the trigger in the first several real runs, reconsider rather than keep it by default.
18. ~~**Provenance convention for folded-in material.** Record source URL, license, author, retrieval date, and a SHA256 digest of the retrieved content for anything adapted from an external source, and add an on-demand check that re-fetches and reports drift.~~ **Shipped** ([`feat-0043`](.tasks/done/feat-0043-vendored-sync-provenance-convention.md); 2026-08-06, in a four-item parallel batch). Attribution here decayed into folklore in under two weeks: the `doc-sync` line in this file once credited an upstream `document` workflow that was never vendored, and the gitignored fold-in source it cited is now gone from the tree entirely. The convention lives in the conventions section of `AGENTS.md` and [`check-provenance.py`](scripts/check-provenance.py) reports drift on demand, exiting 0, 1, or 2 for match, drift, and unreachable. Upstream's automatic in-place sync was deliberately **not** copied, since every fold-in here was house-styled and retargeted and an overwrite would destroy the adaptation. **The task expected some sources to be unlocatable and none were**: all seven backfill targets carry a real digest from a live 2026-08-06 fetch, 8 records across 7 files, each recording in its own note that the digest pins upstream as of the retrieval date rather than the exact bytes adapted, since the snapshot they were adapted from is gone. Verification re-fetched all eight independently and confirmed three attributions by content rather than by matching path names.
19. **Drift sensors that run outside the change lifecycle.** Every sensor this kit owns fires only when something invokes it: `validate.py` and `validate-skills.py` run in CI on a change, `doc-sync` runs when a human asks, and `check-provenance.py` is deliberately outside required CI because it needs network. Nothing watches for drift *between* changes. Added 2026-08-18, and the argument for it is the review pass itself: three of its findings (the shipped task template diverging from the kit's own, `autonomy.md` losing every inbound reference, a tier justification naming a skill that never mentioned the file) are drift that accumulated while every gate stayed green, and each was found by a human reading rather than by anything that runs. The framing is Birgitta Böckeler's guides and sensors (`martinfowler.com/articles/harness-engineering.html`), where a continuously running drift sensor is named as the gap current practice has not filled. Do not presuppose the artifact: a scheduled workflow, a `drift-watch` skill an adopter can run, and a widened `run-checks.py` gate are all candidates, and which one is right depends on whether the check is cheap and deterministic or needs judgment. **Acceptance bar: it must find something on a repository nobody has just reviewed.**
20. **A context and altitude lens** (hold until the `autonomy.md` wiring question is settled). Every source read in the 2026-08-18 research names context management as the primary harness lever, ahead of tooling and orchestration. This kit's strongest context-engineering asset is the agent reading protocol in `AGENTS.md` (read this file, your one task file, and only the files named in `touched_files`), and it lives in the scaffold the kit **emits** rather than as a lens the kit's own skills compose. A fourth module beside `house-style.md`, `review-quality.md` and `autonomy.md` would give skills a shared answer to what an agent reads, when to reset rather than continue, and what a subagent returns instead of its transcript. **Sequenced deliberately last:** `autonomy.md` was authored as the third lens and no skill composed it, so adding a fourth before that was resolved would have repeated the mistake rather than fixed it. **The gate is met as of 2026-08-19** ([`feat-0048`](.tasks/done/feat-0048-wire-the-autonomy-lens-into-the-skills.md)): five skills now compose `autonomy.md`, each naming the specific rule it takes, and `validate-skills.py` fails a self-declared lens with no inbound reference, so the condition this hold names cannot silently recur. **The hold is recorded as unblocked, not discharged** (2026-08-27, `chore-0066`): whether a fourth lens is now wanted is a separate judgment and it is the author's.

### Considered and declined (2026-08-05)

Recorded so the question is not reopened every time someone reads [`repoprompt-workflows`](https://github.com/moonray/repoprompt-workflows). Each was examined against this kit and rejected for the stated reason, not overlooked.

| Declined | Why |
|---|---|
| `track-work` (upstream skill) | Drives GitHub issues and a project board through `gh`. This kit's tracking is deliberately local, which is what keeps an agent's reading list short and works with no network and no account. `tracker-links` already covers the one direction that matters. |
| `Backlog` workflow | Triages tracked issues into worktrees. `new-task` plus `fix-batch` plus `reconcile-worktrees` already is this, authored against this kit's `.tasks/` model rather than RepoPrompt CE's. |
| `Spec` / `Test` / `Loop` / `Deep-Review` workflows, as whole artifacts | The discipline in each was already extracted into portable skills (`spec-author`, `test-author`, the spine, `house-review`). Taking the orchestration shells too would import RepoPrompt CE runtime assumptions for no gain. Specific mechanisms from them are taken individually as items 15 to 17. |
| Upstream's installer model | Symlink-only and macOS-only. `install.py`'s copy-on-Windows, symlink-on-POSIX, CONFLICT-detecting, manifest-reversible model is the more considered one and already ships. |



### Epic C: semi-scalable (teams and clients)

1. **`repo-explainer`.** A "start here" guided tour of an unfamiliar codebase.
2. **`sop-drafter`.** Turn a described workflow into a documented SOP.
3. **`security-audit`.** Repeatable dependency and secret scan with a written summary.
4. **`adr`.** Architecture decision records / decision log.
5. **`systematic-debugging`.** A phased root-cause procedure: reproduce, isolate, form and test one hypothesis at a time, then name the cause before proposing a fix. Added 2026-08-18 from the review pass, which found it to be the largest single hole in the workflow: the kit bootstraps, specs, decomposes, dispatches, tests, verifies, reviews, reconciles and documents, and has no skill for working out *why* something is broken. Diagnosis is both the most common real task and the one where an unguided agent most reliably guesses, and it is the natural upstream of `new-task`, since today a bug report becomes a task file with no step in between that establishes the cause. Prior art: the four-phase `systematic-debugging` skill in Jesse Vincent's `superpowers` (`github.com/obra/superpowers`, MIT), which occupies exactly this slot in a comparable library. Fold in under the provenance convention rather than writing from scratch, and hold the contribution bar: it ships only after it has been used on a real defect here. **Contract drafted 2026-08-18** as [`docs/spec/systematic-debugging.md`](docs/spec/systematic-debugging.md), 13 scenarios, **approved by the author on 2026-08-19** (`e492b10`), and **amended 2026-08-29 to 15** by `chore-0078`, which settled both of its Open Questions before anything was built against it: instrumentation lives only in a copy the run made for the purpose (`S-014`), a target offering no way to make one is answered rather than refused (`S-015`), and the default investigation bound stays out of the contract as a tuning value; it departs from the prior art in two decided ways, ending at a diagnosis that feeds `new-task` rather than at a fix, and returning a deterministic verdict rather than enforcing a gate. Its verdicts are now the kit's single classification vocabulary, and item 17 was retargeted to consume them. **Built 2026-08-29** by `feat-0061` and shipped as a **draft**, so no profile places it and no adopter receives it: fifteen structural tests, a conformance matrix at 15 of 15, and a provenance block pinning the upstream bytes. **Dogfooded 2026-08-29** by `feat-0062`, on the observatory's `database is locked` failure, and **it stays a draft**. The run produced a real diagnosis and the procedure demonstrably changed the answer, killing a wrong cause that reading the code alone had produced. It also produced a **second** wrong cause that passed the skill's own confirming-observation test, and an independent check refuted it: the trial the run called confirming was raising a SQLite busy timeout, which ends any wait whatever is waiting, so it was consistent with the hypothesis rather than a test of it. Five corrections went into the skill as a result, each asserted so it cannot be silently deleted, and the mutation set went to 25 of 25 killed. A skill whose first real use refuted its own output does not go in front of adopters on the strength of that use, so promotion waits on `feat-0063`: one run by a session that did not write it, on a defect it did not choose, whose diagnosis survives an independent check.

### Epic D: personal (stays OUT of the shared kit)

The Content OS pipeline (`produce`, `clip-machine`, `repurpose`, `video-editing`, `video-cutting`, `episode-brief`, `youtube-transcript`, `idea-discovery`) stays in `zen-solutions-studio` as portfolio demos, not plug-and-play kit skills.

### Epic E: delegated execution (cloud and unattended work)

Added 2026-08-07. The goal is to move the large majority of development into cloud agent sessions rather than a remote desktop, across this repository and several others, so work continues away from the machine. Everything in this epic follows from two properties of such a session, and neither is a limitation to work around: they are what the epic is designed against.

**A cloud session sees only what is committed.** This kit's own skills are installed at user scope by [`install.py`](scripts/install.py), and nothing here places them anywhere a clone would carry. So a cloud session that clones this repository has none of them loaded, and the repository that builds the kit is the one repository where the kit is absent. (This sentence opened with the measurement "`git ls-files .claude` returns nothing; the directory holds only `worktrees/`" until 2026-08-27, `chore-0066`. It stopped being true within a day of being written: item 2(b) below committed [`.claude/settings.json`](.claude/settings.json) on 2026-08-07 precisely so the reachability hook would reach these sessions, which the conventions section of [`AGENTS.md`](AGENTS.md) records as the kit's one committed hook registration and the one place it activates a hook on someone's behalf. The measurement moved; the conclusion it supported did not, so the conclusion stands on the user-scope install alone.) Anthropic's 2026 agentic coding trends report names this the delegation gap and puts structured intent specifications in the safeguard position, which is the spine Epic B already built.

**A cloud session cannot stop and ask.** Anthropic's own best-practices guidance makes this the deciding factor and answers it in one line, "give Claude a check it can run". Every interactive check this repository has is a person reading output, so the first item below turns the ones that matter into a command.

The gap exists only for the two global-scope harnesses. Claude Code and OpenCode discover skills from a global directory (`~/.claude/skills`, `~/.agents/skills`), while Cursor and VS Code get repository-level adapters from [`build-adapters.py`](scripts/build-adapters.py); neither adapter tree is committed here, which is a separate question held below rather than solved here.

**Design bar:** this maintainer's multi-repo workflow first, generalize after. The portability contract in the portability-contract section of [`AGENTS.md`](AGENTS.md) is a hard gate at ship time for the two items that generalize (4 and 5 below), and deliberately not a design constraint on items 1 and 2, which are allowed to be about this repository. Harnesses in scope: Claude Code, Codex, Cursor, Windsurf.

**Kit-wide autonomy ceiling.** An unattended agent pushes to a `claude/` branch and opens a **draft** pull request carrying its evidence report. It never merges. This is the ceiling for everything in this epic and is not an item's to relax.

1. **`autonomy.md` v1** (item 2a of the original decomposition, and deliberately first). **v1 authored 2026-08-07, not blessed**: it ships as a module and travels with the skills, but the contribution bar holds, so it stays unstruck until item 2's run has exercised it and item 3 has hardened it from what that found. **Ten rules as of 2026-08-27**, `A1` to `A10`, every one carrying its citation, plus three candidates named and held for want of one. Authored with eight; `A9`, verify the commit you are working from, was added by `bug-0043` from what the first real unattended run found, which is item 3 of this epic doing exactly what it exists for. The fourth held candidate, instructions embedded in material a skill reads, was added 2026-08-08 by `feat-0047` after a recorded four-pass search came back empty, and discharged as `A10` on 2026-08-27 by `chore-0071`, which accepted an external incident as the citation rather than waiting for either trigger it had named. A fourth swappable module at `.agents/rules/autonomy.md`, beside [`house-style.md`](.agents/rules/house-style.md) and [`review-quality.md`](.agents/rules/review-quality.md), organized around one named principle with the rules as its applications: **detect and report, never rewrite; the failure mode must be inaction.** This is a consolidation, not an invention. The principle is already applied in four independent places in this kit and named in none of them: [`doc-sync`](.agents/skills/doc-sync/SKILL.md) states it outright, [`house-review`](.agents/skills/house-review/SKILL.md) is report-only by protocol rule 6, `install.py --check` reports a stale copy and never refreshes it, and [`check-provenance.py`](scripts/check-provenance.py) reports drift rather than syncing, which `feat-0043` chose deliberately against upstream's in-place rewrite. **Every rule in v1 carries a citation** to where it was already exercised: a `file:line`, a task id, or a recorded incident. A rule that cannot be cited does not go into v1 and waits for item 3. That is [`feat-0040`](.tasks/done/feat-0040-evidence-gate-and-finding-signature.md)'s evidence gate applied to a rules module, and it exists because an invented rule reads exactly like a consolidated one and nothing else would catch the difference. The verified candidate pile: the sandbox rule stated explicitly rather than implied by isolation; never modify a file outside declared scope; verification is run by someone other than the agent whose work is verified; the validation command and its verbatim result as two separate fields, with no gap closed by inference from prose; disclose opportunistic work, grounded in two failures observed in `fix-batch` runs, an undisclosed test method that never existed in the repository's history and an undisclosed opportunistic bug fix; a partial audit is never reported as a whole one; never overwrite a file you did not create, report the conflict and stop; open a draft pull request and never merge your own work. [`bug-0018`](.tasks/done/bug-0018-reinstall-destroys-an-adopter-edited-lens.md) is the same principle failing in practice and is worth citing as such. Ordered before item 2 because running a cloud session with no autonomy module is the highest-risk configuration in this epic.

2. **Make this repository cloud-executable.** One Feature, kept whole rather than split, because its three parts are only worth anything together: a session that can check its work but cannot see the skills is as stuck as one that can see them and cannot check. Three parts.
    - **(a) The acceptance command.** One committed script, standard library Python, wrapping the seven gates in [`checks.yml`](.github/workflows/checks.yml), with CI calling it instead of restating them. One rule, two callers, per the precedent [`chore-0029`](.tasks/done/chore-0029-third-copy-of-the-link-rule-in-ci.md) set, where an inline copy of the link rule drifted and let a correctly quoted `CHANGELOG.md` entry pass `--strict` and fail CI. `AGENTS.md` names the script and states in these words that passing it is **necessary but not sufficient**, because CI runs three operating systems by two Python versions and the script runs one.
    - **(b) The bootstrap hook.** A `SessionStart` reminder, a new member of the [`.agents/hooks/`](.agents/hooks/README.md) module following the reminder shape and the opt-in installation contract [`feat-0038`](.tasks/done/feat-0038-hooks-module-and-delegation-reminder.md) set. Detect and report; it never writes. Registered with a `startup` matcher so it does not fire on resume, clear, compact, or fork. The mechanism is a repository-committed hook rather than an account-level environment setup script, because a setup script's output is filesystem-snapshotted for roughly seven days, so an edited skill could be served stale silently, which is the exact silent-wrong-result class this repository keeps getting bitten by. What it checks is **reachability** across project and user scope, with **no environment detection at all**: there is no shared cloud-detection signal across the three harnesses, so explicit detection would mean three detections for one question, which fails the portability contract.
    - **(c) The proof.** Run [`bug-0018`](.tasks/done/bug-0018-reinstall-destroys-an-adopter-edited-lens.md) end to end through `claude --cloud` under `autonomy.md` v1. **Chosen on 2026-08-07 over `feat-0042`, which this item was first drafted against, because that task's acceptance cannot see its own work**: it edits three skill-body files, and `validate-skills.py`, `validate.py --strict`, and the test suite all pass whatever the prose says, so a session could produce hollow text and clear every gate. `bug-0018` is P1 data loss in shipped code whose acceptance requires a regression test that **fails against the unfixed `install.py`**, which is an outcome a session cannot fake. A proof run whose check cannot distinguish real work from plausible work does not prove the thing this Feature exists to establish. `feat-0042` stays in the backlog, unchanged. **Repointed 2026-08-20** (`chore-0051`): `bug-0018` closed on 2026-08-08, one day after the runbook that dispatches it was written, so the target was spent and the run named here could not be performed, and nothing reported it because `validate.py --strict` passes precisely when the link resolves into `done/`. [`cloud-executable.md`](docs/spec/cloud-executable.md) amended `S-017` and `S-018` to name [`bug-0020`](.tasks/done/bug-0020-check-unknown-remedy-is-wrong-for-the-adopted-lens.md) instead, chosen **against the criterion in this paragraph rather than a weakened one**: it is a defect in `scripts/install.py`, so `S-018`'s "the unfixed `install.py`" stays literally true of it, and its first acceptance criterion already required a test failing against the current message.
    - **Acceptance, and it was met on 2026-08-20.** The bar is unchanged in every word except the target: the proof task lands via a cloud session that opened a draft pull request whose report meets the nine-field evidence contract from [`feat-0041`](.tasks/done/feat-0041-delegate-evidence-contract-for-fix-batch.md), with the acceptance script's verbatim output in it and the regression test shown failing before the change and passing after. `bug-0020` did exactly that, and is the first work in this repository implemented end to end by an unattended cloud session: branch `claude/bug-0020-unknown-remedy-lcqb52`, pull request #41 opened **draft** against `developer` and never merged by the session, all nine fields present with `run-checks.py`'s verbatim output at exit 0, and the two new tests reproduced failing against `developer`'s `install.py` and passing against the fixed one by a second session that did not write them. [`cloud-executable.conformance.md`](docs/spec/cloud-executable.conformance.md) moves `S-017`, `S-018` and the unattended-branch surface row to **Conformed** on that run. **The honest bound, because the run did not establish everything this Feature names.** `S-019`, the failure path, stays **Not-built**: the run's gates exited 0, so that path was never entered, and it was recorded separately in the first place for exactly this reason. `S-008` stays conformed on tests and unobserved in a real session, since the run was staged on a base 99 files behind `developer` and the hook that would have fired was the superseded copy, which `bug-0043` then fixed by gating the runbook's reading table on the base. The same run also produced a false finding, rediscovering `bug-0021` and offering it as new, because it was reading superseded code; the Conformed rows rest on evidence re-derived after the rebase, not on the report as first written. **Not struck through here**: whether this Feature is complete is the author's call and not a bookkeeping side effect. (Target and acceptance corrected 2026-08-27 by `chore-0066`, which found this line still naming `bug-0018` seven days after the contract had repointed it and the run had happened.)
    - **A fourth part was planned and is already done.** The presence half of the bootstrap comes from `install.py --check` failing loudly rather than from a second probe that would duplicate knowledge of where skills live. Checked on 2026-08-07: it already does. `check()` at `install.py:749` exits 2 naming the state as unrecorded when nothing is recorded beneath the given home, shipped by [`chore-0031`](.tasks/done/chore-0031-installed-skills-go-stale-with-no-signal.md) alongside the flag itself and pinned by a test at `tests/test_install.py:1079`. Recorded here rather than left in a report, because a non-defect nobody wrote down is one the next audit re-derives.

3. **Harden `autonomy.md` from what item 2's run revealed, then bless it.** A required task with real acceptance, not an intention. v1 ships deliberately thin, holding only rules this kit has already exercised, so the rules a real unattended run needs and nobody anticipated are found by running one. The contribution bar in the contribution-bar section of `AGENTS.md` forbids blessing it before that. **Both gates this item waits on are now met, and it is not therefore done** (recorded 2026-08-27, `chore-0066`). The composition gate closed 2026-08-19 with `feat-0048`, which is what the 2026-08-18 coherence pass named as gating this item: a lens no skill composes cannot be exercised, so it cannot clear the contribution bar. Item 2's run happened 2026-08-20 and has already fed this item twice, `A9` from `bug-0043` and `A10` from `chore-0071`, taking v1 from eight rules to ten. What is left is the blessing itself, which is a judgment on whether one unattended run and one external incident are enough evidence, and it is the author's.

4. **`cloud-ready` skill.** Generalize item 2's output to any repository, and audit a candidate against the readiness checklist using the severities in [`review-quality.md`](.agents/rules/review-quality.md). **Dogfood trigger already scheduled**, which is why this is a skill and not a note: the maintainer's other repositories have mixed secrets and interactive-authentication status and need auditing before any of them is delegated to. The skill must say plainly that a repository requiring single sign-on is a Remote Control repository, not a cloud-session one, because the failure otherwise is a session that starts, works, and cannot authenticate at the one step that mattered.

5. **`fix-batch` cloud mode.** One `claude --cloud` session per task file, replacing the worktree as the isolation boundary. The `feat-0041` contract is the acceptance gate unchanged, since it was written to be answerable from inside a single isolated workspace and a cloud session is one. **Reconciliation is the real delta and needs its own design rather than an assumption**: [`reconcile-worktrees`](.agents/skills/reconcile-worktrees/SKILL.md) lands verified work from a local directory, and a draft pull request per task is a different shape with different failure modes. Dogfood trigger: the next batch of three or more independent task files.

6. **Fixture-based skill evaluation suite under `tests/`.** Absorbs Epic A item 8, and belongs in this epic rather than that one because delegation is what makes it necessary: an unattended batch has no human reading each run, so the only evaluation that survives is one a command can run. State up front what it will and will not cover, because the honest bound is the useful part. Mechanical skills will cover well (the shape of a generated adapter, a validator's exit code, a task file's structure). Judgment-heavy lenses will cover poorly (`house-review`, `spec-quality`, `review-depth`), because a fixture can pin what a lens outputs and not whether the judgment was right, and a suite that pretends otherwise is worse than no suite. **Acceptance bar: the first run must catch a real regression.** A suite that passes on day one has proven only that it was written against today's behaviour. **Design supplied 2026-08-18** by the external research, which found the item's shape already right and two things missing from it. First, **measure a baseline without the skill**: Anthropic's skill authoring guidance is to build evaluations before documentation and to establish what the model does unaided, so the skill's contribution is isolated rather than assumed. This kit's contribution bar, no skill ships cold, is currently satisfied by a single dogfood run, which proves a skill works once against no control at all. Second, **trigger disambiguation**, which neither Anthropic's guidance nor the `superpowers-evals` precedent covers and which this kit needs most: with twenty skills whose descriptions average 759 characters and overlap heavily in vocabulary (`spec-author` / `spec-quality` / `spec-plan-readiness` / `spec-conformance`, `doc-author` / `doc-revise` / `doc-sync`, `test-author` / `test-quality`), the likeliest failure is not a skill behaving wrongly but the wrong skill being selected, and no current gate measures that. Both are mechanical enough to survive the fixture bound this item already states.

7. **Run telemetry, reporting, and bounds.** Absorbs Epic B item 13 phase 2. **Split into three parts on 2026-08-28** (`chore-0076`), because one paragraph was holding three items with three different hold states and could not say so. The hold it carried read: "Held behind item 5 for the reason it was never built in the first place, telemetry has no consumer while a human is watching every run, and item 5 is what first produces runs nobody is watching." That reason survives for (c) and for neither of the others, which is the whole reason the split was worth making rather than leaving the paragraph to be re-read charitably each time.
    - **(a) Capture.** Structured lifecycle events. **Unheld**, and owned by [`feat-0052`](.tasks/feat-0052-turn-on-telemetry-capture-before-the-bounds-that-need-it.md), whose argument is that the hold above is sound about dashboards and wrong about capture, and that the difference costs one environment variable with no backend, no collector, and no service. Capture-then-bound is the only order that works, so this precedes (c) and nothing precedes it.
    - **(b) Reporting. Delivered 2026-08-29**, all 22 scenarios of [`docs/spec/agent-observatory.md`](docs/spec/agent-observatory.md) conformed across eight tasks, `feat-0053` to `feat-0060`, audited in [`agent-observatory.conformance.md`](docs/spec/agent-observatory.conformance.md) at 22 + 0 + 0 = 22. Five rows carry a stated bound and the bounds are the part worth reading, chief among them that `S-017`'s quota half has no producer anywhere and its file format is this component's own invention. **It found things about this repository nobody had counted**: nine of the twenty-one skills in the roster have never been invoked, eight of them among the twenty that actually ship, and the one hook this repository commits has failed on every session start since 2026-08-07, 14 times, silently, which is now [`bug-0050`](.tasks/done/bug-0050-the-committed-hook-has-never-run-on-windows.md). A local surface over the session corpus this kit's own runs already produce. **Unheld, and it was never held**, which is a different claim from being unblocked: it depends on neither (a) nor item 5, because the transcripts it reads accumulate on disk whether or not telemetry is enabled and whether or not anyone is watching the run. It is also the first thing here that could answer the contribution-bar question mechanically, which the contribution-bar section of [`AGENTS.md`](AGENTS.md) asks of every skill and which is currently answered from memory. **It now carries one skill of its own, `agent-observatory`, and that skill is a draft**: `install.py` places it under no profile, including `all`, and it stays that way until it has been used on real work and blessed. It is the only route that reaches cloud and remote sessions, because the harness's own session index is reachable from inside a session and from nowhere else.
    - **(c) Bounds.** Retry and implementor/verifier-cycle limits, time or optional compute budgets, and a clear stop signal on a bound violation. **Still held behind item 5**, on the original reason quoted above, and now additionally behind (a): a bound set before its distribution exists is a guess with a number on it, which is what [`feat-0042`](.tasks/feat-0042-repeat-and-futility-classification.md) was filed to avoid and what the autonomy module refuses to do for retry limits.

8. **After-action promotion loop.** A step in the task closeout lifecycle in the work-altitude-model section of `AGENTS.md`, after `doc-sync`: did this run teach the kit anything reusable, and if so file it against the relevant `SKILL.md` or rules module. This is the compounding mechanism, and it is placed in the lifecycle rather than left to intention for the same reason the `doc-sync` step was, which is that its absence has already cost real work. Held behind items 5 and 6, because a promotion loop with no unattended runs to learn from, and no suite to catch what it breaks, is ceremony.

**Ordering.** The numbering above is reading order, not a strict sequence. These are the blocking edges.

```mermaid
graph LR
  E1[1 autonomy.md v1] --> E2[2 cloud-executable]
  E2 --> E3[3 harden autonomy.md]
  E2 --> E4[4 cloud-ready skill]
  E2 --> E6[6 skill evaluation suite]
  E3 --> E5[5 fix-batch cloud mode]
  E4 --> E5
  E7a[7a capture] --> E7c[7c bounds]
  E5 --> E7c
  E5 --> E8[8 after-action promotion]
  E6 --> E8
  E7b[7b reporting]
```

`7b` carries no inbound edge on purpose. It is the only item in this epic that nothing gates, and drawing it as a free node is the claim being made rather than an omission.

Compounding mechanisms in scope are the three above: the evaluation suite (6), run telemetry and the reporting over it (7a and 7b), and the after-action promotion loop (8). Model-capability seams, meaning routing an item to a model tier by the shape of the work, were considered and **declined as speculative**: there is no evidence here about which tier fails on what, and a seam built before that evidence encodes a guess as a contract.

#### Held, with triggers (Epic E)

| Held | Trigger to revisit |
|---|---|
| **Routines** (scheduled unattended runs) | Item 2 lands. Nothing is scheduled until one manual cloud session has completed successfully, because a schedule multiplies whatever the first run gets wrong. |
| **`routine-author` skill** | The second routine is wanted. One routine is a file; two is a pattern. |
| **Committed repository-scope adapters for Cursor and VS Code** | An actual Cursor or Copilot cloud session on one of these repositories. The trees are generated by `build-adapters.py` and committing them is cheap, but committing generated artifacts nobody reads is how a tree goes stale unnoticed. |
| **Self-hosted environments** | A repository that cannot use Anthropic-hosted sessions, or a client engagement requiring it. |
| **Slack and Claude Tag** | More than one person in a repository. Both are for handing work to an agent from where a team already talks, and there is no team here yet. |

#### Considered and declined (Epic E, 2026-08-07)

| Declined | Why |
|---|---|
| Devin-class agents | Unlike Codex and Cursor, it does not read `AGENTS.md`, so supporting it is a genuine new adapter rather than a free one, and it is not in the harness set this epic serves. **Revisit if** an adopter or client uses it. |
| Agent teams and emergent multi-agent coordination | It contradicts a position this kit already holds. Anthropic's own multi-agent research finds coding has fewer parallelizable subtasks than research and that models coordinate poorly in real time, which is why structural fan-out through `fix-batch`, one isolated agent per pre-scoped task file, is the supported shape here. **Revisit if** a real batch fails in a way coordination would have fixed. |

### Epic F: Sangha (multi-human, multi-agent workspaces)

**Unscheduled**, and deliberately so. This epic records a destination to steer by and to check current
work against. Nothing here is decomposed into task files, per the rule in the work-altitude section that
a Feature is decomposed only when it is actually about to be built.

The name: a **sangha** is a community practising under shared precepts, which is what a governed agent
workspace is, and the **vinaya** is the code that governs one, which makes it the natural name for the
compliance half if the two ever need separating.

**The property this epic exists to establish.** No collaborator, human or agent, is silently missing a
critical instruction, hook, or skill. Every item below is downstream of that sentence.

**The bounding fact, audited 2026-08-27.** This kit is single-user by construction and knows it.
Everything [`install.py`](scripts/install.py) places goes under `Path.home()`. The one record of what was
placed, `scripts/.install-manifest.json`, is gitignored, holds absolute machine-local paths on both sides,
and carries no timestamp and no identity, so committing it would not help. Every drift sensor answers only
about the machine running it. What **is** shared is substantial: `AGENTS.md`, the lenses, `.tasks/`,
`docs/spec/`, CI, three hook wirings, and the `eol=lf` policy that makes byte digests reproducible across
machines. The gap sits exactly at the seam between the committed half and the per-person half.

**The structural blocker, measured rather than assumed.** The only project-scope skill directory any
Claude Code harness reads is `.claude/skills/`, and nothing in this kit ever writes there.
[`install.py`](scripts/install.py) writes `~/.claude/skills` and `~/.agents/skills`;
[`build-adapters.py`](scripts/build-adapters.py) writes `.cursor/rules/`, `.github/prompts/`, and a plugin
tree. **So an adopting team has no supported path to share skills through their own repository**, and
nothing anywhere detects that a teammate is missing one. Item 1 is that blocker, and most of the rest
waits behind it.

1. **A project-scope distribution path.** A team must be able to share skills through the repository they
   already share, rather than through each person's home directory. This is the blocker above and the only
   item here not held behind another.
2. **Registration parity across harnesses.** Today a Codex or OpenCode collaborator gets four hooks
   automatically and a Claude Code collaborator gets one. Whatever the right answer is, the asymmetry
   should be a decision rather than an inheritance. Held behind the hook-coverage audit in Epic B item 13.
3. **Shared currency: does a teammate have what I have?** Nothing detects a missing or stale skill or hook
   on anyone else's machine, and `install-currency-reminder.py` states plainly that it cannot, because a
   manifest entry carries no back-pointer from an installed skill to where it came from. Closing this needs
   a new install-time surface, which is the same question Epic B item 19 holds. **Held until item 1 lands**,
   since a shared distribution path changes what there is to be current about.
4. **Ownership and review state in the work model.** `.tasks/validate.py`'s required fields carry no
   `owner`, `assignee`, `reviewer`, or `approver`, and the lifecycle has no review state between
   `in_progress` and `done`. **Held until more than one person works a backlog here**, on the same
   reasoning that holds Slack and Claude Tag in Epic E.
5. **Governance reproducible from a checkout.** There is no `CODEOWNERS` and no committed ruleset. The
   `main` protection that deadlocked the 2026-08-21 sync exists only as prose in `AGENTS.md` and is not
   reproducible from a clone. An enterprise story cannot have its controls live outside the repository.
6. **Grounding in an organisation's own data and codebases.** The part of this vision with the least prior
   art here, and the one that most needs a decision rather than a design. **It runs directly at a
   constraint this kit holds on purpose**: the tracking model is deliberately local, works with no network
   and no account, and `track-work` was declined for exactly that reason. Item 6 either inherits that
   constraint and exports to external systems, or overturns it, and that is a decision to make on purpose
   rather than to discover.

**The environment this is aimed at, recorded so the design is not drawn against an imagined one** (stated
by the maintainer 2026-08-27). Solo work: Claude Code with VS Code, GitHub, Cloudflare, GCP and Azure,
Supabase. Corporate and client work: Azure DevOps for repositories and boards, Microsoft Teams, SharePoint
and OneDrive, GitHub, Jira, ServiceNow, and a mixed agent surface of Codex, Cursor, Claude Code, Microsoft
Copilot 365 and GitHub Copilot. **This is context, not an integration list.** What it establishes is the
shape rather than the targets: work is tracked in more than one system, collaboration happens somewhere
other than the repository, and the agent surface is already plural, which is why items 1 and 2 are about
reaching every harness rather than the best one. Azure DevOps work-item linking already exists as Epic A
item 10, held until a real board is used, so the first concrete integration is scoped and gated elsewhere.

**A position to inherit or overturn deliberately.** The Epic E declined table rejects emergent multi-agent
coordination, on the evidence that coding has fewer parallelizable subtasks than research and that models
coordinate poorly in real time. The supported shape here is structural fan-out from one dispatcher, one
isolated agent per pre-scoped task file. A multi-human multi-agent workspace either inherits that stance or
overturns it, and doing so by accident is the failure mode worth naming now.

**Design bar, inherited from Epic E and restated because it binds harder here:** this maintainer's real
workflow first, generalize after. The contribution bar applies unchanged. No item here ships to the kit
cold, and a governance feature nobody has governed anything with is exactly the cold ship it forbids.

---

## Kit hardening (from the 2026-07-25 review pass)

A read of all 19 shipped skills on 2026-07-25, the first deliberate pass rather than a per-skill dogfood. It found four systemic issues and two gaps that need a decision before they can be decomposed. Filed rather than fixed, so each item can be dispatched to an isolated agent.

**All eight landed 2026-07-25**, the same day the pass that found them ran. Wave 1 was parallel-safe (disjoint `touched_files`); wave 2 waited on `bug-0002`, which touches the same files. The table stays as the record of what the pass found and how it was sequenced. (Corrected 2026-08-27, `chore-0066`; it read "Ready to dispatch" for the thirty-three days after the last of them closed.)

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

**All three branches are now exercised on real work**, each on a genuine trigger rather than a staged
one, and each recorded in the format `feat-0024` established:

- ~~**`verifier-agent`'s `blocked` verdict**~~ (`feat-0024`), at [`house-review.verification.md`](docs/spec/house-review.verification.md).
- ~~**`test-author`'s characterization mode**~~ (`feat-0027`), at [`install.characterization.md`](docs/spec/install.characterization.md).
- ~~**`spec-plan-readiness`'s blocking paths**~~ (`feat-0028`), at [`build-adapters.readiness.md`](docs/spec/build-adapters.readiness.md).

Each run found something the branch itself was not being tested for: an unresolved precondition
ambiguity (`chore-0014`), two testability defects in `install.py`, and a second seam between the
spine's front and back halves (`chore-0016`, now closed). Exercising a branch on real work has so far
been more productive than the branch coverage was the point of.

Both seams between the spine's halves are now closed. `spec-plan-readiness` was folded in from
upstream against a different planning artifact, and its Step 3 requirements had never been reconciled
against the task format this kit authors: `feat-0025` added task-to-scenario traceability and
`chore-0016` added risk and rollback notes. A full re-read of that list during `chore-0016` found no
third gap, so the two were the whole of it.
- **The wider spec and test coverage question.** Even after `feat-0024`, 5 of 19 skills will have a contract and none will have behavioral tests. Whether that gap is worth closing skill by skill, or whether the targeted-branch approach is sufficient, is a judgment to make once there is evidence from the first three exercises.

## Kit coherence hardening (from the 2026-08-18 review pass)

**Landed 2026-08-18, in one worktree-isolated batch of six**: `bug-0026`, `bug-0028`, `bug-0031`,
`bug-0032`, `chore-0041` and `feat-0049`. Two findings the batch itself surfaced were filed rather
than fixed and **both closed 2026-08-19**:
[`chore-0042`](.tasks/done/chore-0042-renormalise-the-authors-working-tree.md), the renormalise
remainder plus the two `Path.write_text` sites that can reintroduce the drift, and
[`chore-0043`](.tasks/done/chore-0043-amend-build-adapters-spec-for-the-code-span-exception.md), the
contract half of `bug-0028`, since six scenarios govern `rewrite_links()` and none of them excepts a
link that is not a link. `chore-0042`'s working-tree half turned out to rest on a wrong model of the
problem: the index was already LF throughout, so `git add --renormalize .` staged nothing, and there
is no renormalise commit, which is the correct outcome rather than a missed one. (Both had read as
open until 2026-08-27, corrected by `chore-0066`.)

The batch also hit the `fix-batch` dispatch trap for the second recorded
time: all six worktrees were cut from `origin/main` rather than from the dispatch commit, and four
of the six agents diagnosed and recovered from it unprompted.

The third kit-wide pass, and the first to ask whether the twenty skill bodies still agree with each
other and with the templates they ship. Every gate was green before and after: `run-checks.py`
reported 7 passed, `validate.py --strict` reported 114 task files with no errors, and the suite was
292 tests. That is the finding as much as any single item below. **None of the ten was reachable from
the acceptance command**, because every one of them is a claim in prose that stopped being true, and
no validator read a skill body for whether it agrees with another skill body. **Two of the ten are
reachable now**, and by the fix's own choice rather than by anything that existed on the day:
`feat-0048` taught `validate-skills.py` that a self-declared lens under `.agents/rules/` must have an
inbound reference, and `bug-0029` added a drift test over the two task templates' frontmatter keys
and section headings as sets. Noted 2026-08-27 by `chore-0066`, and it sharpens the finding rather
than softening it: the gates catch a class only once somebody builds the check for it, so a green run
says nothing about the eight that are still only prose.

Two are the kit's own named failure signature, something that reports success while doing nothing:

- **The shipped task template lost the two things two skills point at it for.** `fix-batch` tells
  every dispatched agent that the admissible decision-entry kinds are "defined once, in the target
  repository's task template", and `pr-describe` says "the task template owns which entries are
  admissible" and reads an `external` field to build GitHub closing references. Neither the
  `## Decisions` section nor the `external` field exists in `_TEMPLATE.md.tmpl`, so in every
  repository this kit scaffolds, one instruction is a dangling pointer and one feature can never
  fire. Scoped as [`bug-0029`](.tasks/done/bug-0029-shipped-task-template-lost-decisions-and-external.md)
  and **shipped 2026-08-19**: both are now in the shipped template, and the durable half is a drift
  test over the two templates' frontmatter keys and section headings as sets, verified failing
  against the pre-change template. The acceptance criterion as authored asked for that test over the
  *required* keys and `external` is optional, so the test as specified could never have caught the
  defect it was written for; the agent widened it to the full declared key set and recorded the
  rejection rather than satisfying the wording.
  This settles the question [`bug-0026`](.tasks/done/bug-0026-scaffolded-validator-lost-the-external-check.md)
  deliberately deferred as "a separate and arguable question": it is not a question of whether to
  teach an adopter the field, because two shipped skills already treat the template as the authority.
- **`doc-sync`'s prescribed link check cannot see the documents `doc-sync` edits.** It names
  `python .tasks/validate.py --strict`, whose default mode walks `.tasks/` only, while the documents
  `doc-sync` classifies as current-state and edits are `README.md` and `docs/*.md`. The check passes
  instantly having checked nothing. Scoped as
  [`bug-0031`](.tasks/done/bug-0031-doc-sync-link-check-does-not-reach-the-edited-document.md) **Shipped 2026-08-18** (`bug-0031`), and reproduced live during the same session's closeout, when a task-file rename left a `ROADMAP.md` link dead and `--strict` passed anyway..

The rest:

- **`autonomy.md` is a declared lens with zero inbound references.** It opens by naming itself the
  third module beside `house-style.md` and `review-quality.md`, and links outward into five skills;
  none of the twenty links back. Compare 20 of 20 composing `house-style.md`. The consolidation runs
  in one direction only, so an agent following a skill body never reaches the ceiling, and a lens no
  skill composes cannot be exercised, which means it cannot clear the contribution bar. This is the
  gating item under Epic E #3. Scoped as
  [`feat-0048`](.tasks/done/feat-0048-wire-the-autonomy-lens-into-the-skills.md) and **shipped
  2026-08-19**: the lens was then referenced from exactly the five skills whose rules it holds
  (`doc-sync`, `fix-batch`, `pr-describe`, `spec-conformance`, `verifier-agent`), each naming the
  specific rule it takes, and that set matched the lens's own outbound link list. **Superseded
  2026-08-29 by [`feat-0064`](.tasks/done/feat-0064-make-a10-reach-the-skills-that-read-outside-content.md),
  which took it to all twenty-two.** Five was a tight rule for a lens whose rules were about how an
  agent behaves unattended, and the wrong rule once `A10` was added on 2026-08-27, since that one is
  about material an agent reads and every skill reads something. The lens now declares
  `**Scope: universal.**` and a second validator rule enforces it, so the wiring list is derived from
  the lens rather than pinned to a set a later rule outgrew. The durable half is
  a new `validate-skills.py` rule, that a file under `.agents/rules/` declaring itself a lens must
  have an inbound reference; writing it found that `main()` had never opened `.agents/rules/` at all,
  which is why an unwired lens was invisible to every gate. **This closes the gate it names under
  Epic E #3, and the one Epic B #20 names in the same words.** Recorded as met, on 2026-08-27 by
  `chore-0066`, and neither hold is discharged here: that is a judgment and it is the author's.
- **The lite tier scaffolds a required field that cannot be satisfied.** Lite ships no `ROADMAP.md`,
  `_TEMPLATE.md.tmpl` seeds `parent: "ROADMAP#N feature-slug"`, `parent` is required by the shipped
  validator, and `new-task` demands a real ROADMAP parent and offers to add a Feature to a file that
  is not there. `new-task` never mentions the tier. The "Tier stripping at lite" list omits the
  template. Scoped as [`bug-0030`](.tasks/done/bug-0030-lite-tier-parent-field-has-no-roadmap-to-name.md)
  and **shipped 2026-08-19**: the template's `parent` comment names both forms, the tier-stripping
  list covers it, and `new-task` now detects the absence of `ROADMAP.md` and branches rather than
  offering to add a Feature to a file that is not there. The fix was cheap because the shipped
  validator checks `parent` for presence with no format rule, so free text at lite needs no validator
  change; that is written into the task's decisions as the thing to revisit if a consumer ever parses
  the field.
- **`test-author` is the one spine skill that will derive tests from an unapproved contract.** It
  names an approved spec as its input three times and gates only on well-formedness, while
  `verifier-agent` blocks on a non-`approved` status and `new-task` refuses one outright. Tests are
  the most durable form an unapproved contract can take, because they outlive the draft. Scoped as
  [`bug-0032`](.tasks/done/bug-0032-test-author-never-checks-the-spec-is-approved.md) **Shipped 2026-08-18** (`bug-0032`), with characterization mode explicitly exempt so the mode for code with no contract stays reachable..
- **Four prose claims that stopped being true**, bundled because each is a line or two with no design
  question behind it: `init-worktracking`'s tier justification names `fix-batch` as one of three
  skills that run `validate.py` unconditionally, and `fix-batch` has never mentioned the file; four
  skills state four different versions of the kit spine and none matches the README diagram, which is
  the only correct one, and neither `spec-author` nor `verifier-agent` appears in any of them;
  `fix-batch` points worktree agents at `test-author` without naming the characterization mode those
  agents actually need; and `spec-conformance` writes a report to disk by default while
  `verifier-agent`, which composes it, promises no file unless a destination was supplied. Scoped as
  [`chore-0040`](.tasks/done/chore-0040-four-coherence-corrections-across-skill-bodies.md) and
  **shipped 2026-08-20**: all four premises were re-derived rather than inherited and all four still
  held, despite `bug-0030`, `bug-0032` and `feat-0048` having landed on the same files in between.
  Two things the task file itself got wrong are the useful part: `pr-describe` carries two spine
  statements rather than one, and the README diagram the task named as the correct reference is
  itself wrong, filed and since closed as `bug-0039`.
- **Thirty tracked files are CRLF on disk against an `eol=lf` policy**, with `core.autocrlf=true` set
  at repository scope pulling the other way and a `.gitattributes` comment describing behaviour the
  next line overrides. Invisible to `git status`, because `text=auto` normalises on the way back in,
  and material because two comparators here read bytes off disk rather than through git. Scoped as
  [`chore-0041`](.tasks/done/chore-0041-working-tree-crlf-against-the-eol-lf-policy.md) **Shipped 2026-08-18** on its policy half (`chore-0041`). The run falsified two of the finding's own claims: `core.autocrlf=true` sits at system scope, the Git for Windows installer default, not at repository scope, so there is nothing to unset; and a fresh worktree reports `0` at `w/crlf` against this checkout's `30`, so the drift is one machine's. The renormalise remainder, re-scoped accordingly, is [`chore-0042`](.tasks/done/chore-0042-renormalise-the-authors-working-tree.md)..

Two findings were **not** filed, and are recorded here so a later reader does not take the silence
for an oversight:

- **`review-depth` measures a path-scope review against the wrong quantity.** For `house-review`'s
  path-scope-with-no-range mode it computes `reviewable_lines` from a diff over the scoped paths,
  which measures the change to those files rather than their length, while `house-review` then reads
  them in full. Downgraded on reproduction rather than dropped: the skill does carry an explicit
  fallback for an unmeasurable signal and does handle a path scope in its Inputs, so this is a
  measurement mismatch, not the unhandled gap it first appeared to be. Not worth a task until
  someone hits it.
- **`doc-author` (55 lines) and `doc-revise` (46) are structural outliers**: no numbered procedure, no
  Inputs section, roughly a third the size of every other skill, while `doc-sync` (301 lines)
  composes `doc-revise` "by reference for the editing half". Left to the author's judgment, because
  the useful frame for it is Anthropic's degrees-of-freedom rubric (high freedom where many
  approaches work, low freedom where the path is a narrow bridge) and applying that rubric across the
  kit is a larger decision than repairing two files.

One candidate was **dropped** on reproduction: that `review-depth` has no handling at all for
`house-review`'s first review mode. Both the fallback and the path-scope input exist.

The external benchmark that ran alongside this pass produced Epic C #5, Epic B #19 and #20, and the
design amendment to Epic E #6. Its finding about the kit's own architecture is worth recording here
rather than only in the epics: read against Prithvi Rajasekaran's harness-design write-up for
Anthropic, all four of the levers he names are already implemented here, and his closing rule, only
increase complexity when needed, is the one to hold against a kit at twenty skills. The two
measurable divergences from Anthropic's skill authoring guidance are that progressive disclosure is
enforced (`MAX_BODY_LINES = 500`) and exercised nowhere (zero `references/` directories, 18 of 20
skills a single file, `fix-batch` at 396 lines then and 479 when re-measured on 2026-08-27), and that
descriptions average 759 characters against
a 1024 ceiling, so roughly 15,000 characters of metadata load before any skill triggers. Both are
trades worth making knowingly rather than by accretion; neither is filed.

---

## Out of scope by design

- No database or service dependency in anything the kit ships. [`install.py`](scripts/install.py) places `.agents/skills/`, `.agents/rules/`, and `.agents/hooks/` and nothing else, and nothing in those three asks an adopter to stand up a runtime, a store, or a process: they are markdown, `SKILL.md`, and stdlib Python. Portability is the whole point, and portability is a property of what an adopter receives rather than of what sits in this repository. **Maintainer tooling that reaches no adopter tree is outside this bullet and is not thereby unconstrained**, because the stdlib rule in the conventions section of [`AGENTS.md`](AGENTS.md) still governs it: standard library only, so the acceptance command keeps running on a bare Python 3 with no install step on every cell of the CI matrix. Scoped from "anywhere in the kit" on 2026-08-28 by `chore-0076`, which needed a local store and a local server for [`docs/spec/agent-observatory.md`](docs/spec/agent-observatory.md) and found this sentence forbidding both in five separate documents.
- No skill ships to the kit cold. A skill is drafted, used on real work, iterated, then blessed. Speculative skills stay at this roadmap altitude, not in `.agents/skills/`.
