---
id: feat-0035
title: Draft the review-depth skill (deterministic review-effort selection composing house-review)
type: feat
status: in_progress
priority: P2
parent: "ROADMAP Epic B #10: review-depth"
depends_on: []
touched_files:
  - .agents/skills/review-depth/SKILL.md
created: 2026-07-29
---

## Problem

ROADMAP Epic B item 10 is `review-depth`: select quick, standard, or deep review from deterministic
signals (change size, directory spread, severe risk flags, blast radius, documentation-only scope),
compose it with [`house-review`](../.agents/skills/house-review/SKILL.md) so review effort matches
risk, and let an explicit user choice always override detection.

Today `house-review` has exactly one effort setting. Its Step 2 already tells the reviewer to bound
the read against the diff stat, subtract material that carries no review signal, and order the rest
by risk, but it says nothing about how hard to look once the reading is bounded. So a one-line
README typo fix and a 900-line change across `scripts/`, `tests/`, and `docs/spec/` get the same
treatment: the same rubric sweep, the same depth of context, the same reporting floor. In practice
that means one of two failures, and which one you get depends on the reviewer's mood rather than on
the change. Either small changes are over-reviewed, which trains the author to skim reviews, or
large risky ones are under-reviewed, which is the failure that actually costs something.

The gap is not the rubric, which is settled in [`review-quality`](../.agents/rules/review-quality.md).
It is that nothing decides how much reviewing a given change has earned, and nothing makes that
decision reproducible. Two runs over the same diff should reach the same depth, and the reason
should be inspectable rather than felt.

## Scope

**In scope:** author `.agents/skills/review-depth/SKILL.md`, harness-agnostic, delivering:

- a stated signal table computed from the same changeset `house-review` reviews (reviewable changed
  lines, directory spread, trust-boundary risk flags, blast radius, documentation-only scope), with
  every threshold written as a number rather than a feeling;
- an ordered, first-match-wins selection rule over those signals, so the same signal table always
  yields the same depth;
- three depths (`quick`, `standard`, `deep`) defined **only** as settings on knobs `house-review`
  already exposes: how much is read around the changed lines, how exhaustively the rubric is swept,
  and the lowest severity worth writing down;
- an explicit user choice overriding detection unconditionally, with the detected depth still
  reported so the override is visible rather than silent;
- a deterministic output block naming the depth, whether it was detected or chosen, every signal
  value, the excluded paths, and the exact rule that fired;
- a stated fallback (`standard`, announced) when a signal cannot be computed, so an unmeasurable
  change never silently becomes a cheap review.

**Out of scope:** blessing the skill, which waits for the dogfood evidence and explicit author
sign-off; striking the roadmap item through, adding a `docs/CATALOG.md` row, or adding a
`CHANGELOG.md` line, all of which claim shipped status this task has not earned; **any edit to
`.agents/skills/house-review/SKILL.md`** or to the two rules modules (if composition needs a change
there, report it as a finding rather than making it); writing a `docs/spec/` contract for this skill;
a multi-lens deep review that runs `test-quality` alongside `review-quality`, which is
`house-review`'s own stated future direction and a separate piece of work; and `maintainability-review`
(Epic B item 11), whose lens a future `deep` depth might compose but which is not built.

## Implementation notes

- **Compose, do not restate.** [`chore-0010`](done/chore-0010-spec-plan-readiness-compose-test-quality.md)
  exists because `spec-plan-readiness` copied `test-quality`'s layer taxonomy inline and created two
  copies free to drift. The same trap is wide open here: it is tempting to explain what a deep review
  checks by listing the eight rubric categories. Do not. The categories and the four severities stay
  in [`review-quality.md`](../.agents/rules/review-quality.md), reached by link. The trust-boundary
  classes that set a risk flag are `house-review` Step 2's own ordering classes, referenced rather
  than re-enumerated; what this skill adds is a mechanical way to detect them, not a second list of
  what they are.
- **What depth may not touch.** Report-only posture, the validate-before-reporting rule, and the
  severity definitions are the lens's, and no depth weakens any of them. A `quick` review is a
  smaller read, never a lower standard of proof for a finding. State this explicitly, because
  "quick" invites exactly that reading.
