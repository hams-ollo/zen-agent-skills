---
id: chore-0054
title: The validate-skills contract does not describe the supporting-file link rule that chore-0036 shipped
type: chore
status: done
priority: P2
parent: "ROADMAP Kit mechanics hardening (2026-07-27 review pass)"
depends_on: [chore-0036]
spec: "docs/spec/validate-skills.md"
scenarios: []
touched_files:
  - docs/spec/validate-skills.md
  - docs/spec/validate-skills.conformance.md
  - docs/spec/README.md
created: 2026-08-21
---

## Problem

[`chore-0036`](chore-0036-link-check-skill-supporting-files.md) gave `validate-skills.py` a new rule:
it link-checks the markdown files a skill ships beside its `SKILL.md`, excludes `.tmpl` templates
because their links are written for a destination the script does not know, and prints a second
summary line reporting what it checked and what it skipped.

**None of that is in the contract.** [`validate-skills.md`](../../docs/spec/validate-skills.md) describes
a validator that reads skills; it has no scenario for a supporting file, its `Output` element does not
admit a second summary line, and its `What it reads` element does not say the whole skill directory.

`chore-0036`'s agent declined to amend the spec itself, which was correct: amending an approved
contract is not a delegated agent's call. It recorded the divergence honestly instead, classifying the
`Output format` row **Diverged** in
[`validate-skills.conformance.md`](../../docs/spec/validate-skills.conformance.md) and logging the owed
amendment as unreconciled. This task is that amendment.

This is the same position `S-022` and `S-023` were in before `chore-0039` and `chore-0047` wrote them:
behaviour shipped, contract silent, matrix carrying the gap. Both of those were closed by writing the
scenario rather than by reverting the behaviour, and the behaviour here is wanted.

## Scope

**In scope:** describe the shipped rule in the contract, and reconcile the matrix rows it leaves open.

- A scenario for the supporting-file link rule, taking the next free `S-NNN` id read from the spec
  rather than assumed.
- The `Output` element widened to admit the coverage line.
- The `What it reads` element widened to say the skill directory rather than only `SKILL.md`.
- **The exclusion is contract-level, not an implementation detail.** A `.tmpl` file is skipped because
  its links resolve at a destination this script cannot know, and that limit is the reason the rule is
  trustworthy. State it in the scenario, not only in the code.
- The dated amendment note, `status:` left reading `approved` per the convention in
  [`docs/spec/README.md`](../../docs/spec/README.md), and a row added to that file's re-approval queue.
- Flip the matrix rows the amendment closes, and update the coverage-proof arithmetic to match.

**Out of scope:**

- `scripts/validate-skills.py` and `tests/test_validate_skills.py`. The implementation is `chore-0036`'s
  and is not reopened here. If writing the scenario reveals the behaviour is wrong, that is a finding
  to report, not a code change to make.
- Widening the rule to `templates/`, which `chore-0036` scoped out deliberately and argued for at
  length. Its `## Decisions` records why, including that `references/` does not exist anywhere in this
  kit so the task's own recommended default would have shipped a check reading zero files forever.
- The CI `--links` globs, out of scope in `chore-0036` for the same reason: the two rules differ and
  the skill tree's is the portability one `validate-skills.py` owns.
- Granting the re-approval. That is the author's, by editing the note.

## Implementation notes

Read `chore-0036`'s `## Decisions` before writing the scenario. The suffix rule, the disabled
sibling-skill shortcut, and the `__pycache__` exclusion each have a recorded reason, and a scenario
written without them will describe a simpler validator than the one that shipped.

The honest bound is what the scenario must capture. Coverage today is **1 of 14** supporting files:
eight `.tmpl` templates and five non-markdown files are excluded by stated rules, leaving
`project-bootstrap/templates/house-code-style.md`. A scenario that implies broad coverage would be
wrong. `chore-0036`'s own framing is the one to keep: a stated limit is worth more than coverage
nobody can trust.

Do not restate the numbers as a contract clause. Counts drift, and this repository has now twice
shipped a prose count that disagreed with the file it described (`ROADMAP.md` on `autonomy.md`'s rule
count, and this task's own predecessor claiming ten templates out of nine). Describe the rule; let the
matrix carry the measurement.

## Decisions

**Rejected: adding a Goal or a Non-Goal for the new rule.** Goal 4 already reads "a skill's
cross-references", not a `SKILL.md`'s, and the constraint that a skill is distributed as a directory
already carries why a file beside the body is in scope. A new goal restating either would be a second
place for the same claim to drift from. The `.tmpl` exclusion is stated inside S-024, where this task
asked for it, rather than as a Non-Goal: a Non-Goal says what the tool declines to attempt, and this
is a rule about which files the tool reads, which is behaviour and belongs in a scenario.

**Rejected: writing the 1-of-14 coverage figure into the contract.** S-024 states that the run reports
both what it read and what it declined to read, and says explicitly that no coverage figure is a
clause of the contract. The measurement sits in the conformance matrix beside the date it was taken,
which is where a number that moves with the tree belongs.

**Seam left open: the two suffix tests in `classify_supporting_file` differ in case sensitivity.**
`.tmpl` is matched exactly and the markdown suffixes case-insensitively, so a file named `X.md.TMPL`
lands in the non-markdown count rather than the template count. It is still not read, which is all
S-024 asserts, so this moves a file between the two *skipped* counts and never into the checked one.
Recorded in the S-024 matrix row as a bound rather than fixed, because `scripts/` is out of scope
here.

**Seam left open: `TestSupportingFileLinkChecks` is not retagged with `S-024`.** All thirteen tests
still carry `chore-0036`'s characterization tag, so they now name less than they cover, the same
position S-022's and nine of S-023's tests are in. Retagging all three sets is one follow-up of
`chore-0045`'s shape and is not done here, because this task changes no file under `tests/`.

**Premise that turned out partly false: the dispatch note's "adding `validate-skills`" to the
re-approval queue.** It already had a row, from `chore-0039` and `chore-0047`, so the row was extended
rather than added and the count of approved-and-amended specs stays at seven. What did change is the
"three of them carry two" sentence, since `validate-skills` now carries three, and the date. The
`## The specs` table and its totals also needed updating and are not named in `## Scope`: the scenario
column read 23, and the paragraph below it read 156 scenarios with 143 in matrices. Recomputed from
the files rather than incremented: the eleven per-spec counts sum to 157, and `systematic-debugging`'s
13 are the ones no matrix holds, so 157 - 13 = 144.

## Risks and rollback

A contract plus two sibling documents, so this section is required.

The risk is describing the implementation rather than the behaviour. A scenario that names
`classify_supporting_file` or the `.tmpl` suffix as mechanism rather than as observable outcome pins
the contract to one implementation and makes the next refactor an amendment. Write what a reader can
observe from the validator's output.

Reversible by reverting one commit. `status: approved` is left as the convention requires, so no
verification run is made unanswerable by the change.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] `validate-skills.md` carries a scenario for the supporting-file link rule, with an id taken from
      the spec rather than assumed, and the `.tmpl` exclusion stated as part of the contract.
- [x] The `Output` and `What it reads` surface elements describe what the script now does.
- [x] A dated amendment note is added, `status:` still reads `approved`, and a row is added to
      `docs/spec/README.md`'s re-approval queue.
- [x] The matrix rows `chore-0036` left Diverged or unreconciled are reconciled, and the coverage-proof
      arithmetic is restated with the numbers rather than asserted.
- [x] No file under `scripts/` or `tests/` is modified.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
