---
id: chore-0045
title: Three one-line corrections the 2026-08-19 waves surfaced, bundled because none carries a design question
type: chore
status: open
priority: P2
parent: "ROADMAP Kit coherence hardening (2026-08-18 review pass)"
depends_on: [bug-0036]
touched_files:
  - tests/test_build_adapters.py
  - docs/spec/README.md
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
`TestRewriteLinksInsideCodeSpansAndFences` in [`test_build_adapters.py`](../tests/test_build_adapters.py)
is headed "Scenarios S-003 through S-008 refined" and says at line 106 that an "`S-018` in that shape
is the author's call, recorded in `bug-0028`'s decisions". The author made that call on 2026-08-18 and
`chore-0043` added `S-018` to the contract on 2026-08-19, so the tests can now cite the scenario they
protect instead of describing a pending question. This matters slightly more than a stale comment:
`spec-conformance` reads test tags as evidence, and a test tagged to a refinement rather than to an id
is harder to map to the row it supports.

**2. `docs/spec/README.md` says four where its own table says five.**
The marker-key section at line 64 reads "Four do, listed below", and the re-approval table below it
has carried five rows since `house-review` was added. `chore-0043` updated the neighbouring line to
"As of 2026-08-19, five specs", so the document now contradicts itself two lines apart. The count is
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

**Out of scope:**

- `bug-0027`'s tests in `tests/test_validate_skills.py`, which carry the same stale phrasing about
  `validate-skills.md`. That id does not exist until [`chore-0039`](chore-0039-amend-validate-skills-spec-for-the-code-span-exception.md)
  lands, so retagging them is that task's follow-up, not this one's. Do not guess the id.
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

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [ ] The code-span test class and its cases cite `S-018`, and no test docstring describes that
      decision as still open.
- [ ] `docs/spec/README.md`'s marker-key count equals the number of rows in its re-approval table,
      verified by counting the rows.
- [ ] `tasks-README.md.tmpl`'s field table has a `title` row.
- [ ] `tests/test_validate_skills.py` is untouched, since its id does not exist yet.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
