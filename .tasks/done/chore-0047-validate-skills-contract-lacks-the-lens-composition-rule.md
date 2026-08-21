---
id: chore-0047
title: The skill linter gained a lens-composition rule and the contract it is derived from does not mention it
type: chore
status: done
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: []
spec: "docs/spec/validate-skills.md"
touched_files:
  - docs/spec/validate-skills.md
  - docs/spec/validate-skills.conformance.md
  - docs/spec/README.md
created: 2026-08-19
---

## Problem

[`feat-0048`](feat-0048-wire-the-autonomy-lens-into-the-skills.md) added a rule to
[`validate-skills.py`](../../scripts/validate-skills.py): a file under `.agents/rules/` that declares
itself a lens must be referenced by at least one skill, or the run errors. It is real, tested in both
directions, and it fires with a good message:

```text
ERROR .agents/rules/autonomy.md: declares itself a lens but no skill references it, so nothing
composes it and an adopter who rewrites it changes nothing.
```

[`validate-skills.md`](../../docs/spec/validate-skills.md) is the approved contract that script's tests
are derived from, and it says nothing about it. Counted 2026-08-19, after `chore-0039` amended that
same spec to `S-022`: zero scenarios mention a lens, an inbound reference, or `.agents/rules/`.

The gap is exactly the one this repository keeps finding and is now finding in its own newest work.
`bug-0023`, `bug-0027` and `bug-0028` each taught a tool something the contract did not say, and
`chore-0039` and `chore-0043` were the tasks that wrote those down. This is the same shape, one
iteration later: the code moved and the contract did not.

It is also structurally different from those three in a way worth stating, because it changes what
the scenario has to cover. Every rule the spec already describes is about a **skill**, and
`main()` iterated only over the skills directory, which is why an unwired lens was invisible to every
gate. `feat-0048`'s rule is the first that reads a sibling directory, so the contract needs a
scenario about a file that is not a skill at all, and the Proposed Surface needs to admit that the
tool looks outside `.agents/skills/`.

The timing is not anybody's fault. `feat-0048` and `chore-0039` ran in the same wave, in isolated
worktrees, and neither could see the other: `feat-0048`'s agent flagged the gap in its report and
correctly declined to edit a spec outside its `touched_files` that a sibling was already editing.

## Scope

**In scope:** describe the lens-composition rule in the contract and audit it.

- `docs/spec/validate-skills.md`: a new scenario for the rule, in the shape `S-022` and `S-018` use,
  since the author settled that shape on 2026-08-18 and it now has two precedents. State what counts
  as a reference, which `feat-0048` decided as the lens's filename appearing in a `SKILL.md`, by
  relative link or by prose naming the file, and deliberately not a bare subject-word mention.
- The same file's Proposed Surface, which currently describes a tool that reads skills, so that it
  admits reading `.agents/rules/` too.
- `docs/spec/validate-skills.conformance.md`: a row for the new scenario with its test evidence.
- `docs/spec/README.md`: the amendment note's row, and the recomputed counts.

Follow the amendment convention in [`docs/spec/README.md`](../../docs/spec/README.md): keep
`status: approved`, add a dated header note naming the date and this task id, and use the words
**pending the author's re-approval** verbatim, because that exact phrasing is what the re-approval
search finds and one spec is already invisible to it for using different words.

**Out of scope:**

- Any change to `scripts/validate-skills.py` or `tests/test_validate_skills.py`. `feat-0048` settled
  the behaviour and it is tested in both directions; this task only writes it down. If describing it
  makes you want to change it, that is a finding to report rather than a change to make.
- The skip condition when no sibling `rules/` directory exists. It is an implementation detail that
  keeps existing fixtures unaffected, not a behaviour an adopter can observe.
- Whether the five wired skills should now have their inline autonomy prose thinned in favour of the
  lens. `feat-0048` deliberately left that open and it is a separate decision.
- Retagging any test docstring, which is [`chore-0045`](../chore-0045-three-small-items-from-the-2026-08-19-waves.md).

## Implementation notes

Read `feat-0048`'s `## Decisions` section before writing the scenario. Two of its choices are
load-bearing for what the contract should say: what counts as a reference, and that no reference
declares the lens canonical over a skill's inline prose, because `autonomy.md`'s own Scope section
permits a local exception. A scenario that implied the opposite would contradict the module.

Recompute the counts in `docs/spec/README.md` from the files rather than incrementing them. Two
tasks collided in that paragraph on 2026-08-19 and the numbers had to be hand-merged; `chore-0039`
then recomputed them and found the merge correct. Keep that habit.

Ground the conformance row in the tests that exist, `TestLensComposition` in
`tests/test_validate_skills.py`, rather than in this description.

