---
id: chore-0043
title: The build-adapters contract governs link rewriting in six scenarios and none of them excepts a link that is not a link
type: chore
status: done
priority: P2
parent: "ROADMAP Kit coherence hardening (2026-08-18 review pass)"
depends_on: []
spec: "docs/spec/build-adapters.md"
scenarios: ["S-003", "S-004", "S-005", "S-006", "S-007", "S-008"]
touched_files:
  - docs/spec/build-adapters.md
  - docs/spec/build-adapters.conformance.md
created: 2026-08-18
---

## Problem

[`bug-0028`](bug-0028-adapter-link-rewrite-fires-inside-code-spans-and-fences.md) taught
`rewrite_links()` that a markdown link inside an inline code span or a fenced block is not a link, so
it is emitted unchanged. That is the right behaviour and it is not what the approved contract says.

[`build-adapters.md`](../../docs/spec/build-adapters.md) carries six scenarios governing that function,
`S-003` through `S-008`, and none of them mentions a code span or a fence. Counted 2026-08-18:

```text
grep -c -i "code span\|fence" docs/spec/build-adapters.md   ->  0
```

`S-008` is the closest, saying external and same-page links are emitted unchanged, and it is about
link *kind* rather than about whether the text is a link at all. So the code and its tests now hold a
rule the contract does not state, which is the same gap `spec-conformance` exists to catch and which
nothing will catch here, because a matrix audits the scenarios that exist.

This is the third instance of one defect class and the second of this exact amendment. `bug-0023`
fixed it in `.tasks/validate.py`, `bug-0027` in `scripts/validate-skills.py`, and `bug-0028` in
`scripts/build-adapters.py`. The contract half of the second was filed as
[`chore-0039`](../chore-0039-amend-validate-skills-spec-for-the-code-span-exception.md), still open.
This task is its sibling, and the two should read as one decision applied twice rather than as two
independently-argued exceptions.

## Scope

**In scope:** amend the contract so it describes the function that exists, and re-audit the affected
rows. Two documents:

- `docs/spec/build-adapters.md`: state the exception as a **new scenario**, settled by the author on
  2026-08-18; see the decisions section. `chore-0039` carries the identical decision for `S-009`, so
  the two are one decision applied twice.
- `docs/spec/build-adapters.conformance.md`: re-audit the affected rows against the current code.

Follow the convention in [`docs/spec/README.md`](../../docs/spec/README.md) for a spec amended after
approval: keep `status: approved`, add a dated header note naming the date, this task id, and what
changed, and say **pending the author's re-approval** in those words so the queue stays findable.
Add the row to that file's re-approval table.

**Out of scope:**

- Any change to `scripts/build-adapters.py` or its tests. `bug-0028` settled the behaviour and this
  task only writes it down. If the amendment makes you want to change the code, that is a finding to
  report, not a change to make.
- `chore-0039` itself, which owns the same amendment for `validate-skills.md` and is independently
  dispatchable.
- The three copies of the range-finding helpers now living in `build-adapters.py`,
  `validate-skills.py` and `.tasks/validate.py`. `bug-0028` verified they are character-identical and
  recorded the duplication as a deliberate seam; deduplicating them is a separate decision with a
  portability cost, since the tracker validator ships standalone into an adopter's repository.

## Decisions

- **2026-08-18, author: the amendment takes the shape of a new scenario, not a qualification on an
  existing one.** Applies to both this task and its sibling, so the two read as one decision applied
  twice. A new `S-NNN` stating that a link inside an inline code span or a fenced block is emitted
  unchanged is traceable, is citable by a test, and gives `spec-conformance` a row of its own to
  audit. A qualification folded into an existing scenario would leave the exception with no id, so
  nothing could cite it and no matrix could report on it separately. The cost accepted is one more
  scenario per spec to maintain.

- **2026-08-19, agent: the new scenario is numbered `S-018` and placed beside `S-008`, not appended.**
  The id follows the highest existing one so nothing renumbers and every existing citation still
  resolves. The *position* follows the topic instead, immediately after the six rewrite scenarios it
  excepts, because a reader meets S-003 through S-008 and needs the exception in the same breath.
  That splits id order from document order, which this spec already does: `chore-0015` placed `S-014`
  between `S-010` and `S-011` for the same reason. The alternative, appending after `S-017`, would put
  the exception four scenarios below the rules it governs, where the rules read as unqualified.
  `bug-0028`'s tests already anticipate this id: their docstring names an `S-018` "in that shape" as
  the author's call, so this is the id they were written against.

