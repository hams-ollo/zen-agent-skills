---
id: chore-0049
title: Nothing checks that a conformance matrix's cited evidence still exists, and two independent causes have now produced stale rows in one month
type: chore
status: done
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: [bug-0037]
touched_files:
  - scripts/run-checks.py
  - tests/test_run_checks.py
  - docs/spec/cloud-executable.md
  - docs/spec/cloud-executable.conformance.md
  - docs/spec/README.md
created: 2026-08-20
---

## Problem

[`bug-0037`](bug-0037-conformance-matrices-cite-line-numbers-that-prose-edits-invalidate.md)
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

**This task is one of five in the same class**, grouped 2026-08-22 rather than worked as unrelated errands: a guard that does not guard. The other four are [`chore-0032`](chore-0032-links-guard-fires-per-run-not-per-pattern.md), [`chore-0058`](chore-0058-no-gate-link-checks-the-markdown-under-agents-outside-skills.md), [`chore-0059`](../chore-0059-the-third-and-fourth-copies-of-the-link-helpers-are-unguarded.md), and [`chore-0060`](chore-0060-the-scaffold-manifest-id-high-water-is-stale-and-unguarded.md). `chore-0058` closed 2026-08-27, and `bug-0045` was the sixth and is closed: it found six of seven gates reporting `ok` over a repository containing nothing. **What the grouping asks of whoever works this one**: when you fix it, look for the next member before you finish, because every member of this class so far was found only by looking after the previous one landed. The pattern behind the class is [`chore-0063`](chore-0063-the-repository-has-never-written-down-what-it-keeps-learning.md).

## Scope

**In scope:** a check that a conformance matrix's cited evidence still resolves in the file it names.

- Decide which citation forms are checkable and check only those. A quoted phrase is a substring test
  against a named file and is decidable; a section heading is decidable; a symbol name is decidable
  for Python and probably not in general. A form that cannot be checked reliably is reported as
  unchecked rather than guessed at, following the coverage-proof habit `spec-conformance` already uses.
- Report the audited and unaudited counts, so a clean result over a subset is never mistaken for a
  clean result over the whole.

- **Added 2026-08-28 at dispatch, after a first run stopped here.** An eighth gate diverges from an
  approved contract, which this task did not say. The `Gate set` Proposed Surface element in
  [`cloud-executable.md`](../../docs/spec/cloud-executable.md) reads "The seven currently in
  `checks.yml`" and then enumerates them by name, and
  [`cloud-executable.conformance.md`](../../docs/spec/cloud-executable.conformance.md) records it
  `Conformed` against `test_the_seven_gates_are_present_ordered_and_complete`. Adding a gate without
  touching either would ship a divergence and call it a feature.
  **The author's decision, taken 2026-08-28: amend the element to state the property rather than the
  count.** Name what the set is, every gate that decides whether a change here is acceptable, as
  enumerated by `gates()`, rather than how many there are. A count-shaped claim in a contract goes
  stale the first time anyone adds a gate, which is the class this repository keeps filing tasks
  about. Add the dated amendment note, leave `status:` reading `approved` per the convention in
  [`docs/spec/README.md`](../../docs/spec/README.md), extend that file's existing `cloud-executable`
  re-approval row rather than adding a second, and reconcile the matrix row you touch. Per
  `.agents/rules/house-style.md`, introduce no count of any table's rows.
  This also governs [`chore-0072`](chore-0072-a-gate-for-the-roadmap-staleness-class-chore-0066-mapped.md),
  which adds a gate too and inherits the amendment rather than repeating it.

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

## Decisions

**Which citation forms are checkable, and what happens to the rest.** Three are decided: a **test
name** (`test_*`, read from the whole row, checked against a `def` under `tests/`, and needing no
file attribution because a test name is a Python function name), a **symbol** (`name(...)` or
`UPPER_SNAKE`, word-boundary presence in a file the row names), and a **quoted phrase** (a
multi-token span, normalised substring of a file the row names). Everything else is reported
`unchecked` with its reason and counted separately: single words, flags, task and scenario ids, bare
filenames, and section headings named in running prose rather than in backticks. Measured over the
ten current matrices: 396 audited, 186 unaudited, 582 extracted.