## Decisions

- **2026-08-20, implementation: the rule is written as `S-023`, placed last rather than beside a
  related rule.** `S-022` sits beside `S-013` because it is an exception the link rows are read
  against. This one is read against nothing above it: it is the only rule in the contract whose
  subject is not a skill, so grouping it with any existing rule would imply a relationship that does
  not exist. Both documents place it last and the conformance coverage proof says why.

- **2026-08-20, implementation: the scenario states reachability only, and explicitly says a
  reference does not make the lens canonical over a skill's inline prose.** This is `feat-0048`'s
  second load-bearing decision, and stating it in the negative was necessary rather than tidy: a
  scenario that said only "a lens must be referenced" invites the reading that the referenced module
  governs, which contradicts `autonomy.md`'s own Scope section ("A skill may state a local
  exception"). The same qualifier covers `house-style.md` and `review-quality.md`, whose Scope
  sections say the same thing.

- **2026-08-20, implementation: what counts as a reference is stated positively and negatively.**
  Positively, the lens's filename in a `SKILL.md`, by relative link or by prose naming the file,
  because `AGENTS.md`'s portability contract tells a skill to name some files in prose rather than
  link to them. Negatively, the bare subject word is not a reference. The negative half is the one
  that has to be in the contract: without it a later reader would reasonably relax the rule to a
  topic mention, which satisfies the check while leaving a reader no route to the module, and that is
  the exact failure `feat-0048` was filed for.

- **2026-08-20, implementation: the opening-window bound is described qualitatively, without the
  number.** The scenario says the declaration is read in the file's opening and not anywhere in the
  body, because which documents count as lenses is observable to an adopter. `LENS_DECLARATION_LINES
  = 10` is not in the scenario: the exact width is a tuning constant, already bounded in both
  directions by its own test, and pinning it in an approved contract would make a safe widening into
  a contract amendment.

- **2026-08-20, implementation: no new Goal was added, deliberately.** `feat-0032`, `bug-0007` and
  `bug-0008` each added one alongside their scenarios, so declining is a departure worth recording.
  The task's Scope names exactly two changes to `validate-skills.md`, the scenario and the Proposed
  Surface, and a Goal is a header-level claim about the tool's purpose that the author re-reads at
  re-approval. Flagged in the report instead, so the author can add Goal 8 in the same pass that
  grants re-approval if they want one.

- **2026-08-20, implementation: the Proposed Surface gained a "what it reads" row rather than a
  reworded Invocation row.** The surface previously described a tool with one input and no statement
  of scope, which is why reading a sibling directory could be added without contradicting it. A row
  naming both directories, and saying the rules module is read only for `S-023`, makes the next
  expansion of the read scope visible as a surface change.

- **2026-08-20, implementation: the S-023 conformance row is `Conformed`, and the code-span
  asymmetry is recorded in its note rather than as a divergence.** The substring test that decides
  "is this lens referenced" is not guarded by the code-span and fence ranges `S-022` applies to the
  link rules, so a body that only showed a lens filename inside a fence would satisfy it. The
  scenario says "appearing in a `SKILL.md`" and the code does exactly that, so calling it a
  divergence would be inventing a contract the author never wrote. Reported as a finding, and no
  file under `scripts/` or `tests/` was touched.

- **2026-08-20, implementation: the counts in `docs/spec/README.md` were recomputed, not
  incremented.** Counted `^### Scenario S-` across the eleven spec files, excluding `README.md` and
  the five sibling report kinds: 156 total (up from a verified 155 before this edit, so the previous
  figure was correct), and 143 held by the ten specs carrying a conformance matrix, with
  `systematic-debugging` the only one without. The pre-edit recount reproducing 155 and 142 is the
  part worth keeping: it is what makes the new numbers a measurement rather than an increment.

## Risks and rollback

Three documents in one directory and no code, so the more-than-one-module rule does not fire. This
section is kept only for the amendment convention, which is the real hazard: amending an approved
contract without the dated note and the re-approval row is how a spec quietly becomes something no
human agreed to.

Reversible by reverting one commit. No code depends on the wording.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] `validate-skills.md` carries a scenario for the lens-composition rule, stating what counts as a
      reference and what does not.
- [x] Its Proposed Surface admits that the tool reads `.agents/rules/` and not only `.agents/skills/`.
- [x] The spec keeps `status: approved` and carries a dated note naming this task id with the words
      **pending the author's re-approval**.
- [x] `validate-skills.conformance.md` has a row for the new scenario citing `TestLensComposition`.
- [x] `docs/spec/README.md`'s counts are recomputed from the files, and its re-approval table lists
      this amendment.
- [x] No file under `scripts/` or `tests/` is modified.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