- **2026-08-19, agent: the rule is stated as an exception with precedence, not as a seventh link
  kind.** S-003 through S-008 classify a link by kind, and S-018 answers a prior question, whether the
  text is a link at all. Writing it as another kind would make it ambiguous which fires for a fenced
  external link. So the scenario says it takes precedence over all six, which is also the order the
  code evaluates in.

- **2026-08-19, agent: the negative half of the rule is in the scenario body rather than left to the
  tests.** An unterminated fence yielding no range is what stops the rule from silently disabling the
  rewrite for the rest of a body, and it is the single most valuable thing a future editor can know
  before "improving" the detector. It is pinned by a test, but a test is not the contract. The same
  is true of the point that a link whose *text* is a code span is still rewritten, which is how nearly
  every link in this kit is written and therefore the failure mode with the widest blast radius.

- **2026-08-19, agent: the measured reach is recorded as two numbers, not one.** The task cites
  `bug-0028`'s measurement of 131 links matched and 0 newly suppressed. Re-measured against this
  commit, the twenty shipped bodies now yield **133** matched and **0** inside a code span or fence.
  The first number moved because bodies gained links since `bug-0028` ran (`feat-0048` wired the
  autonomy lens in), so it is a dated observation rather than a stable fact. Both are in the matrix
  with their dates: quoting only the older one would have made a re-derivable measurement look wrong
  to the next reader who ran it. The zero is the load-bearing half, and it says the exception fires on
  nothing in this kit today, so it is a guard against a future body rather than a live rewrite.

- **2026-08-19, agent: the counts in `docs/spec/README.md` are corrected along with the table row.**
  Adding a scenario makes that file's `build-adapters` row say 17, its total say 153, and its
  matrix-coverage sentence say 121, all of which the amendment falsifies. The re-approval row is the
  only edit the acceptance criteria name, but leaving three arithmetic statements wrong in the file
  being edited for correctness is not a smaller change, it is a worse one. The re-approval entry is
  folded into the existing `build-adapters` row as a second amendment rather than added as a new row,
  which is the shape `install` already uses for its two.

- **2026-08-19, agent: `bug-0028`'s tests are reported as stale-tagged, not retagged.** Now that
  `S-018` exists the tests could cite it directly, and their own docstring says so. Touching anything
  under `tests/` is out of scope for this task, so the conformance matrix records the mismatch instead
  and it is carried as a finding.

## Implementation notes

The behaviour to describe, taken from the code rather than from this task file: a link whose `](../`
falls inside an inline code span (any backtick run) or inside a fenced block is emitted byte for
byte, in every target. An unterminated fence yields no range, so it suppresses nothing after it,
which matches `bug-0015`, `bug-0017`, `bug-0023` and `bug-0027` and is pinned by a test.

Ground the amendment in observation rather than in this description: `bug-0028` measured the fix
against all twenty shipped `SKILL.md` bodies and found 131 links matched and 0 newly suppressed, so
every generated adapter is byte-identical before and after. That number belongs in the conformance
re-audit, because it is what makes the rule's current reach checkable rather than asserted.

## Risks and rollback

Touches two documents in one directory and no code, so the more-than-one-module rule does not fire
and this section is kept only for the amendment convention, which is the real hazard here. Amending
an approved contract without the dated note and the re-approval table row is how a spec quietly
becomes something no human agreed to; `docs/spec/README.md` records that a note phrased in different
words is already invisible to the search that finds the others.

Reversible by reverting one commit. No code depends on the wording.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] `docs/spec/build-adapters.md` states that a link inside an inline code span or a fenced block is
      emitted unchanged, in the same shape `chore-0039` uses for `validate-skills.md`.
- [x] The spec keeps `status: approved` and carries a dated note naming this task id and using the
      words **pending the author's re-approval**.
- [x] The re-approval table in `docs/spec/README.md` lists it, or the task states why it does not.
- [x] `build-adapters.conformance.md` re-audits the affected rows against the current code and cites
      the measured reach (131 links matched, 0 newly suppressed across the twenty shipped bodies).
- [x] No file under `scripts/` or `tests/` is modified.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
