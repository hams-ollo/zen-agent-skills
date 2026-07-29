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

- [ ] `.agents/skills/review-depth/SKILL.md` exists, with `name: review-depth`, a `description` that
      says both what it does and when to use it, and `license: MIT`.
- [ ] `python scripts/validate-skills.py` exits 0 with no new warnings and no new errors.
- [ ] `python .tasks/validate.py --strict` exits 0.
- [ ] `python -m unittest discover -s tests -p "test_*.py"` exits 0, unaffected by this change.
- [ ] `python scripts/build-adapters.py --dry-run` and
      `python scripts/install.py --dry-run --home ./.tmp/zen-home` both exit 0 and include the new
      skill.
- [ ] The body names exactly three depths (`quick`, `standard`, `deep`) and states one ordered
      selection rule whose branches are mutually exclusive, so one signal table yields one primary
      depth. Amended after the dogfood: when the risk rule fires it also yields a remainder depth for
      the unflagged files, derived from the same table by the same ordered rule, so the pair is as
      reproducible as a single value.
- [ ] Every threshold in the selection rule is a stated number, not an adjective.
- [ ] The body states that an explicit user choice overrides detection, and that the detected depth
      is still reported when it is overridden. Amended after the override run: when detection would
      have escalated, the files it would have escalated on are reported too, since a dropped anchor
      list is the one way an honoured override still misleads.
- [ ] The output block carries the changeset identity, so the depth and the review it governs
      provably describe the same range rather than two independently resolved ones.
- [ ] The body contains no copy of the rubric category list and no copy of the severity definitions;
      both are reached by relative link to `review-quality.md`.
- [ ] `.agents/skills/house-review/SKILL.md` and both files in `.agents/rules/` are byte-identical to
      their state before this task (`git diff --stat` shows neither).
- [ ] Every relative markdown link added resolves to a file that exists, both on disk and under the
      shipped layout (no link escapes the `.agents/` tree).
- [ ] No em-dashes; headings sentence case.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] Dogfooded against at least two real changesets in this repository, one documentation-only and
      one large and multi-directory, with the selected depth recorded per changeset, judged right or
      wrong by hand, and the skill iterated from what the run found.
- [ ] Dogfooded against a repository that is not this one, with a real dependency tree and lockfiles,
      so the exclusion classes and the size floor fire on real material rather than staying
      theoretical. Read-only against that repository.
- [ ] The `house-review` handoff run end to end at least once on an anchored changeset, producing
      real findings at both depths, with anything the handoff needed and could not get reported as a
      finding rather than patched into `house-review`.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only
      a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
- [ ] Author sign-off on the dogfood evidence before the skill is blessed. Until then the skill stays
      a draft, the roadmap item stays unstruck, and no `docs/CATALOG.md` row claims it is shipped.
