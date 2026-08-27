---
id: chore-0045
title: Three one-line corrections the 2026-08-19 waves surfaced, bundled because none carries a design question
type: chore
status: done
priority: P2
parent: "ROADMAP Kit coherence hardening (2026-08-18 review pass)"
depends_on: [bug-0036]
touched_files:
  - tests/test_build_adapters.py
  - tests/test_validate_skills.py
  - docs/spec/README.md
  - docs/spec/build-adapters.conformance.md
  - docs/spec/validate-skills.conformance.md
  - .agents/skills/init-worktracking/templates/tasks-README.md.tmpl
created: 2026-08-19
---

## Problem

Three items surfaced by delegate agents during the two 2026-08-19 waves, each a line or two with no
interesting decision behind it. Bundled deliberately, following the precedent `chore-0038` set and
`chore-0040` reused: authoring and verifying three task files would cost more than the work. The
bundling is the exception rather than the pattern, and the reason is written here so a later reader
does not take it as licence.

**1. Two test docstrings say a decision is unmade that has since been made.**
`TestRewriteLinksInsideCodeSpansAndFences` in [`test_build_adapters.py`](../../tests/test_build_adapters.py)
is headed "Scenarios S-003 through S-008 refined" and says at line 106 that an "`S-018` in that shape
is the author's call, recorded in `bug-0028`'s decisions". The author made that call on 2026-08-18 and
`chore-0043` added `S-018` to the contract on 2026-08-19, so the tests can now cite the scenario they
protect instead of describing a pending question. This matters slightly more than a stale comment:
`spec-conformance` reads test tags as evidence, and a test tagged to a refinement rather than to an id
is harder to map to the row it supports.

**2. `docs/spec/README.md` says four where its own table says five.**
The marker-key section reads "Four do, listed below", and the re-approval table below it grew past
that number some time ago and grew again on 2026-08-19 when `chore-0039` added its row. Count the
rows rather than taking any number from this file, which was already wrong once: it said five while
this task sat open, and `chore-0039` landed a sixth. `chore-0043` updated the neighbouring line to
"As of 2026-08-19", so the document now contradicts itself two lines apart. The count is
the argument for eventually replacing that table with a frontmatter key, which is the one place a
wrong number actively undercuts the point being made.

**3. The scaffolded tracker README omits `title` from its field reference.**
`tasks-README.md.tmpl`'s field table documents every frontmatter field except `title`, which
`_TEMPLATE.md.tmpl` carries and which `validate.py` does not require. Noticed by `bug-0029`'s agent,
which correctly left it alone as out of its scope. An adopter reading the field reference to learn
the schema is told about eight fields and handed a template with nine.

## Scope

**In scope:** the three corrections above.

- Item 1: retag the class and its cases to `S-018`, and delete the sentence describing the decision
  as pending.
- Item 2: correct the count to match the table, and check it rather than incrementing it.
- Item 3: add a `title` row to the field table, matching the surrounding rows' style.
- Item 4, added 2026-08-19 once its blocker cleared: retag `bug-0027`'s docstrings in
  `tests/test_validate_skills.py` to `S-022`, the same correction item 1 makes for `S-018`.

- **Item 5, added 2026-08-27 at dispatch: reconcile the two conformance matrix rows this task's own
  retag falsifies.** Both matrices anticipate this task and one names it. The `S-018` test-coverage row
  in [`build-adapters.conformance.md`](../../docs/spec/build-adapters.conformance.md) says the tests are
  "tagged with the scenarios they refine" and that "their docstring says an `S-018` is the author's
  call". The `S-022` row in
  [`validate-skills.conformance.md`](../../docs/spec/validate-skills.conformance.md) quotes the tag
  `Scenario S-009 refined` verbatim, says the docstrings "describe the amendment as the author's open
  call", and closes "retagging them is `chore-0045`'s follow-up and deliberately not done here".
  Items 1 and 4 make all of that false. Landing the retag without the rows leaves two matrices
  asserting a state the same commit removed, and a quoted phrase that resolves nowhere.
  **Re-audit each row rather than find-and-replacing its quote**, per the disposition `chore-0062` and
  `chore-0068` both recorded: repairing a citation without re-deriving the verdict asserts a freshness
  the repair did not establish. Record the re-audit in each matrix and in `re_audited`, crediting only
  this pass.

