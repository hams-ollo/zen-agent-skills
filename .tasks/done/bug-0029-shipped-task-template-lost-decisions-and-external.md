---
id: bug-0029
title: The shipped task template lost the two things two skills point at it for, so both are dead in every repository this kit scaffolds
type: bug
status: done
priority: P1
parent: "ROADMAP Kit coherence hardening (2026-08-18 review pass)"
depends_on: [bug-0026]
touched_files:
  - .agents/skills/init-worktracking/templates/_TEMPLATE.md.tmpl
  - .agents/skills/init-worktracking/templates/tasks-README.md.tmpl
  - tests/test_tasks_validate.py
created: 2026-08-18
---

## Problem

The kit's own [`_TEMPLATE.md`](../_TEMPLATE.md) carries an `external:` frontmatter field and a
`## Decisions` section. The template that actually ships into an adopter's repository,
`.agents/skills/init-worktracking/templates/_TEMPLATE.md.tmpl`, carries neither. Measured 2026-08-18:

```text
$ grep -c "external\|## Decisions" .agents/skills/init-worktracking/templates/_TEMPLATE.md.tmpl
0
```

Two shipped skills name that template as the authority on things it does not contain:

- [`fix-batch`](../../.agents/skills/fix-batch/SKILL.md) Step 3 item 8 tells every dispatched agent that
  "the admissible entry kinds and the exclusion list are defined once, in the target repository's task
  template".
- [`pr-describe`](../../.agents/skills/pr-describe/SKILL.md) says "the task template owns which entries
  are admissible", and its closing-reference section reads the `external` field to emit the `Closes`
  line that makes merging a pull request close the upstream issue.

So in a scaffolded repository `fix-batch`'s instruction points at a section that does not exist, and
`pr-describe`'s entire issue-closing feature can never fire, because no task file it reads will ever
carry the field. Neither failure announces itself. This is the shape this kit names as its own enemy:
a feature that reports success while doing nothing.

**This settles a question [`bug-0026`](bug-0026-scaffolded-validator-lost-the-external-check.md)
deliberately deferred.** That task found the sibling half (the shipped *validator* lost the `external`
check) and put this half out of scope, calling it "a separate and arguable question: whether an adopter
should be taught it, or whether the check should simply hold if they find it". The argument that
settles it is that it was never only a teaching question: two shipped skills already treat the template
as the definition, so withholding it does not leave an adopter uninformed, it leaves two skills
pointing at nothing. `bug-0026` also did not look at `## Decisions`, which has the same problem and no
record anywhere.

## Scope

**In scope:** carry the `external:` field and the `## Decisions` section into `_TEMPLATE.md.tmpl` with
their explanatory comments retargeted for a scaffolded repository, mention the `external` field in
`tasks-README.md.tmpl`'s field reference, and add an assertion that the two templates cannot diverge
again on required frontmatter keys or section headings.

**Out of scope:**

- `fix-batch`'s and `pr-describe`'s bodies. They are correct as written; the template is what is
  missing. The four other prose corrections found in the same pass are
  [`chore-0040`](chore-0040-four-coherence-corrections-across-skill-bodies.md).
- The `parent`/ROADMAP tier problem in the same template, which is
  [`bug-0030`](bug-0030-lite-tier-parent-field-has-no-roadmap-to-name.md). Do not fix it here even
  though it is the same file; that task depends on this one for exactly that reason.
- Porting the validator's `external` check. That is `bug-0026`, and this task depends on it.
- Any change to `docs/spec/tracker-links.md`. `S-007` already says what should happen.

## Implementation notes

Retarget the comments rather than copying them. `bug-0017` recorded the rule: the template's prose is
deliberately written for a scaffolded repository and must not tell an adopter about this one. The
`external:` comment in `_TEMPLATE.md` cites `docs/spec/tracker-links.md`, which will not exist in an
adopter's repository, so state the accepted forms (`#123` and `owner/repo#123`, a bare number
rejected) instead of citing the path.

The `## Decisions` section's three admissible entry kinds and its exclusion list are the part
`fix-batch` depends on, so carry them, not just the heading. Carry the "delete this section rather than
leaving it empty" instruction with them; without it the heading becomes the thing the kit's own
template warns against, a heading every task carries and most leave blank.

The drift assertion is the durable half, and the natural home is
[`test_tasks_validate.py`](../../tests/test_tasks_validate.py), which already reads both templates and
which `bug-0026` extends with a validator-drift assertion in the same pass. Prior art for asserting a
relationship between two files rather than pinning a string is
`test_every_hook_in_the_module_is_registered_everywhere` in
[`test_hooks.py`](../../tests/test_hooks.py). Compare the two templates' required frontmatter keys and
their `##` headings as sets; do not compare their prose, which is supposed to differ.

## Decisions

- **A rejected alternative**: the acceptance criterion asks for a test over the *required* frontmatter
  keys, which would not have caught this defect, because `external` is optional in both templates. The
  test compares the full set of frontmatter keys each template declares instead, which fails against
  the pre-change template and is the stronger guarantee.
- **A seam left open deliberately**: the kit template's exclusion list names this repository's report
  file kinds (`<spec>.verification.md`, `<spec>.conformance.md`). A scaffolded repository has no such
  convention, so the shipped copy names the test run and the spec in prose instead. That makes the
  two exclusion lists say the same thing in different words, which the heading-and-field drift test
  tolerates on purpose (`bug-0017`: the prose is retargeted, the structure is not).
- **A seam left open deliberately**: `tasks-README.md.tmpl`'s field table still omits `title`, which
  the template's frontmatter carries. Out of scope here; the new drift test compares the two templates
  to each other, not either template to the README that documents it.

## Risks and rollback

Changes what a scaffolded repository contains, so an adopter who re-scaffolds gets a field and a
section they did not have. That is the point, and the failure direction is benign: `external` is
optional, and the `## Decisions` instruction says to delete the section when it does not apply. The
ordering risk is real though: shipping the field before `bug-0026` ports its validator check would give
an adopter a field whose malformed values nothing catches, which is worse than not shipping it, hence
`depends_on`.

Reversible by reverting one commit. Nothing already scaffolded changes until its owner re-runs
`init-worktracking`.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [x] `_TEMPLATE.md.tmpl` carries an `external:` field whose comment names the accepted forms without
      citing a path that will not exist in an adopter's repository.
- [x] `_TEMPLATE.md.tmpl` carries a `## Decisions` section with all three admissible entry kinds, the
      exclusion list, and the delete-when-empty instruction.
- [x] `tasks-README.md.tmpl`'s field reference names `external` and what it is for.
- [x] A test comparing the two templates' required frontmatter keys and `##` headings as sets, which
      fails against the current templates and passes after the change.
- [x] A scaffolded repository's `_TEMPLATE.md`, filled in with an `external` value, validates against
      the scaffolded validator.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
