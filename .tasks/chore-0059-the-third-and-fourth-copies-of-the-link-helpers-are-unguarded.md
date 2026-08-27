---
id: chore-0059
title: Two of the four copies of the code-span and fence rule promise in a comment to stay character-identical, and nothing checks that they do
type: chore
status: open
priority: P2
parent: "ROADMAP Kit mechanics hardening (2026-07-27 review pass)"
depends_on: []
touched_files:
  - tests/test_validate_skills.py
  - tests/test_build_adapters.py
created: 2026-08-22
---

## Problem

Four copies of the same rule exist in this repository: the two patterns and the two helpers that
decide a markdown link rendered as literal text is not a link.

```text
.tasks/validate.py                                     BACKTICK_RUN_RE FENCE_RE code_span_ranges fenced_block_ranges
.agents/skills/init-worktracking/templates/validate.py  same four
scripts/validate-skills.py                              same four
scripts/build-adapters.py                               same four
```

All four are identical today. Verified by parsing each file and comparing the function bodies as
dumped ASTs with docstrings stripped, and the constants as dumped expressions:

```text
code_span_ranges      sha=d6ce0538e702 in all four
fenced_block_ranges   sha=2fe83488a877 in all four
BACKTICK_RUN_RE       re.compile('`+') in all four
FENCE_RE              re.compile('^ {0,3}(`{3,})([^`]*)$') in all four
```

Copies one and two are held there by a test. Copies three and four are held there by a sentence.

`tests/test_tasks_validate.py` carries `ValidatorCopiesAgreeTests`, whose
`test_the_executable_code_is_identical_in_both_copies` compares the whole module AST of
`.tasks/validate.py` against the `init-worktracking` template, and whose docstring explains why a
list-driven check was not enough: "a list-driven check cannot report a name that nobody added to
the list".

Nothing compares the other two. `scripts/validate-skills.py` says instead:

```python
# These two patterns and the two helpers below are REPRODUCED from `.tasks/validate.py`,
# where bug-0015 and bug-0017 taught the backlog validator that a link rendered as
# literal text is not a link. Copied rather than imported: the two validators are
# separate tools with separate lifecycles, and `validate.py` also ships as a template
# into other repositories, so neither may depend on the other. The regexes are kept
# character-identical to the originals so a later reader can diff the two copies.
```

`scripts/build-adapters.py` says the same thing about being "the third copy", and ends: "The
regexes are kept character-identical to the originals so a later reader can diff the copies when
the rule next changes."

Searched, to establish nothing enforces those two sentences:
`grep -rln "code_span_ranges\|fenced_block_ranges" tests/` returns exactly one file,
`tests/test_tasks_validate.py`, and inside it both identity tests compare `MODULE_PATH` against
`TEMPLATE_PATH`, which are `.tasks/validate.py` and the `init-worktracking` template. No test in
`tests/test_validate_skills.py` or `tests/test_build_adapters.py` names either helper at all.

**A comment promising two files are identical is the exact artefact this repository has already
been burned by, and the burned comment is still quoted in the tree.** `.tasks/validate.py` carried
one, and its own comment at lines 57 to 63 now records what happened to it:

> This comment used to claim the regex was "deliberately identical" to a copy of it inside the docs
> link step in .github/workflows/checks.yml. The claim was true when written and false by the time
> anyone relied on it: bug-0015 taught this copy that a link inside a code span is not a link, and
> the CI copy learned nothing, so the two disagreed about what counts as a link while a comment
> said they could not.

Fixing that drift cost `chore-0029`, which replaced the CI copy with a call. The rule has needed
four separate fixes across its copies, each teaching one copy something the others did not know:
[bug-0015](done/bug-0015-link-check-fires-inside-code-spans.md) on 2026-08-05,
[bug-0017](done/bug-0017-mislabelled-link-check-fires-inside-fenced-blocks.md) on 2026-08-06,
[bug-0023](done/bug-0023-broken-links-fires-inside-code-spans-and-fences.md) and
[bug-0027](done/bug-0027-skill-lint-fires-inside-fenced-blocks.md) both on 2026-08-08. Four fixes
in four days across four copies is the pattern that says the next change will do it again.

The copies are identical right now, so this is a missing guard rather than a live defect.

**This task is one of five in the same class**, grouped 2026-08-22 rather than worked as unrelated errands: a guard that does not guard. The other four are [`chore-0032`](chore-0032-links-guard-fires-per-run-not-per-pattern.md), [`chore-0049`](chore-0049-a-checker-for-conformance-matrix-citations.md), [`chore-0058`](done/chore-0058-no-gate-link-checks-the-markdown-under-agents-outside-skills.md), and [`chore-0060`](chore-0060-the-scaffold-manifest-id-high-water-is-stale-and-unguarded.md). `chore-0058` closed 2026-08-27, and `bug-0045` was the sixth and is closed: it found six of seven gates reporting `ok` over a repository containing nothing. **What the grouping asks of whoever works this one**: when you fix it, look for the next member before you finish, because every member of this class so far was found only by looking after the previous one landed. The pattern behind the class is [`chore-0063`](done/chore-0063-the-repository-has-never-written-down-what-it-keeps-learning.md).

## Scope

**In scope:** extend the existing identity guarantee to the two script copies.

- Compare `code_span_ranges`, `fenced_block_ranges`, `BACKTICK_RUN_RE`, and `FENCE_RE` in
  `scripts/validate-skills.py` and in `scripts/build-adapters.py` against the canonical copy in
  `.tasks/validate.py`, using the AST comparison `ValidatorCopiesAgreeTests` already defines rather
  than a second technique.
- Compare bodies with docstrings stripped, not text. The three docstrings differ deliberately: each
  copy's ends by naming `.tasks/validate.py` as the original, which is the pointer the comments are
  for.
- Put the test where a reader of the file under test will find it. Two small classes, one in
  `tests/test_validate_skills.py` and one in `tests/test_build_adapters.py`, beat one class in a
  third file that neither script's reader opens.

**Out of scope:**

- Unifying the four copies into one importable module. The reason for the duplication is recorded
  in three places and is still true: `.tasks/validate.py` ships as a template into repositories
  that cannot import from here, and the three tools have separate lifecycles. This task tolerates
  the duplication, exactly as `bug-0028` decided, and only removes the silence.
- A whole-module comparison of the kind copies one and two get. The three files are genuinely
  different tools that share four names, so the boundary here is the enumerated set, and the
  standing limitation of an enumerated set should be written into the test's docstring rather than
  discovered later.
- `LINK_RE`, which is deliberately different in `build-adapters.py`: it anchors on `](` rather than
  on the opening bracket, and `rewrite_links()` depends on that. Do not pull it into the set.
- `LINK_SKIP_PREFIXES` and `EXTERNAL_LINK_PREFIXES`, which `.tasks/validate.py` records at its own
  definition as guarding a different rule and deliberately not a fourth and fifth copy.
- The frontmatter parsers, a separate three-way duplication whose copies are not identical and
  which `build-adapters.py` already calls out as "where the duplication is the real problem".

## Implementation notes

Prior art to mirror exactly: `_body_without_docstring()` and `_assignment()` in
`ValidatorCopiesAgreeTests`. Both are static helpers taking a path and a name and returning dumped
AST, and both raise `AssertionError` when the name is absent, which is what makes a rename fail
loudly instead of silently comparing nothing to nothing. Copy that behaviour; a helper that returns
`None` for a missing name would make the whole new test vacuous.

Both new test files already compute a repository root, so no new path constant is needed.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] A test in `tests/test_validate_skills.py` fails when `code_span_ranges`,
      `fenced_block_ranges`, `BACKTICK_RUN_RE`, or `FENCE_RE` in `scripts/validate-skills.py`
      differs from the copy in `.tasks/validate.py`.
- [ ] The same for `scripts/build-adapters.py`, in `tests/test_build_adapters.py`.
- [ ] Each test fails if a compared name is absent from either file, rather than passing over it.
- [ ] Both tests are shown to fail against a deliberately mutated copy, and the verbatim output of
      that run is recorded in the closeout.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
