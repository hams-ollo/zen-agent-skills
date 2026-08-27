---
id: chore-0065
title: Amend the validate-skills contract for the non-skill .agents markdown link rule, which no scenario describes
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [chore-0058]
spec: "docs/spec/validate-skills.md"
scenarios: []
touched_files:
  - docs/spec/validate-skills.md
  - docs/spec/validate-skills.conformance.md
  - docs/spec/README.md
created: 2026-08-27
---

## Problem

[`chore-0058`](done/chore-0058-no-gate-link-checks-the-markdown-under-agents-outside-skills.md)
extended [`validate-skills.py`](../scripts/validate-skills.py) to link-check the markdown that ships
under `.agents/` outside every skill directory: the rules module and the hooks README. **No scenario
in [`docs/spec/validate-skills.md`](../docs/spec/validate-skills.md) describes that rule**, and that
task deliberately declared no `spec` and left the amendment to be filed at closeout, in the shape of
[`chore-0054`](done/chore-0054-amend-validate-skills-spec-for-the-supporting-file-rule.md). This is
that amendment.

Two things the contract now fails to describe:

- **The rule itself.** The link rules reach outside `.agents/skills/` for the second time. `S-024`
  covers a markdown file shipped *beside a `SKILL.md`*; nothing covers one shipped beside the skills
  *tree*, which is a different geometry with a different escape ceiling.
- **The `Output` surface element, which is now stale.** It reads "then a second line reporting how
  many supporting files were link-checked and how many were skipped, by reason (S-024)". That second
  line now also carries the non-skill `.agents/` counts, and it has three renderings rather than one:
  the counts, a words-only sentence when nothing ships there, and a words-only sentence when the walk
  declined because the tree is not a shipped layout.

The third rendering is the part most worth pinning, because it exists for a reason a later reader will
not infer: `main()` is callable against any directory of skill folders, so an unconditional walk of the
parent would read unrelated markdown off the machine. `chore-0058`'s `## Decisions` records the
measurement, 20,203 entries under the system temp directory on the machine it ran on.

## Scope

**In scope:** state the rule and correct the surface.

- A scenario for the non-skill `.agents/` markdown rule, taking the next free `S-NNN` **read from the
  spec rather than assumed**. As of 2026-08-27 the spec carries `S-001` through `S-024` contiguous,
  which makes `S-025` the next free one, but re-derive that rather than trusting this sentence.
- Cover the escape half explicitly, not just the resolves half. A link reaching above the `.agents/`
  tree resolves in this repository and dangles in every installed tree, and reporting it merely as
  broken would lose the distinction the implementation makes.
- The `Output` surface element corrected for the widened second line and its three renderings. **State
  the property, not the rendering strings**: that a run which declined to look, a run which looked and
  found nothing, and a run which checked zero files must be distinguishable from one another.
- The dated amendment note, `status:` left reading `approved` per the convention in
  [`docs/spec/README.md`](../docs/spec/README.md), and the re-approval queue updated. That file already
  carries a `validate-skills` row; extend it rather than adding a second, and per
  `.agents/rules/house-style.md` do not introduce a count of the table's rows anywhere in the document.
- Reconcile the matrix rows the amendment touches and restate the coverage-proof arithmetic with the
  numbers rather than asserting it.

- **Two present-tense claims that [`chore-0064`](done/chore-0064-the-lint-skills-coverage-line-reports-the-wrong-count.md)
  falsified on 2026-08-27, added to this task's scope at that wave's reconciliation.** That change
  replaced the second summary line's `beside them` with the skill count, so two sentences written
  about the old wording are now false and no gate reports it:
  [`validate-skills.conformance.md`](../docs/spec/validate-skills.conformance.md), the `Output format`
  Proposed Surface row, which says the element "now admits the second line" and then quotes the old
  text as "printed on every run that reaches the summary"; and
  [`cloud-executable.conformance.md`](../docs/spec/cloud-executable.conformance.md), the observation
  recording what a passing gate's line carries, whose closing sentence says the line "does not move
  with the gate's own scope", which is exactly what `chore-0064` changed.
  **Re-audit those rows rather than find-and-replacing the quote**, for the reason `chore-0062`
  declined the same move: repairing a citation without re-auditing the row asserts a freshness the
  repair did not establish.
  **Two neighbouring quotes of the same string are dated measurements and must not be touched**: the
  `chore-0055` reach measurement in the same matrix, and the first half of the `cloud-executable`
  observation. Both say what was measured on a stated date and are accurate records of that moment.
  Rewriting either would falsify a record rather than refresh a citation.

**Out of scope:**

- **`scripts/validate-skills.py` and `tests/test_validate_skills.py`.** The implementation is
  `chore-0058`'s and is not reopened. If writing the scenario reveals the behaviour is wrong, that is a
  finding to report, not a code change to make.
- The line-ordering question and the coverage line's contents, which are
  [`chore-0064`](done/chore-0064-the-lint-skills-coverage-line-reports-the-wrong-count.md). That task may
  need this contract changed; if so it says so and stops, and the change lands here. **Do not amend the
  `Output` element's ordering clause on its behalf**, because that is a decision its work has not made
  yet.
- Granting the re-approval, which is the author's.

## Implementation notes

Mirror `chore-0054`, which did this one level down for the supporting-file rule and is the closest
prior art in shape and size.

`chore-0058`'s agent recommended the amendment also cover the `.agents/hooks/` half rather than only
the rules module, and the recommendation is worth taking: the rule reaches two distinct sibling trees,
and a scenario naming only `rules/` would be narrower than the code. Confirm that against the
implementation rather than inheriting it from this sentence.

## Risks and rollback

A contract plus two sibling documents, so this section is required.

The risk is writing the implementation into the contract. The walk's guard, that the skills directory
must carry `SKILLS_DIR.name`, is a mechanism chosen to bound a real hazard, and it will change if the
walk root ever becomes an explicit parameter. Fix the observable property instead: that the run says
which of the three things happened.

Reversible by reverting one commit. `status: approved` is left as the convention requires, so no
verification run is made unanswerable by the change.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] The spec carries a scenario for the non-skill `.agents/` markdown link rule, with an id taken
      from the spec rather than assumed, covering both the resolves half and the escape half.
- [ ] The `Output` surface element describes the widened second line and the three distinguishable
      outcomes, without naming the rendering strings verbatim.
- [ ] A dated amendment note is added, `status:` still reads `approved`, and the re-approval queue
      reflects it without introducing a count of the table's rows.
- [ ] The matrix is reconciled and its coverage-proof arithmetic is restated with the numbers.
- [ ] No file under `scripts/` or `tests/` is modified.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