**A signposted elision is unchecked, never unresolved (the elision rule).** A phrase carrying `...`
or an angle-bracket placeholder like `<name>` is one where the author said they were standing in for
text rather than quoting it, so it is a substring of nothing and a substring test cannot decide it.
Confirmed 2026-08-28 that three rows in `build-adapters.conformance.md` are written this way and all
three are correct: `SHARED/skills/<name>/<target>` (S-007), `any(start <= m.start() < end ...)`
(S-018), and `for fname, obj in ...` (S-015). They land in three different buckets rather than one,
which is worth knowing before anyone "simplifies" the classifier: the first is a single token and
never reaches the phrase rule, the second is a call form and is checked as the symbol `any` before
being dismissed as a builtin, and only the third reaches the elision rule itself.

**Rejected: attributing a citation to a subject by position.** The first working version took the
most recent `` `file` / `` marker in a cell as the subject of every span after it. Measured against
the real corpus, it produced false positives and no true findings, because a cell may name two files
and switch between them in prose: the S-005 row of `tracker-links.conformance.md` cites
`pr-describe`'s clause and then `EXTERNAL_RE`, which lives in `.tasks/validate.py`. Every file a row
names is now a candidate and a citation resolves if it resolves in any of them. This is strictly
more conservative, and the failure being hunted, a renamed symbol or an edited phrase, removes the
text from every candidate at once.

**Rejected: reporting every phrase that fails a literal substring test.** Twelve did on the first
pass, and reading the source for each one showed **all twelve were correct citations**: a citation
collapses onto one line what the source wraps over several, an intervening comment sits inside a
construct, a signature is written in shorthand, quoting differs between JSON and prose. Three
normalisations were added for the cases verified by hand (whitespace collapsed, full-line comments
removed, quote characters removed), each a widening that can only turn a report into silence. A
checker whose first run cries wolf twelve times gets switched off inside a week, and a switched-off
gate is worse than no gate because it still looks like coverage.

**A builtin is unchecked, because the test could not fail.** `sum()` appears in
`build-adapters.conformance.md` as prose about a builtin call rather than as a citation of a
definition, and asserting that `sum` occurs in a Python file has no failing case. A check that
cannot fail is unchecked whatever it printed, per the conventions section of `AGENTS.md`.

**Rejected: relabelling the coverage-proof breakdown instead of filtering it.** As first
delivered the audited line printed `quoted phrase 110, symbol 235, test name 56` beneath a stated
total of 396, and those sum to 401: the breakdown counted every citation of each form, including the
five that have a decidable form and were deliberately not audited (two signposted elisions, three
builtin names). Caught in verification, not by this task. The defensible alternative was to relabel
the line as a tally of *extracted* forms, which would also have closed the arithmetic. It was
rejected because it closes the sum by removing the claim: the audited total would then have no
breakdown at all, and being able to see what was audited is the whole point of a coverage proof. The
breakdown is filtered to the audited half instead, and both halves now come from a single partition
of the citation list, so each citation contributes exactly one entry to exactly one breakdown and
both sums hold by construction rather than at a call site. The unaudited breakdown had summed
correctly by luck under the old shape and now does so for the same structural reason.

**Seam left open: line-number citations stay unsafe, deliberately.** This checker decides symbols,
test names, and quoted phrases, none of which is a line anchor, so nothing here makes the form
`bug-0037` removed safe to reintroduce. `test_the_line_number_citation_form_is_still_absent` pins
their continued absence rather than their validity.

**Seam left open: the unaudited 186.** The largest bucket is spans this checker declines to treat as
citations at all. Narrowing it is a convention question about how matrices should cite, which the
scope of this task puts with a human rather than inside a checker, so the number is reported on every
run instead of being quietly reduced.

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

- [x] A conformance matrix citing a quoted phrase that no longer appears in the named file is
      reported, proven by a test that fails against a fixture.
- [x] A citation whose form the checker cannot decide is reported as unchecked, not as passing.
- [x] The run states the audited and unaudited counts, and the arithmetic rather than the claim.
- [x] Run over the current ten matrices, the checker's output is recorded in the closeout, whether it
      is empty or not.
- [x] The `Gate set` surface element states the property rather than a count, carries a dated
      amendment note, leaves `status:` reading `approved`, and its matrix row is reconciled.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
