---
id: chore-0049
title: Nothing checks that a conformance matrix's cited evidence still exists, and two independent causes have now produced stale rows in one month
type: chore
status: open
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: [bug-0037]
touched_files:
  - scripts/run-checks.py
  - tests/test_run_checks.py
created: 2026-08-20
---

## Problem

[`bug-0037`](done/bug-0037-conformance-matrices-cite-line-numbers-that-prose-edits-invalidate.md)
deferred building a citation checker and said exactly what would justify one: if the re-derivation
turned up more stale rows than the two known ones, that count is the argument. It did.

Measured at that task's closeout, over 65 pointers rather than the 40 the task predicted:

```text
7 citations pointed at wrong content
6 of them the known AGENTS.md family, one cause (chore-0046, plus two later landings)
1 previously unknown: install.py:983-986 claimed the "if not scoped" branch
  and resolved to _check_entry()'s definition; the real content is in check()
```

**Two independent causes, in one document, in one month.** That is the difference between a single
incident someone fixes by hand and a class that recurs. The unknown one is the sharper half: nobody
was looking for it, no gate reported it, and it surfaced only because one task happened to re-read all
65 pointers.

The other half of the evidence is that the obvious guard would have missed most of it. The acceptance
grep `bug-0037` used matches only tokens carrying a filename, and 25 of the 65 pointers were bare
`:NNN` continuations sitting in the same table cells. **A grep-shaped guard would have passed with 25
fragile pointers left in place.**

Citations are now by symbol, section heading, or quoted phrase across all ten matrices, which is
strictly more durable and still unchecked: a symbol gets renamed, a heading gets reworded, a quoted
phrase gets edited, and the matrix goes on asserting it.

**This task is one of five in the same class**, grouped 2026-08-22 rather than worked as unrelated errands: a guard that does not guard. The other four are [`chore-0032`](chore-0032-links-guard-fires-per-run-not-per-pattern.md), [`chore-0058`](done/chore-0058-no-gate-link-checks-the-markdown-under-agents-outside-skills.md), [`chore-0059`](chore-0059-the-third-and-fourth-copies-of-the-link-helpers-are-unguarded.md), and [`chore-0060`](chore-0060-the-scaffold-manifest-id-high-water-is-stale-and-unguarded.md). `chore-0058` closed 2026-08-27, and `bug-0045` was the sixth and is closed: it found six of seven gates reporting `ok` over a repository containing nothing. **What the grouping asks of whoever works this one**: when you fix it, look for the next member before you finish, because every member of this class so far was found only by looking after the previous one landed. The pattern behind the class is [`chore-0063`](chore-0063-the-repository-has-never-written-down-what-it-keeps-learning.md).

## Scope

**In scope:** a check that a conformance matrix's cited evidence still resolves in the file it names.

- Decide which citation forms are checkable and check only those. A quoted phrase is a substring test
  against a named file and is decidable; a section heading is decidable; a symbol name is decidable
  for Python and probably not in general. A form that cannot be checked reliably is reported as
  unchecked rather than guessed at, following the coverage-proof habit `spec-conformance` already uses.
- Report the audited and unaudited counts, so a clean result over a subset is never mistaken for a
  clean result over the whole.

**Out of scope:**

- Re-deriving any citation. `bug-0037` did that. If the guard finds a stale row on its first run, that
  is a finding to report, not work to fold in here.
- Requiring a particular citation form in new matrices. That is a convention question and belongs with
  a human, not inside a checker.
- Line-number citations, which `bug-0037` removed and which nothing should reintroduce. If the checker
  would make them safe again, say so and leave the decision alone.

## Implementation notes

**The false-positive risk is the whole design problem and it should be weighed before any code.**
`bug-0037` named it: a checker for "does this quoted phrase still appear in that file" is a real tool
with real false-positive risk, and a check that cries wolf gets disabled within a week, which is the
same reason `check-provenance.py` is deliberately kept out of required CI. Prefer a small set of
high-confidence failures over flagging everything that might be stale.

Weigh where this belongs before writing it. It reads `docs/spec/`, not `.agents/`, so
`validate-skills.py` is a poor host even though it already stretched once to read a sibling directory
(`S-023`, and the surface entry that amendment needed). A separate script called from
`run-checks.py` is the shape `touched_files` above assumes; correct it if the work chooses otherwise,
and record why.

## Risks and rollback

More than one module, since a new script and a `run-checks.py` gate are both in play, so this section
is required. The realistic failure is a noisy checker that a later task disables, which is worse than
no checker because it looks like coverage. Bound it by reporting unchecked citations explicitly, and
by running it over the current ten matrices before wiring it into any gate: if it reports anything on
a tree `bug-0037` just cleaned, that is either a real find or a false positive, and both are worth
knowing before it becomes a gate.

An eighth gate also changes `run-checks.py`'s own summary arithmetic, which `tests/test_run_checks.py`
pins. Expect to update that pin deliberately rather than discovering it.

Reversible by reverting one commit. Nothing depends on the check existing.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] A conformance matrix citing a quoted phrase that no longer appears in the named file is
      reported, proven by a test that fails against a fixture.
- [ ] A citation whose form the checker cannot decide is reported as unchecked, not as passing.
- [ ] The run states the audited and unaudited counts, and the arithmetic rather than the claim.
- [ ] Run over the current ten matrices, the checker's output is recorded in the closeout, whether it
      is empty or not.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
