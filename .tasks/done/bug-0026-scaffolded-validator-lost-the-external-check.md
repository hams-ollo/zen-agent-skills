---
id: bug-0026
title: The validator the kit scaffolds into an adopter's repository has no external check, so the silent tracker failure is unguarded everywhere it ships
type: bug
status: done
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [bug-0023]
spec: "docs/spec/tracker-links.md"
scenarios: ["S-007", "S-008"]
touched_files:
  - .agents/skills/init-worktracking/templates/validate.py
  - tests/test_tasks_validate.py
created: 2026-08-08
---

## Problem

[`validate.py`](../validate.py) and the copy shipped at
`.agents/skills/init-worktracking/templates/validate.py` are deliberate near-duplicates. Stripping
docstrings and diffing their parsed source, 2026-08-08, gives exactly two differences, and the first
is a missing rule:

```text
--- .tasks/validate.py
+++ .agents/skills/init-worktracking/templates/validate.py
-EXTERNAL_RE = re.compile('^(?:[A-Za-z0-9._-]+/[A-Za-z0-9._-]+)?#\d+$')
-external = fm.get('external', '')
-if external and (not EXTERNAL_RE.match(external)):
-    err(rel, f'external {external!r} is not a GitHub issue reference (#123 or owner/repo#123)')
-def main(argv=None) -> int:
+def main() -> int:
```

`S-007` in [`tracker-links.md`](../../docs/spec/tracker-links.md) makes a malformed `external` value an
**error** rather than a warning, and the reason is written into the validator's own comment: the value
is emitted verbatim into a pull request description, so "a form GitHub does not recognise is ignored
silently, and the issue simply never closes".

**The guard exists only in the repository that authored it.** [`pr-describe`](../../.agents/skills/pr-describe/SKILL.md)
ships to adopters and tells an agent, in its body, that a task file may carry an `external` field.
`init-worktracking` scaffolds the tracker into that same repository with a validator that never checks
it. So every repository this kit sets up gets the feature and not the check, which is the exact
silent failure `S-007` exists to prevent.

The conformance matrix records `S-007` as Conformed, citing `.tasks/validate.py`. That is accurate for
this repository and does not ask the portability question, so nothing was wrong at the time and
nothing has been looking since.

The second half of the diff is smaller and worth closing in the same pass: `chore-0017` made the CLI
layer injectable as `main(argv=None)` so a test can drive it, and that did not travel either, leaving
the scaffolded validator's CLI unreachable from a test in an adopter's repository.

## Scope

**In scope:** carry `EXTERNAL_RE`, the `external` check, and `main(argv=None)` into the template copy,
and add an assertion that keeps the two copies' executable code in step so this cannot recur silently.

**Out of scope:**

- The `external` field's documentation in the scaffolded tracker. The template's `_TEMPLATE.md.tmpl`
  and `tasks-README.md.tmpl` do not mention the field at all, which is a separate and arguable
  question: whether an adopter should be taught it, or whether the check should simply hold if they
  find it. Do not add prose to those templates in this task; report the gap and let the author
  decide.
- `pr-describe`'s body.
- Amending `tracker-links.md`. `S-007` already says what should happen; only the implementation is
  short.

## Implementation notes

Copy the executable code, not the docstrings. `bug-0017` recorded the rule: the template's docstrings
are deliberately retargeted so a scaffolded repository is never told about this one, and what is
supposed to be identical is the executable code and every module-level regex. Reproduce that
distinction rather than collapsing it.

The drift assertion is the durable half. A test that parses both files, strips docstrings, and
compares the result would have caught this and would catch the next one; there is prior art for the
idea in the wiring-consistency tests in [`test_hooks.py`](../../tests/test_hooks.py), which assert a
relationship between files rather than pinning a string. If a full comparison proves too brittle,
assert the narrower property that every module-level regex and every top-level function name present
in one is present in the other, and say in the test why the bound was chosen.

`depends_on: [bug-0023]` is a file-collision ordering, not a logical one. That task edits the same
template validator, and two agents changing it in parallel collide by construction.

## Decisions

- **Rejected the narrower drift bound this task offered as a fallback** (every module-level regex and
  top-level function name present in one copy is present in the other). Full stripped-AST equality
  was tried first and turned out exact, so the weaker bound bought nothing. It is also the shape that
  failed here: the pre-existing name-list test carried a comment recording `EXTERNAL_RE` as this
  repository's alone, so no list-driven check could ever have reported its absence from the template.
  A guarantee that has to be enumerated cannot cover the rule nobody thought to enumerate. The two
  name-list tests are kept for their sharper failure messages, not for their coverage.
- **Rejected a separate template test class restating S-007 and S-008.** `TemplateExternalFieldTests`
  subclasses `ExternalFieldTests` and swaps a `module` attribute, so both copies are held to one set
  of assertions. Two independently authored suites for one contract can drift apart in exactly the
  way the two validators did.
- **Seam left open deliberately:** the `external` field is now *validated* in a scaffolded repository
  and *documented* nowhere in it. `_TEMPLATE.md.tmpl` and `tasks-README.md.tmpl` still do not mention
  it, so an adopter meets the rule only by tripping it. This task's scope section rules that out of
  scope and asks for the gap to be reported rather than closed, so it is left for the author to
  decide whether the scaffold should teach the field or only guard it.

## Risks and rollback

Changes what a scaffolded repository validates, so an adopter who re-scaffolds gets a check they did
not have. That is the point, and the failure direction is a check that fires on a form GitHub does
accept. `EXTERNAL_RE` is already exercised here against both accepted forms and the rejected bare
number, so port it verbatim rather than rewriting it.

Reversible by reverting one commit. Nothing already scaffolded changes until its owner re-runs
`init-worktracking`.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [x] A test driving the **template** validator that a malformed `external` value fails validation and
      exits non-zero (`S-007`). It must fail against the current template.
- [x] A test driving the template validator that an absent `external` key passes (`S-008`), and that
      both `#123` and `owner/repo#123` are accepted.
- [x] A test that the two validator copies' executable code agrees, which fails if either gains a rule
      the other lacks.
- [x] The template's `main` accepts an injectable `argv`, and a test drives it.
- [x] The template validator still runs standalone in a directory holding no other file from this kit,
      which is the property `chore-0029` demonstrated and this task must not break.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