- **Order the selection rule so escalation wins.** Check risk flags and blast radius *before*
  documentation-only. In this repository that ordering is load-bearing rather than theoretical: an
  approved contract under [`docs/spec/`](../docs/spec/) is a markdown file, so a change that edits
  one is documentation-only by file type and high blast radius by meaning. The order is what stops a
  contract edit from being waved through as a docs change.
- **Be honest about where determinism ends.** Line counts, directory counts, and file-type checks are
  mechanical. Deciding whether an unusual file is generated or vendored is judgment, and so is
  whether a symbol is a public surface. The skill gets reproducibility by *recording* those calls
  (every excluded path, every flagged file) so a rerun can be compared, not by pretending the call
  was never made. Say so rather than overclaiming.
- Mirror the shape of a sibling workflow skill: positioning intro, `## When to use` / `## When not to
  use`, `## Inputs`, numbered `## Procedure`, `## Output format` with a deterministic schema in a
  fenced `text` block, `## Notes`, `## Conventions`.
- Frontmatter must match the schema the sibling skills carry, including `license: MIT` (this is
  kit-authored, not a fold-in). Copy it from a sibling rather than inventing it. Keep `description`
  under 1024 characters and free of angle brackets, and write it as a block scalar so a real YAML
  parser can read it. The `bug-0007` and `bug-0008` task files in `.tasks/done/` record what went
  wrong here before, and why each of those constraints is an error rather than a preference.
- Follow [`.agents/rules/house-style.md`](../.agents/rules/house-style.md); keep the body under the
  500-line guideline; any diagram is Mermaid.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

Every box below was run on 2026-07-31 rather than inferred; the figures are from that run.

- [x] `.agents/skills/review-depth/SKILL.md` exists, with `name: review-depth`, a `description` that
      says both what it does and when to use it, and `license: MIT`.
- [x] `python scripts/validate-skills.py` exits 0 with no new warnings and no new errors. 20 skills,
      0 errors, 0 warnings.
- [x] `python .tasks/validate.py --strict` exits 0. 68 task files, 0 errors, 0 warnings.
- [x] `python -m unittest discover -s tests -p "test_*.py"` exits 0, unaffected by this change. 86
      tests, OK.
- [ ] `python scripts/build-adapters.py --dry-run` and
      `python scripts/install.py --dry-run --home ./.tmp/zen-home` both exit 0 and include the new
      skill. **Not met as worded, and the wording is what is wrong.** Both exit 0, and
      `build-adapters.py` generates the 2 expected adapter files. The install command does not
      mention the skill at all, correctly: its default is the `spine` profile, the skill is not in the
      spine seed and no spine member references it, so profile closure excludes it and the run reports
      17 of 20. `--profile all` places it (2 lines). Amend the criterion to name `--profile all` for
      the placement check, since the default profile excluding an unreferenced skill is the `feat-0033`
      behaviour working rather than a failure.
- [x] The body names exactly three depths (`quick`, `standard`, `deep`) and states one ordered
      selection rule whose branches are mutually exclusive, so one signal table yields one primary
      depth. Amended after the dogfood: when the risk rule fires it also yields a remainder depth for
      the unflagged files, so the pair is as reproducible as a single value. Amended again on
      2026-07-31, because the first wording ("derived from the same table by the same ordered rule")
      described the defect: the remainder is now derived from its **own** re-measured table, with the
      anchors' lines and directories excluded, and capped at `standard`.
- [x] Every threshold in the selection rule is a stated number, not an adjective.
- [x] The body states that an explicit user choice overrides detection, and that the detected depth
      is still reported when it is overridden. Amended after the override run: when detection would
      have escalated, the files it would have escalated on are reported too, since a dropped anchor
      list is the one way an honoured override still misleads.
- [x] The output block carries the changeset identity, so the depth and the review it governs
      provably describe the same range rather than two independently resolved ones. The handoff run
      found this insufficient in one respect: identity is recorded, provenance is not. See finding 5
      in the dogfood evidence below.
- [x] The body contains no copy of the rubric category list and no copy of the severity definitions;
      both are reached by relative link to `review-quality.md`.
- [x] `.agents/skills/house-review/SKILL.md` and both files in `.agents/rules/` are byte-identical to
      their state before this task (`git diff --stat` shows neither). The commit touches 2 files.
