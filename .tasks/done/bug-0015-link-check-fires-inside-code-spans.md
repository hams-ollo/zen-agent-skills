---
id: bug-0015
title: The mislabelled-link check fires on markdown links written inside code spans
type: bug
status: done
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - .tasks/validate.py
  - .agents/skills/init-worktracking/templates/validate.py
  - tests/test_tasks_validate.py
created: 2026-08-05
---

## Problem

`mislabelled_links()` in [`validate.py`](../validate.py) gathers links with a bare regex over the whole
file text, so it cannot tell a link from a **code span that contains link syntax**. A backticked
`` `[README.md](../README.md)` `` renders as literal text and is not clickable by anyone, and the
check reports it anyway.

**This blocks closing [`bug-0012`](bug-0012-links-that-resolve-to-the-wrong-file.md), the task that
added the check.** Its Problem table and its Implementation notes illustrate the defect by quoting
the wrong link form, inside code spans, exactly as an author documenting a link bug must. Both
illustrations resolve from `.tasks/` today, so the file is clean where it sits. The moment it moves
to `.tasks/done/` for closeout, `../README.md` starts resolving to `.tasks/README.md` and the check
fires on its own examples, twice, promoted to errors by `--strict` which CI uses.

Measured 2026-08-05 by copying the file to `.tasks/done/` and running the validator:

```
WARN  .tasks/done/_probe-bug-0012.md: link text names README.md but ../README.md opens .tasks/README.md
WARN  .tasks/done/_probe-bug-0012.md: link text names README.md but ../README.md opens .tasks/README.md
```

**`bug-0012` predicted this exact failure and named it the costliest one.** Its risk section says the
heuristic firing on correct links "would make `validate.py` fail on a clean tree, and the pressure
would be to edit ledger prose to appease it", and its Implementation notes call the false positives
"the whole design problem". The prediction was right and the guard was aimed one case too narrow: the
check correctly skips prose text and `path:line` text, and nothing skips a code span.

`broken_links()` has the same blindness and it has never mattered, because a dangling target inside a
code span is still a dangling target worth knowing about. Only the mislabelled check turns a
deliberately-wrong illustration into an error.

**Authoring this task hit the same wall**, which is the cheapest possible confirmation that the defect
is not specific to `bug-0012`. A first draft of the Implementation notes below wrote the generic link
shape, brackets then parentheses, inside a code span to name the construct being discussed.
`broken_links()` reported it as a dangling relative link and `--strict` failed, so the sentence had to
be reworded to describe the shape in prose instead. Any task file about link syntax will meet this,
and the workaround will always be to avoid writing the thing you are documenting.

## Scope

**In scope:** make `mislabelled_links()` ignore link syntax that sits inside an inline code span, in
[`.tasks/validate.py`](../validate.py) and in the
[`init-worktracking` template copy](../../.agents/skills/init-worktracking/templates/validate.py), which
ships this defect to every scaffolded repository; tests pinning both the single-backtick and
double-backtick forms; then `bug-0012` can be moved to `.tasks/done/` and closed.

**Out of scope:** changing `broken_links()`, which is unaffected for the reason above and where the
current behaviour is arguably correct; the third copy of the link rule inline in
`.github/workflows/checks.yml`, which has no mislabelled check to fix; full CommonMark parsing, which
is far more than this needs; rewording any of `bug-0012`'s prose, which is the repair this task
exists to avoid.

## Implementation notes

**Span-aware, not parser-grade.** The rule that matters is narrow: a link whose opening bracket falls
inside a backtick-delimited run is not a link. Markdown allows a code span to be opened
by any number of backticks and closed by the same number, and `bug-0012`'s own file uses **both** the
single form (`` `[README.md](../README.md)` ``, in the Problem table) and the double form
(``` `` [`README.md`](../README.md) `` ```, in the Implementation notes), so handling only single
backticks fixes one of the two occurrences and leaves the file still failing. Both forms are in the
tree right now, so both are real test cases rather than hypotheticals.

**Prefer under-firing, consistently with the check it amends.** `bug-0012` chose to report this class
as a warning rather than an error precisely because a false positive on a completed record is worse
than a missed link, and the same reasoning says to skip anything ambiguous here rather than to
attempt clever recovery inside a partially-closed span.

**Keep the two copies in step.** This is the constraint `bug-0011` recorded and `bug-0012` honoured:
fixing this repository's validator while the template keeps shipping the gap is the specific mistake
both tasks avoided. The two copies are already character-identical in the code this task touches,
which was verified during `bug-0012`'s reconciliation, so they should stay that way.

**Pin the regression with the real file, not only a fixture.** The fixture proves the rule; moving
`bug-0012` to `done/` and running `--strict` proves the case that motivated it. Do both.

## Decisions

- **Rejected: pairing backtick runs across the whole file**, which is what CommonMark does and was the
  obvious reading of "opened by any number of backticks and closed by the same number". It fails this
  task's own worst case: one stray unmatched backtick pairs with the next stray one and every link
  between them stops being checked, silently. `code_span_ranges()` pairs runs within a single line
  instead, so a stray backtick costs at most its own line and an unmatched run opens nothing.
- **Seam left open deliberately: a code span that wraps across a line break is not recognised.**
  Markdown allows one inside a paragraph, and this checker will still report a mislabelled link there.
  That is the safe side of the trade above, not an oversight: the outcome is the false positive this
  task removes elsewhere, never a check that has switched itself off. Closing it needs paragraph
  awareness, which is the full parsing the Scope section rules out.
- **False premise: the two validator copies are not character-identical across all of
  `mislabelled_links()`.** The Implementation notes say they are, and their code and module-level
  regexes are, which is what the acceptance criterion turns on. Their docstrings deliberately differ:
  this repository's names `.tasks/README.md` and its three real files, the template's is written for a
  scaffolded repository that has neither yet. That divergence is intentional and predates this task.

## Risks and rollback

Required: this touches more than one module (both validator copies plus tests), and it changes what a
shipped scaffold emits.

- **The failure that costs most is over-skipping.** A span detector that is too greedy, for example
  one that treats an unmatched backtick as opening a span that runs to end of file, would silently
  switch the check off for everything after it. That is worse than today's false positive, because a
  disabled check reports success. Mitigate by asserting in a test that a genuine mislabelled link
  **outside** any code span is still reported in a file that also contains backticks.
- Rollback is one revert. The change adds a skip condition and writes no persisted format.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python .tasks/validate.py --strict

- [x] A test proving a mislabelled link inside a **single**-backtick code span is not reported,
      failing against the pre-fix validator.
- [x] A test proving the same for a **double**-backtick code span, since `bug-0012`'s file contains
      both and fixing only one leaves it failing.
- [x] A test proving a genuine mislabelled link outside any code span is **still** reported, in a
      file that also contains code spans, so the fix cannot pass by disabling the check.
- [x] The same skip exists in the template validator, and the two copies remain character-identical
      in `mislabelled_links()` and its module-level regexes.
- [x] `bug-0012` is moved to `.tasks/done/` with `status: done` and its relative links re-anchored,
      and `python .tasks/validate.py --strict` exits 0 with the moved file in place and **no edit to
      either of its two illustrations**.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only
      a maintainer can find out about has not shipped for anyone else.
- [x] File moved to `.tasks/done/`, `status: done`, **with its relative links re-anchored for the
      extra directory level**; one dated line added to `CHANGELOG.md` referencing this task id.
- [x] `bug-0012` closed out in the same pass, since this task exists to unblock it.
