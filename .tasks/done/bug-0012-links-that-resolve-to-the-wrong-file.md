---
id: bug-0012
title: Three links in done/ resolve to the wrong README, and existence checking cannot see them
type: bug
status: done
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [bug-0011]
touched_files:
  - .tasks/validate.py
  - .agents/skills/init-worktracking/templates/validate.py
  - tests/test_tasks_validate.py
  - .tasks/done/chore-0001-fix-readme-spine-and-stale-notes.md
  - .tasks/done/bug-0004-reinstall-not-idempotent-windows-py39.md
  - .tasks/done/chore-0004-align-docs-to-spine.md
created: 2026-08-03
---

## Problem

`bug-0011` repaired 101 dangling links and added a check that resolves every link from the directory
the file actually lives in. That closed the dangling class completely. It does not close the class
underneath it: **a link that still resolves, to the wrong file.**

`.tasks/README.md` exists, so `../README.md` written from `.tasks/done/` resolves to it rather than to
the root `README.md`. Existence is satisfied, the check passes, and the link is wrong. Five files in
`done/` carry that link and three of them mean the root README, judged by their own link text and by
the prose around them:

| File | Link text and context | Means | Resolves to |
|---|---|---|---|
| `done/chore-0001-fix-readme-spine-and-stale-notes.md:16` | "`[README.md](../README.md)` has three real inaccuracies: the "workflow spine" mermaid diagram" | root | `.tasks/README.md` |
| `done/bug-0004-reinstall-not-idempotent-windows-py39.md:27` | "`README.md` says "The installer is" | root | `.tasks/README.md` |
| `done/chore-0004-align-docs-to-spine.md:29` | "`README.md` never mentions the spine. Its capability sentence" | root | `.tasks/README.md` |

The other two are correct and must not be touched: `done/bug-0002-agents-section-references-by-name.md`
and `done/bug-0011-tasks-links-break-on-move-to-done.md` both name `.tasks/README.md` in their link
text, which is what `../README.md` resolves to from `done/`.

**This is not a regression from `bug-0011`.** All three resolved to the wrong file before it as well,
which is precisely why they were never among the 101: nothing dangled. `bug-0011`'s summary that the
tree now has zero broken links is accurate and means *nothing dangles*, not *every link is correct*.

**Found by the automated reviewer on `bug-0011`'s own pull request**, which observed that
`../README.md` still resolves in a real scaffold and so does not reliably pin the failure mode the
regression tests describe. The tests are hermetic and correct inside their fixture, which creates a
root `README.md` and no `.tasks/README.md`, so they do prove the validator's location-sensitivity.
The reviewer's underlying point was about the repository, not the fixture, and it was right.

## Scope

**In scope:** re-anchor the three links above to `../../README.md`; add a check for the class, so a
link whose text names a path is compared against the path it actually resolves to; propagate the check
to [`init-worktracking`'s template validator](../../.agents/skills/init-worktracking/templates/validate.py),
which carries the same gap and ships to every scaffolded repository; tests for both the positive case
and the two false-positive cases below.

**Out of scope:** rewriting any other content in the three ledger files, which are records of past
states; the two links that are already correct; auditing link *text* for accuracy generally, which is
prose review and not mechanical; the three report-only findings `bug-0011` filed against
`.github/workflows/checks.yml` and left deliberately alone.

## Implementation notes

- **The check is a heuristic and its false positives are the whole design problem.** The mechanical
  form is: when a link's text names something path-shaped, resolve the target and compare. It fires
  correctly on `` [`README.md`](../README.md) `` from `done/`. It must not fire on link text that is
  prose rather than a path (`[the readme](../README.md)`), and it must not fire when the text names a
  path *with* a line suffix, as in `` [`.tasks/README.md:29`](../README.md) ``, which is correct today
  in `done/bug-0002`. Both of those exist in the tree right now, so both are real test cases and not
  hypotheticals.
- **Prefer under-firing.** `bug-0011` chose to check links in `done/` knowingly, on the ground that a
  link is a live affordance a reader clicks. The same logic applies here, but a false positive on a
  ledger file is worse than a missed one: it pushes an author to reword a historical record to satisfy
  a checker. If the heuristic cannot be made quiet, report the finding as a warning rather than an
  error and say so in the usage text.
- Mirror `bug-0011`'s structure: the check belongs beside `broken_links()` in
  [`.tasks/validate.py`](../validate.py), and the two copies of the validator must stay in step. Fixing
  only this repository's copy while the template keeps shipping the gap is the mistake `bug-0011`
  explicitly avoided and recorded.
- The three re-anchors are one-line edits each and change no other text in those files, matching the
  97-insertions-against-97-deletions discipline `bug-0011` used so no completed record was rewritten.

## Risks and rollback

Required: this touches more than one module (both validator copies plus tests), and it changes what a
shipped scaffold emits.

- **The heuristic firing on correct links is the failure that costs most.** It would make
  `validate.py` fail on a clean tree, and the pressure would be to edit ledger prose to appease it.
  Mitigate by pinning both false-positive cases named above as tests before implementing the check,
  not after.
- Rollback is one revert. The change adds a check and edits three links; it writes no persisted format
  and changes no interface.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py"

- [x] A test proving a link whose text names a path but resolves elsewhere is reported, failing
      against the pre-fix validator.
- [x] A test proving prose link text (`[the readme](../README.md)`) is **not** reported.
- [x] A test proving path-with-line-suffix text (`` [`.tasks/README.md:29`](../README.md) ``) is
      **not** reported, since that link is correct from `done/`.
- [x] `python .tasks/validate.py --strict` exits 0 on the repaired tree, and reported non-zero (or
      warned, per the decision above) on the tree before the three re-anchors.
- [x] The three links named in the Problem table resolve to the root `README.md`; the two correct ones
      are byte-identical to their current state.
- [x] The same check exists in the template validator, verified against a freshly scaffolded throwaway
      repository as `bug-0011` did.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

**Closure is blocked on [`bug-0015`](bug-0015-link-check-fires-inside-code-spans.md), and the code in
this task has already landed.** Recorded 2026-08-05 during reconciliation, so the open status is not
read as unfinished work. Every acceptance criterion above is met and verified independently, and the
change is in the working tree. What cannot happen yet is the move to `.tasks/done/`: the two
illustrations of the defect in the Problem table and the Implementation notes sit inside code spans,
and the check this task added reads link syntax by regex without knowing what a code span is, so from
`done/` it fires on this file's own examples and `--strict` fails. Rewording them is the repair this
task's own risk section warns against, so `bug-0015` fixes the checker instead and closes this task in
the same pass.

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only
      a maintainer can find out about has not shipped for anyone else.
- [x] File moved to `.tasks/done/`, `status: done`, **with its relative links re-anchored for the
      extra directory level**; one dated line added to `CHANGELOG.md` referencing this task id.
