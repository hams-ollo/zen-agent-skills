---
id: chore-0054
title: The validate-skills contract does not describe the supporting-file link rule that chore-0036 shipped
type: chore
status: open
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

[`chore-0036`](done/chore-0036-link-check-skill-supporting-files.md) gave `validate-skills.py` a new rule:
it link-checks the markdown files a skill ships beside its `SKILL.md`, excludes `.tmpl` templates
because their links are written for a destination the script does not know, and prints a second
summary line reporting what it checked and what it skipped.

**None of that is in the contract.** [`validate-skills.md`](../docs/spec/validate-skills.md) describes
a validator that reads skills; it has no scenario for a supporting file, its `Output` element does not
admit a second summary line, and its `What it reads` element does not say the whole skill directory.

`chore-0036`'s agent declined to amend the spec itself, which was correct: amending an approved
contract is not a delegated agent's call. It recorded the divergence honestly instead, classifying the
`Output format` row **Diverged** in
[`validate-skills.conformance.md`](../docs/spec/validate-skills.conformance.md) and logging the owed
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
  [`docs/spec/README.md`](../docs/spec/README.md), and a row added to that file's re-approval queue.
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

- [ ] `validate-skills.md` carries a scenario for the supporting-file link rule, with an id taken from
      the spec rather than assumed, and the `.tmpl` exclusion stated as part of the contract.
- [ ] The `Output` and `What it reads` surface elements describe what the script now does.
- [ ] A dated amendment note is added, `status:` still reads `approved`, and a row is added to
      `docs/spec/README.md`'s re-approval queue.
- [ ] The matrix rows `chore-0036` left Diverged or unreconciled are reconciled, and the coverage-proof
      arithmetic is restated with the numbers rather than asserted.
- [ ] No file under `scripts/` or `tests/` is modified.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
