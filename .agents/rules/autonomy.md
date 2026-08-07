# Zen autonomy lens (edit freely)

This file is a **swappable module**, the third beside [`house-style.md`](house-style.md) and
[`review-quality.md`](review-quality.md). Those two govern how an agent writes and how it reviews.
This one governs what an agent may do **when nobody is watching**: in a worktree, in a batch, in a
cloud session, in any run where the answer to "should I?" cannot be a question put to a person.

It is separated from the skills so an adopter can retune the ceiling, or replace it with their own,
without touching skill logic. If you are adopting this kit: keep it, empty it, or rewrite it.

**v1 is a consolidation, not an invention.** Every rule below was already being applied somewhere in
this kit, in prose, one skill at a time, without the thing they have in common ever being named.

## The principle

> **Detect and report, never rewrite. The failure mode must be inaction.**

An unattended agent that does too little leaves work on the table, and a person picks it up. An
unattended agent that does too much destroys work nobody knew it touched, reports success, and the
loss surfaces later with no trace of what caused it. Those two failures are not symmetric, so the
rules below all lean the same way: **when uncertain, stop and say so.**

The principle is not new here. It is already applied in four independent places, and named in none
of them:

| Where | How it shows up |
|---|---|
| [`doc-sync`](../skills/doc-sync/SKILL.md) | States it outright: dry run is the default, detection never changes a file, and a contract document is never edited because a disagreement there means the code is wrong. |
| [`review-quality.md`](review-quality.md), protocol rule 6 | "Report only. State the findings and the suggested fixes. Do not edit or commit anything." |
| `scripts/install.py`, the `check()` docstring | Carries the sentence verbatim: "Detect and report, never rewrite. Re-installing is a person's decision." |
| `scripts/check-provenance.py` | Reports drift and never syncs, deliberately declining upstream's in-place rewrite, because every fold-in here was adapted and an overwrite would destroy the adaptation. |

Four independent authors of four unrelated components reached the same rule. That is the argument
for writing it down once.

## Why every rule here carries a citation

Each rule names where it was already exercised: a file and line, a task id, or a recorded incident.
**A rule that cannot be cited does not belong in v1.**

This is the evidence gate from [`review-quality.md`](review-quality.md) applied to a rules module,
and it exists for one reason: an invented rule reads exactly like a consolidated one. Both are one
confident sentence in the imperative. Nothing about the prose distinguishes a constraint this kit
learned by losing work from a plausible-sounding rule someone thought of while writing this file, and
a module that mixes the two silently spends the authority of the first on the second.

References to files outside the installed skill tree are named in prose rather than linked, per the
portability contract in `AGENTS.md`: this module ships to adopters without this repository around it,
so a link that escapes the tree would resolve here and dangle everywhere it actually runs.

## Scope: what you may touch

**A1. Stay inside your sandbox, and treat the boundary as a runtime rule, not a starting state.**
Never read, write, or run any command against any path outside your assigned workspace, for any
reason: not to sync your changes, not to work around a missing file, not to check something in the
main checkout. If you believe you need to reach outside it, that is a blocker to report, not a
problem to solve.

*Cited:* [`fix-batch`](../skills/fix-batch/SKILL.md), the dispatch-prompt section, states this
verbatim and says why: worktree isolation is a starting-state guarantee, not a runtime sandbox, and
nothing stops a shell call from going wherever it wants unless you say so directly. *The incident:*
an agent in an isolated worktree used a shell to reach outside it and overwrite a file in the main
checkout with a stale copy, destroying unrelated uncommitted work that had nothing to do with its
task.

**A2. Change only what your task scoped. Anything extra is a finding, not a bonus.**
Work outside your declared scope is not a favor to the reviewer, because they cannot tell the
difference between a helpful extra and a mistake without investigating it, and you have given them no
reason to look.

*Cited:* `fix-batch`, the verification step: "Confirm the changes touch only the files the task scoped
it to. Anything extra is a finding, not a bonus, investigate it, do not assume it is helpful just
because tests pass."

**A3. Never overwrite a file you did not create. Report the conflict and stop.**
This holds even when you are confident the replacement is better, and it holds most strongly for
files an adopter was invited to edit.

*Cited:* `scripts/install.py`, module docstring: "Never clobbers a real file it did not create: such
a target is reported CONFLICT and skipped for you to resolve." Pinned at contract level as `S-004` in
the `install` spec, and again as `S-010` in the `build-adapters` spec, where a rules file already
present in the target project is never overwritten. *The counter-example worth citing:* task
`bug-0018` is this rule failing in shipped code. `install.py` removes and replaces the rules
directory on re-install, so an adopter's edited lens is destroyed silently at exit 0, in the one file
the kit specifically asks them to make their own. The rule was written down in one half of the
distribution path and not implemented in the other.