**Out of scope:**

- Nothing about `bug-0027`'s tests any more. They were held out while the id they needed did not
  exist; [`chore-0039`](chore-0039-amend-validate-skills-spec-for-the-code-span-exception.md)
  landed it as `S-022` on 2026-08-19, so retagging them is now item 4 below rather than a deferral.
- The marker-key decision itself. Item 2 corrects a number inside an argument; whether that argument
  should be acted on is `docs/spec/README.md`'s standing open question and the author's.
- The kit's own `.tasks/README.md`, which is a different file from the template and is not missing the
  row. Check before assuming symmetry.
- Any behaviour change. All three are statements of fact, and the facts are the fix.

## Implementation notes

Item 2 is the one that can be got wrong by doing the obvious thing. Count the rows in the table rather
than trusting either the old number or this task file, which was written on 2026-08-19 and is exactly
the sort of restatement that produced the drift.

Item 1 should keep whatever the docstrings say about *behaviour*, which is accurate and was verified
by `bug-0028` against all twenty shipped bodies. Only the pending-decision sentence and the heading's
id reference are stale.

`depends_on: [bug-0036]` is a file collision, not a logical one: that task also edits
`tests/test_build_adapters.py`.

## Decisions

- **Premise that turned out false, item 2.** This task claimed `docs/spec/README.md` reads "Four do,
  listed below" beside a longer re-approval table. It no longer does, and no count of that table's
  rows survives anywhere in the file. [`chore-0057`](chore-0057-the-marker-key-paragraph-counts-four-against-a-seven-row-table.md)
  removed both counts on 2026-08-22 rather than correcting them, under the rule `chore-0056` earned
  and [`house-style.md`](../../.agents/rules/house-style.md) now carries: never count the rows of a
  table in prose beside it. The table has seven rows and the two counts that remain in that section
  ("Five things read a spec's `status`", and the per-spec amendment counts) were checked and are
  both correct. Nothing was changed for this item; introducing a fresh count would have re-created
  the defect `chore-0057` closed.
- **Premise that turned out false, the out-of-scope note.** This task's scope section says the kit's
  own [`.tasks/README.md`](../README.md) "is a different file from the template and is not missing the
  row", and instructs a reader to check before assuming symmetry. Checked: it is missing it. Both
  field tables carry the same eleven rows, `id` through `created`, and neither names `title`, which
  both `_TEMPLATE.md` files carry as their second key. Only the template was changed, because the
  kit's own README is out of scope by the task's own text; the correction there is a follow-up.
- **Premise that turned out false, item 5.** The `S-022` test-coverage row said the `bug-0027`
  docstrings "describe the amendment as the author's open call". They never did. `git log -S` on both
  "author's call" and "open call" over [`test_validate_skills.py`](../../tests/test_validate_skills.py)
  returns no commit across the file's whole history; that sentence lived only in the parallel
  `S-018` row's subject, [`test_build_adapters.py`](../../tests/test_build_adapters.py). The row is
  corrected rather than carried, and says which half of it was stale and which half was never true.
- **Seam left open deliberately.** Both test files open with a module docstring naming a scenario
  range that stopped short of the ids retagged here: `test_build_adapters.py` says "S-001 through
  S-017", and `test_validate_skills.py` says the suite was extended to "S-009 through S-016". Both
  were already stale before this task and neither is falsified by the retag, since the retag changes
  no test's coverage. They are left for a pass that re-derives the whole coverage claim rather than
  edited here, where the edit would assert a freshness this pass did not establish.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [x] The code-span test class and its cases cite `S-018`, and no test docstring describes that
      decision as still open.
- [x] `docs/spec/README.md`'s marker-key count equals the number of rows in its re-approval table,
      verified by counting the rows.
- [x] `tasks-README.md.tmpl`'s field table has a `title` row.
- [x] `bug-0027`'s test docstrings in `tests/test_validate_skills.py` cite `S-022`, and none
      describes that decision as still open.
- [x] The `S-018` and `S-022` test-coverage rows in the two matrices are re-audited to match the
      retagged docstrings, `re_audited` credits only this pass, and no dated measurement elsewhere in
      either matrix is rewritten.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