- [x] Every relative markdown link added resolves to a file that exists, both on disk and under the
      shipped layout (no link escapes the `.agents/` tree). All 5 resolve, and
      `validate-skills.py::check_links` enforces the portability half rather than it being checked by
      hand.
- [x] No em-dashes; headings sentence case.

## Dogfood evidence

Recorded 2026-07-31. Ranges and commands are given so every row can be re-run rather than trusted.
No relative links are added in this section on purpose: see the closeout note at the end.

### The `house-review` handoff, run end to end

Changeset `8ff7d49^..8ff7d49` (`chore: add a code of conduct and a pull request template`), chosen
because it is anchored and because the skill body already cites it, so the run doubles as a check on a
claim the skill makes about itself. The range was supplied explicitly, which is itself a finding
(item 1 below).

| Signal | Value |
|---|---|
| `reviewable_lines` | 407 (404 added, 3 deleted, `git diff --numstat -M`) |
| `directories` | 4 (`.`, `.github`, `.github/workflows`, `.tasks/done`) |
| `risk_flags` | `.github/workflows/checks.yml`: subprocess, and the workflow's permissions block |
| `blast_radius` | `.github/workflows/checks.yml`: named kind, CI workflow |
| `documentation_only` | false |
| `excluded` | none. No lockfile, generated, vendored, minified, or fixture material in range |

Selected `deep` on the single anchor and `remainder_depth: standard` for the other 7 files, by R2 then
R7. **Judged right by hand.** The body's claim that this commit "gets a deep read of the workflow and
a `standard` read of the prose" reproduced exactly, and every finding came from the 10 changed CI
lines, which is the outcome the anchoring exists to produce.

