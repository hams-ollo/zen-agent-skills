---
id: chore-0032
title: The --links empty-match guard fires per run, so one dead glob checks nothing and passes
type: chore
status: done
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [chore-0029]
touched_files:
  - .tasks/validate.py
  - .agents/skills/init-worktracking/templates/validate.py
  - tests/test_tasks_validate.py
  - .github/workflows/checks.yml
created: 2026-08-06
---

## Problem

`chore-0029` gave `--links` a guard against the failure its own risk section named as costliest: a
link check that passes instantly having checked nothing. The guard exits non-zero when the patterns
match no documents. **It fires only when every pattern matches nothing.**

CI calls it with three patterns. If one stops matching, the step passes on the strength of the
others, and the only signal is a document count nobody is comparing against anything:

```
python .tasks/validate.py --links "*.md" "docs/**/*.md" "totally-gone/**/*.md"
checked 37 documents, 0 broken link(s)     exit 0

python .tasks/validate.py --links "*.md" ".github/**/*.md"
checked 9 documents, 0 broken link(s)      exit 0
```

Measured 2026-08-06 during `chore-0029`'s verification. **Rename `docs/` and CI passes having checked
9 of 38 documents.** `docs/` holds 29 of the 38, so the great majority of the coverage disappears
while the step reports success.

**The workflow comment overstated this and has been corrected** to state the real bound, so nothing
in the tree currently claims a property the code does not have. The gap itself is still open, which
is what this task closes.

**This is the fourth instance of one failure shape in two waves**, which is the reason it is worth a
task rather than a shrug. A blank line deleted a provenance record (`bug-0016`); an unreadable file
deletes all of a file's records (`bug-0019`); a stray backtick could have disabled the link check
below it (`bug-0015`, guarded); and a dead glob drops 29 documents. Every one of them exits 0.

**This task is one of five in the same class**, grouped 2026-08-22 rather than worked as unrelated errands: a guard that does not guard. The other four are [`chore-0049`](chore-0049-a-checker-for-conformance-matrix-citations.md), [`chore-0058`](chore-0058-no-gate-link-checks-the-markdown-under-agents-outside-skills.md), [`chore-0059`](../chore-0059-the-third-and-fourth-copies-of-the-link-helpers-are-unguarded.md), and [`chore-0060`](chore-0060-the-scaffold-manifest-id-high-water-is-stale-and-unguarded.md). `chore-0058` closed 2026-08-27, and `bug-0045` was the sixth and is closed: it found six of seven gates reporting `ok` over a repository containing nothing. **What the grouping asks of whoever works this one**: when you fix it, look for the next member before you finish, because every member of this class so far was found only by looking after the previous one landed. The pattern behind the class is [`chore-0063`](chore-0063-the-repository-has-never-written-down-what-it-keeps-learning.md).

## Scope

**In scope:** make the guard per pattern, so a pattern matching nothing fails the run and names
itself, in [`.tasks/validate.py`](../validate.py) and the
[template copy](../../.agents/skills/init-worktracking/templates/validate.py); tests pinning the
one-of-three case; and whatever the workflow comment should say once the bound changes.

**Out of scope:**

- Which globs CI passes. That set is `chore-0029`'s and is deliberate.
- The disjoint coverage between `--strict` and `--links`, which is deliberate and load-bearing.
- Asserting an absolute document count in CI, which would fail on every legitimate addition and is
  the reason `chore-0018` and `chore-0019` moved to globs in the first place.
- `broken_links()` and `mislabelled_links()`, which are unaffected.

## Implementation notes

**A pattern legitimately matching nothing is the case to think about before writing the check.** In
this repository all three CI globs always match, but an adopter's scaffolded repository may have no
`.github/` at all, and the template ships this same code. A per-pattern failure that cannot be
relaxed would make the scaffold's own check unusable in a repo without CI. Either let a caller mark a
pattern optional, or have the scaffold pass only patterns it knows match, and say which in the
template's comment.

**Name the dead pattern in the message.** "No document matched" without saying which pattern died
sends the reader to check three globs by hand, and the whole value here is that the failure is
self-explaining.