## Evidence: what you may claim

**A4. The validation command and its verbatim result are two separate fields, and prose closes no gap
between them.**
Report the command exactly as typed, and the verbatim tail of its output. Not a summary of the
output, not a description of what it means, not "tests pass".

*Cited:* `fix-batch`'s delegate evidence contract, the `validation command` and `validation result`
rows, established by task `feat-0041`. The reason recorded there is the whole point: "the validation
command and its result" cannot be answered in prose without either running it or lying.

**A5. Disclose opportunistic work. Silence is not the same as "none".**
If you found or fixed something that was not the assignment, say so explicitly. An empty findings
field must mean you looked and found nothing, and it must be impossible to reach by not mentioning
it.

*Cited:* `fix-batch`'s findings field states it directly: "`none` is a valid answer and is not the
same as silence." *Two recorded incidents, both from the same batch:* an agent fabricated an extra,
undisclosed test method that had never existed in the repository's history and then miscounted it as
one of the originals; and a different extra change initially looked like fabrication and was nearly
deleted, when it turned out to be a real, previously undiscovered bug fix the agent had found
opportunistically and never disclosed. Both directions cost the reviewer the same investigation, and
disclosure would have cost the agent one sentence.

**A6. A partial audit is never reported as a whole one.**
State what you checked and what you did not. A clean result over a subset is not a clean result, and
the difference is invisible to anyone reading only your conclusion.

*Cited:* [`spec-conformance`](../skills/spec-conformance/SKILL.md) requires a coverage proof and says
an empty result is valid only alongside the audited set, because "no divergence" requires positive
evidence that the whole spec was checked. *The incident:* a conformance matrix asserted it had
audited "S-001 through S-014, every spec item" beside a spec carrying fifteen scenarios, recorded in
task `feat-0036`'s closeout and named again in `chore-0033` as the reason to state both counts and
the arithmetic rather than the claim.

**A7. Verification is run by someone other than the agent whose work is verified.**
Do not verify your own implementation and record the result as independent evidence. Where the
harness allows the separation, take it; where it does not, say which agent produced the verdict.

*Cited:* [`verifier-agent`](../skills/verifier-agent/SKILL.md): "Independence is the point. Where the
harness allows the separation, the agent that verifies should not be the agent that wrote the
implementation. Self-verification is the failure mode this skill exists to remove."

## Landing: what you may do with the result

**A8. Push to a branch of your own and open a draft pull request. Never merge your own work.**
The ceiling for any unattended run. Carry the evidence report in the pull request body. Landing it is
a person's decision, and an unattended agent never makes it.

*Cited, with one honest qualification.* The shape is exercised:
[`pr-describe`](../skills/pr-describe/SKILL.md) is "draft text only, never touches GitHub", printing
both artifacts and surfacing the command rather than running it, so the agent prepares and a person
dispatches. **The specific ceiling, a `claude/` branch and a draft pull request that is never merged,
is a decision recorded in `ROADMAP.md` Epic E rather than a rule this kit has already run under.** It
is the only rule in v1 in that position, it is named as such rather than dressed up as consolidated,
and confirming or amending it against a real unattended run is the first job of v2.

## Considered for v1 and held, for want of a citation

The gate is only real if it excludes things. These were wanted and left out, because this kit has not
run into them yet and a plausible number is not evidence:

- **Retry limits and futility classification.** Scoped as task `feat-0042`, which states honestly
  that it is preventive rather than observed, and carries its own kill criterion.
- **Token, wall-clock, or compute budgets.** Held as Epic E item 7, behind the batch mode, because a
  bound with no observed run to calibrate against is a guess with a number on it.
- **Escalation paths, meaning when an unattended agent should stop and wait for a person rather than
  reporting and finishing.** Real, and currently unanswerable: nothing here has run unattended long
  enough to know where the line falls.

## Scope

These are defaults, not laws. A skill may state a local exception, and a downstream adopter may
raise or lower the ceiling, drop rules, or replace this module entirely. One default is worth keeping
whatever else changes: **the asymmetry**. An adopter who relaxes A3 or A8 into "use your judgment"
gets back the failure this module was written for, which is not an agent that did too little.

The point of pulling it into its own file is that the override is a one-file edit, and no adopter
inherits a ceiling they did not choose.
