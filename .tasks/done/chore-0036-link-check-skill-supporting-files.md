---
id: chore-0036
title: A skill's supporting files are never link-checked, so the one tree that ships into an adopter's repository is unguarded
type: chore
status: done
priority: P2
parent: "ROADMAP Kit mechanics hardening (2026-07-27 review pass)"
depends_on: [bug-0027]
spec: "docs/spec/validate-skills.md"
scenarios: []
touched_files:
  - scripts/validate-skills.py
  - tests/test_validate_skills.py
created: 2026-08-08
---

## Problem

`check_links()` in [`validate-skills.py`](../../scripts/validate-skills.py) is called once per skill,
with that skill's `SKILL.md` text. Nothing reads a skill's `templates/` or `references/` files. The
`--links` globs the CI gate passes (`*.md`, `.github/**/*.md`, `docs/**/*.md`) never reach
`.agents/skills/`, and the templates carry a `.tmpl` suffix, so no `.md` glob would find them
regardless.

That leaves 14 supporting files unchecked across two skills,
[`init-worktracking`](../../.agents/skills/init-worktracking/SKILL.md) with nine and
[`project-bootstrap`](../../.agents/skills/project-bootstrap/SKILL.md) with five. Seven of the nine
`init-worktracking` templates carry relative markdown links, and those links are written verbatim into
an adopter's repository as `AGENTS.md`, `.tasks/README.md`, `ROADMAP.md`, and the rest.

I simulated the scaffold on 2026-08-08, placing each template where the skill body says it lands, and
resolved every link from its destination: **0 dangling links today**. So this is a coverage gap and
not a live defect. It is worth closing because "a link that resolves here and dangles where the file
is actually used" is the failure the portability contract in
[`AGENTS.md`](../../AGENTS.md) is built around, and this is the one path where nothing looks at all.

## Scope

**In scope:** link-check the files a skill ships beside its `SKILL.md`, against the location those
files occupy in the shipped layout.

**Out of scope:**

- The scaffolded **destination** geometry. A template's links resolve from where the template is
  written, not from where it sits in this repository, and modelling that placement is a second
  question. Decide and state which of the two this task checks; see the note below.
- Widening the CI `--links` globs to cover `.agents/`. The two rules differ, and the skill tree's rule
  is the portability one that `validate-skills.py` owns.
- Any change to the templates themselves. If the new check finds a real dangling link, that is a
  finding to report, and fixing it is a separate decision.

## Implementation notes

The honest bound is the design work here, and getting it wrong in either direction is worse than the
gap. A template is authored to be **placed elsewhere**, so a link inside `AGENTS.md.tmpl` whose
target is `.tasks/` is correct at the adopter's repository root and dangles where the file currently
sits. Resolving those links relative to `.agents/skills/init-worktracking/templates/` would report
every one of them as broken and make the check unusable, which is the same mistake the `file://`
tolerance in [`validate.py`](../validate.py) was added to undo.

Two defensible answers:

- **Check only `references/`**, which is read in place and whose links must resolve from the skill
  directory, and state that `templates/` is deliberately excluded because its links are written for a
  destination this script does not know.
- **Check `templates/` too, against a declared destination.** The skill body already states where each
  template lands, so a small mapping declared in the skill or the linter can be resolved against. More
  coverage, and it adds a second source of truth that can drift from the skill body.

Take the first unless the second can be made drift-proof, and record the choice and the rejected
alternative. A stated limit is worth more than coverage nobody can trust.

`depends_on: [bug-0027]` is both an ordering and a correctness edge: that task teaches `check_links()`
about code spans and fences, and a template full of fenced examples would otherwise light up the
moment this widens the file set.

## Decisions

**The bound: a supporting markdown file is link-checked where it sits, unless its name carries the
`.tmpl` suffix.** That suffix is this kit's own marker for content written into another repository,
and it is a property of the file rather than a table, so it cannot drift from the skill body. A
`references/` note is checked the day one exists, because it is markdown without the suffix.

- **Rejected: check `templates/` against a declared destination** (the second option in the notes
  above). It needs a mapping of template to destination path, which is a second source of truth
  beside the skill body and drifts from it silently. Silent drift is the failure this whole rule
  exists to catch, so buying coverage with it is a bad trade.
- **Rejected: check only `references/` and exclude `templates/` wholesale** (the first option, and
  the one this task told me to take by default). It is excluded on the facts rather than on the
  argument: **no skill in this kit has a `references/` directory at all**, so that rule would ship a
  check that reads zero files and reports a coverage number that cannot distinguish a working walk
  from a broken one. It would also skip
  [`project-bootstrap/templates/house-code-style.md`](../../.agents/skills/project-bootstrap/templates/house-code-style.md),
  which is not a template in the sense that matters: it documents the directory it sits in, its
  SKILL.md links to it as `templates/house-code-style.md`, it is never written anywhere else, and its
  one relative link must resolve from where it sits. Directory name is a proxy for the real question
  and the suffix is the answer to it. The chosen rule is a strict superset of this one.
- **The cost, stated rather than hidden:** a destination-bound markdown file added to a `templates/`
  directory *without* the `.tmpl` suffix would be checked against this repository and would report
  links written for somewhere else. That failure is loud, and the fix is a rename that also makes the
  file read as a template to every human. The rejected rule's failure is silent, which is worse.

**Premise that turned out false: the file counts in the Problem section.** It claims 14 supporting
files with nine in `init-worktracking` and five in `project-bootstrap`; the first three numbers are
right and the fourth claim, "ten of the `init-worktracking` templates carry relative markdown links",
cannot be, since there are only nine of them. Measured at `3be5924`: **seven** of the nine carry
relative markdown links (`_TEMPLATE.md.tmpl` and `validate.py` carry none), and one
`project-bootstrap` supporting file carries one, for eight in total across both skills. The
classification the new rule ships is 1 markdown, 8 template, 5 non-markdown, pinned in
`test_classification_of_the_real_shipped_supporting_files`.

**Seam left open deliberately: `templates/` link coverage is still zero and stays that way.** The
scaffolded destination geometry is out of scope by this task's own Scope section, and the honest
reason it can wait is in the Problem section: the 2026-08-08 simulation found 0 dangling links. The
new check confirms that from the other side, in that nothing it does read reports anything.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [x] A test with a skill carrying a supporting file whose relative link does not resolve, asserting
      the lint reports it and names the file. It must fail against the current `validate-skills.py`.
- [x] A test that a supporting file with resolving links passes.
- [x] A test that a link escaping the shipped `.agents/` tree from a supporting file is reported, the
      same rule `SKILL.md` bodies already carry.
- [x] Whatever is excluded is excluded **by a stated rule with a test**, not by omission.
- [x] Every real skill still lints clean, and the run says how many files it checked so the number is
      comparable across runs.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
