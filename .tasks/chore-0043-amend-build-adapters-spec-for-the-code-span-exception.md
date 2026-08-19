---
id: chore-0043
title: The build-adapters contract governs link rewriting in six scenarios and none of them excepts a link that is not a link
type: chore
status: open
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

[`bug-0028`](done/bug-0028-adapter-link-rewrite-fires-inside-code-spans-and-fences.md) taught
`rewrite_links()` that a markdown link inside an inline code span or a fenced block is not a link, so
it is emitted unchanged. That is the right behaviour and it is not what the approved contract says.

[`build-adapters.md`](../docs/spec/build-adapters.md) carries six scenarios governing that function,
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
[`chore-0039`](chore-0039-amend-validate-skills-spec-for-the-code-span-exception.md), still open.
This task is its sibling, and the two should read as one decision applied twice rather than as two
independently-argued exceptions.

## Scope

**In scope:** amend the contract so it describes the function that exists, and re-audit the affected
rows. Two documents:

- `docs/spec/build-adapters.md`: state the exception. Whether that is a qualification on the existing
  scenarios or a new scenario beside them is the author's call, and `chore-0039` faces the identical
  choice on `S-009`. **Take the same shape in both**, and if `chore-0039` has already landed, follow
  what it chose rather than deciding again.
- `docs/spec/build-adapters.conformance.md`: re-audit the affected rows against the current code.

Follow the convention in [`docs/spec/README.md`](../docs/spec/README.md) for a spec amended after
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

## Implementation notes

The behaviour to describe, taken from the code rather than from this task file: a link whose `](`
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

- [ ] `docs/spec/build-adapters.md` states that a link inside an inline code span or a fenced block is
      emitted unchanged, in the same shape `chore-0039` uses for `validate-skills.md`.
- [ ] The spec keeps `status: approved` and carries a dated note naming this task id and using the
      words **pending the author's re-approval**.
- [ ] The re-approval table in `docs/spec/README.md` lists it, or the task states why it does not.
- [ ] `build-adapters.conformance.md` re-audits the affected rows against the current code and cites
      the measured reach (131 links matched, 0 newly suppressed across the twenty shipped bodies).
- [ ] No file under `scripts/` or `tests/` is modified.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