What the two legs cost: the deep leg read the workflow in full as of that commit plus the three
dependents its own comments reference (`scripts/validate-skills.py`, `.tasks/validate.py`, and
`README.md`'s Python floor claim, which matches the matrix at 3.11). The standard leg read the 7
remaining files as a diff with context. Two of seven candidate findings were dropped at the lens's
validate step, both because a dependent already covered the gap, which is the check working.

Findings: 1 major, 3 minor, 1 nit, all on the anchor; the remainder came out clean and is recorded as
clean rather than padded. The major one is mechanically reproducible: CI's link step and
`python .tasks/validate.py --strict` both pass while 101 relative links are broken across 36 files in
`.tasks/done/`, because CI globs root, `.github/`, and `docs/` only and `.tasks/validate.py` has no
link check at all. Root cause is the closeout move: `../` in a task file is correct in `.tasks/` and
one level too shallow in `.tasks/done/`. `.agents/` was checked and is **not** a gap, which is why the
finding names one tree and not two: `validate-skills.py::check_links` covers it, and 0 of its 115
relative links are broken.

### Findings against the handoff, reported rather than patched

Per this task's out-of-scope list, nothing below was fixed in `house-review` or in either rules
module.

1. **`house-review` Step 1 defines no explicit-range mode.** Its two modes are an explicit path scope
   and branch against merge-base with a working-tree fallback. Reviewing a historical commit needs a
   range neither mode produces. **Corrected 2026-08-03**: this originally said Step 2 assumes such a
   range exists. It does not. The presuming sentence ("a path scope with an explicit base or range is a
   narrowed change review") is at `house-review` Step 1 line 61, inside the same step that names only
   two modes, which makes the finding sharper rather than weaker: the step contradicts itself. Found by
   the agent dispatched for this finding, and verified here. **The gap is also in the approved
   contract**, which is why it is not a one-line edit: `docs/spec/house-review.md` permits "a base, or
   a commit range" at Invocation (line 151), then enumerates three Modes whose third is "a path scope
   plus a range" (line 152), and gives a Range resolution chain with no explicit-range branch (line
   153). No scenario covers a bare range with no path scope. `pr-describe` was checked and does **not**
   share the gap: its Step 1 honours "any explicit base/range the user gave". **Fixed 2026-08-03 as
   `chore-0024`, on a separate branch**, which names three modes in Step 1, amends the Modes and Range
   resolution rows, adds scenario S-013, and adopts the same `supplied` / `resolved` vocabulary this
   skill reports. Verified against its diff rather than its report: all five acceptance commands
   reproduce, and it made one edit beyond its brief, tightening the preconditions of S-002, S-003 and
   S-004 from "naming no scope" to "naming neither a path scope nor a range", without which S-013 and
   S-002 would both fire on a bare range with different outcomes.
   **Reconciliation note, now discharged.** This skill's Inputs section said the inconsistency "is
   filed against `house-review` and is not resolved here", which was true on this branch alone and
   false once `chore-0024` landed. It was deliberately not pre-corrected, because asserting a fix that
   lived on an unmerged branch would have been the same class of error as citing `HEAD` for a
   measurement. The two were merged on 2026-08-03 and the sentence was rewritten in the same operation,
   which is the only point at which it could be made true.
2. **`remainder_depth` degenerates above the R5 threshold.** ~~The rule re-reads the same signal table
   with the two lists emptied, so `reviewable_lines` stays at the whole-set value and any changeset
   over 600 lines gets `deep` for the remainder too.~~ **Fixed 2026-07-31 on the author's
   instruction.** Measured on `v0.1.0..5ba2311`, pinned to a commit rather than to `HEAD` because the
   first version of this line cited a moving reference and the commit recording it falsified its own
   figure the moment it landed: 1047 reviewable lines across 7 directories, 30 of them
   in the two anchors, yielded `deep` anchors and a `deep` remainder, so the anchor list said nothing.
   That is the failure the body already argues against in its own words, since a `deep` that fires on
   everything is the uniform effort setting this skill replaces. The fix is two steps, and **the
   obvious one is not the one that works**: re-measuring the remainder over its own files alone still
   selects `deep` there (1017 lines, 5 directories, both over R5's thresholds), because the anchors
   held 30 of 1047 lines. What fixes it is capping the remainder at `standard` whenever R2 fires, on
   the ground that R5 escalates on size as a proxy for unlocated risk and R2 has just located it. Both
   steps are in, since re-measuring is still what decides `quick` against `standard`. Verified: the
   `8ff7d49` run above is unchanged (397 lines, 3 directories, `standard` from either table), so the
   recorded claim it confirmed still holds.
3. **`documentation_only` does not classify a task file.** The definition splits prose that
   *describes* the system from prose the system *runs*, and a work record is neither. It did not
   matter here, because the workflow made the signal false regardless, but this repository has 70 of
   them and the next docs-only changeset will hit it. **Fixed 2026-07-31.** A work record (task file,
   backlog entry, roadmap item, after-action note) now counts as describing prose, on the ground that
   nothing executes it and nothing must conform to it. The signal table also states the three-way
   split of prose outright, since two-way was the root error: describing, executable, and *governing*
   (a contract, a schema, a conformance record), the last being a `blast_radius` named kind that R2
   reaches before R3 can call it a docs change. That third class is what makes the generous rule for
   work records safe. Verified on `960c8d4`, four task files and nothing else, 440 lines in 1
   directory: previously the signal had no defined value, so the Step 4 fallback fired and announced
   `standard` as an unmeasurable change; now R4 selects `standard` by a stated rule. Same depth,
   reached honestly, and the fallback goes back to meaning what it says instead of absorbing the
   commonest changeset shape in this repository.
4. **"a shipped template" is undefined among the `blast_radius` named kinds.**
   `.github/PULL_REQUEST_TEMPLATE.md` is a template and is shipped in the repository, yet nothing
   composes it. It was classified as not a named kind and the call recorded, which is the stated
   fallback, but the term needs one clarifying line. **Fixed 2026-07-31.** A shipped template is now
   defined as one tooling copies or instantiates elsewhere, so a defect propagates to every consumer
   and cannot be recalled; a repo-local template a service renders in place is not a named kind and
   qualifies only by the reference count. Verified in both directions: `6225b1e` touches
   `.agents/skills/init-worktracking/templates/tasks-README.md.tmpl`, which is instantiated into every
   adopter repository and now flags, and `8ff7d49`'s pull request template still does not, so the
   anchor set for the handoff run above is unchanged and the claim it confirmed still holds.
5. **The output block records changeset identity but not its provenance.** `changeset:` distinguishes
   a range from the working tree, not a range the skill resolved from one the user supplied. This run
   supplied one, and nothing in the block would show that later. **Fixed 2026-07-31.** Added
   `changeset_source: resolved | supplied`, always present, plus an explicit range to the Inputs list
   and a line in Step 5 saying that a supplied range must be handed to `house-review` rather than left
   to its Step 1, which would not arrive at it. The `house-review` half of this stays filed as item 1
   and is untouched here.

Items 2 through 5 are edits to this skill and are in scope for this task; all four are done as of
2026-07-31. Item 1 is an edit to `house-review`, is out of scope here, and is filed separately.

### Earlier runs

The six in-repository changesets and the external Python repository are recorded in the skill body as
conclusions, not as a per-changeset table: the blanket-escalation rule R2 replaced (4 of 6 changesets
tripped it), the `blast_radius` prose carve-out (`docs/CATALOG.md` at 19 referencing files sent a
four-line fix to `deep`), the exclusion class firing on a `uv.lock` (6512 lines down to 655), the
generated `schemas/*.schema.json` exclusion (938 lines), and the `git grep -l` substitution after a
recursive grep did not finish in two minutes. The per-changeset records were not kept and cannot be
reconstructed from the artifacts, so the two dogfood lines below stay unticked rather than being
ticked from the body's own summary of itself.

### Closeout note: this file's own links break when it moves

Confirmed by simulating the move, not by reasoning about it. All 5 relative links in this file resolve
from `.tasks/` and none resolves from `.tasks/done/`: the four `../` links land inside `.tasks/`
itself, and `done/chore-0010-...` becomes `done/done/chore-0010-...`. Rewrite all 5 when the file
moves, and see the major finding above for why no check would catch it.

## Definition of done

- [x] Acceptance command(s) pass locally. Run 2026-07-31; see the note on the one criterion whose
      wording needs amending rather than whose command failed.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] Dogfooded against at least two real changesets in this repository, one documentation-only and
      one large and multi-directory, with the selected depth recorded per changeset, judged right or
      wrong by hand, and the skill iterated from what the run found.
- [ ] Dogfooded against a repository that is not this one, with a real dependency tree and lockfiles,
      so the exclusion classes and the size floor fire on real material rather than staying
      theoretical. Read-only against that repository.
- [x] The `house-review` handoff run end to end at least once on an anchored changeset, producing
      real findings at both depths, with anything the handoff needed and could not get reported as a
      finding rather than patched into `house-review`. Run 2026-07-31 on `8ff7d49^..8ff7d49`; see the
      dogfood evidence above. One qualification recorded rather than glossed: the anchor leg produced
      5 findings and the `standard` remainder leg produced none, so "real findings at both depths" is
      met in the sense that both legs were worked and reported, not in the sense that both yielded
      findings. A clean remainder is a result, and manufacturing one to fill this box is the exact
      thing the lens forbids.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only
      a maintainer can find out about has not shipped for anyone else. **Run 2026-07-31, change-scoped
      to what a 20th skill could invalidate. 11 findings, `drift_found`.** Disposition, all with a
      reason: D-001, D-002, D-004, D-005 and D-006 (five grounded count and profile claims across
      `README.md`, `docs/ARCHITECTURE.md` and `docs/GETTING-STARTED.md`) are **not corrected here on
      purpose**, because they are true of the blessed set and false only because the installer places
      an unblessed draft; `feat-0036` removes the cause and makes all five true with no edit. D-009,
      the contract finding behind them, was reported against the code and never against `AGENTS.md`,
      per the classification rule. D-003, D-007 and D-008 are `suspected` count claims whose
      denominator moves only if this skill is blessed, so they belong to the blessing, not to the
      draft. D-010 and D-011 (undated present-tense rows in two conformance records) were dated on the
      author's instruction, following the `chore-0023` precedent: the dates are the real measurement
      dates recovered from history, 2026-07-28 and 2026-07-29, and no figure was re-measured or
      overwritten. Explicitly **not** a finding: S-014's `all=14273`, which the author flagged as
      stale, is dated 2026-07-29 and therefore correctly records what was measured then. `docs/CATALOG.md`
      has no `review-depth` row and `ROADMAP.md` Epic B item 10 is unstruck, both intended and both
      confirmed clean rather than assumed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
- [ ] Author sign-off on the dogfood evidence before the skill is blessed. Until then the skill stays
      a draft, the roadmap item stays unstruck, and no `docs/CATALOG.md` row claims it is shipped.