**Keep the two copies in step**, the constraint `bug-0011`, `bug-0012`, `bug-0015`, `bug-0017`, and
`chore-0029` each honoured in turn. The executable code and module-level regexes stay identical; the
template's prose stays retargeted so it never names this repository.

## Decisions

- **Rejected: an optional-pattern mechanism.** The implementation notes offered a caller-side marker
  (a prefix, or a second flag) as one of two ways to keep the scaffold usable. It was rejected after
  enumerating every caller: `scripts/run-checks.py`'s `doc links` gate passes `*.md`,
  `.github/**/*.md`, and `docs/**/*.md`, all three of which match here (8, 1, and 36 documents on
  2026-08-27); [`doc-sync`](../../.agents/skills/doc-sync/SKILL.md) passes the single path of the
  document it just edited; and **the scaffold ships no automated caller at all**, since
  `init-worktracking` writes no workflow file and no template invokes `--links`. So the mechanism
  would have shipped unexercised, and an escape hatch is the most likely route by which this guard
  stops guarding a second time. The other option offered was taken instead: the template's usage
  example now names `'*.md'` alone and says in prose to add `'docs/**/*.md'` once a `docs/` directory
  exists, so no scaffolded caller can carry a pattern its tree lacks.
- **The two copies are kept in step by a check, not by hand.** No new mechanism was needed:
  `ValidatorCopiesAgreeTests.test_the_executable_code_is_identical_in_both_copies` in
  [`tests/test_tasks_validate.py`](../../tests/test_tasks_validate.py) already compares the two files as
  dumped ASTs with docstrings stripped, so an edit landing in one copy alone fails the suite. That is
  the state `chore-0059` wants for the third and fourth copies of the link helpers and this pair
  already has; writing a second, narrower assertion for `check_links` alone was rejected as the
  weaker guarantee `bug-0026` proved cannot report a name nobody enumerated.
- **False premise: the workflow no longer holds the comment this task was written to correct.**
  `.github/workflows/checks.yml` is in `touched_files` because in 2026-08-06 it passed the globs
  itself. `feat-0045` has since moved every gate into `scripts/run-checks.py`, so the workflow now
  runs `python scripts/run-checks.py` and restates nothing, and the comment describing the guard's
  bound lives at the `doc links` gate in that script. The comment was corrected there and
  `checks.yml` was left untouched, which satisfies the criterion where it now applies.
- **False premise: the document counts in this task are stale, in the direction that makes the
  defect worse.** The task records 38 documents with `docs/` holding 29. Re-measured 2026-08-27:
  45 documents, `docs/` holding 36. Renaming `docs/` would drop 36 of 45 rather than 29 of 38, so
  the coverage the old guard let disappear has grown since the task was written.

## Risks and rollback

Required: this changes a required CI gate and what a shipped scaffold emits.

- **The failure that costs most is a gate that now fails for a legitimate reason**, for example an
  adopter with no `.github/` directory, because a gate that cries wolf gets deleted. Decide the
  optional-pattern story before implementing, not after, and cover the scaffold case in a test.
- Rollback is one revert of the guard plus the workflow comment; no persisted format changes.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python .tasks/validate.py --strict

- [x] A test proving one pattern matching nothing, among several that match, exits non-zero. It must
      fail against the current implementation.
- [x] The message names the pattern that matched nothing.
- [x] A test proving the all-patterns-dead case still fails, so the existing guard is not lost.
- [x] A test covering the scaffold case: a repository with no `.github/` runs the template's own
      check without a spurious failure, or the optional-pattern mechanism is exercised.
- [x] `python .tasks/validate.py --links "*.md" ".github/**/*.md" "docs/**/*.md"` still reports 38
      documents and 0 broken links against this tree.
- [x] The workflow comment describes the bound the code now has.
- [x] The two validator copies remain identical in the executable code and module-level regexes.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason.
- [x] File moved to `.tasks/done/`, `status: done`, **with its relative links re-anchored for the
      extra directory level**; one dated line added to `CHANGELOG.md` referencing this task id.
