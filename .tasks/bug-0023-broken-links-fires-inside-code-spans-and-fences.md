---
id: bug-0023
title: broken_links() reports a link inside a code span or a fenced block, the rule mislabelled_links() already follows
type: bug
status: open
priority: P2
parent: "ROADMAP Kit hardening (2026-07-25 review pass)"
depends_on: []
touched_files:
  - .tasks/validate.py
  - .agents/skills/init-worktracking/templates/validate.py
  - tests/test_tasks_validate.py
created: 2026-08-08
---

## Problem

[`bug-0015`](done/bug-0015-link-check-fires-inside-code-spans.md) taught this validator that a link
inside an inline code span is not a link, and
[`bug-0017`](done/bug-0017-mislabelled-link-check-fires-inside-fenced-blocks.md) extended that to
fenced blocks. Both landed in `mislabelled_links()`. `broken_links()` never learned either, and
`broken_links()` is what **both** callers actually run: `--strict` over the backlog, and the `--links`
gate that [`checks.yml`](../.github/workflows/checks.yml) calls.

Measured 2026-08-08 against a document whose only two links are a fenced example and an inline code
span, neither of which resolves:

```text
broken_links   -> ['../does-not-exist.md', './nope.md']
mislabelled    -> []
```

**The tree is quiet on a coincidence, not on the rule.** Nine markdown links currently sit inside
code spans or fences across the checked document set, and every one of them resolves, because
`../README.md` written from `.tasks/done/` lands on `.tasks/README.md`. That is precisely the
wrong-file resolution [`bug-0012`](done/bug-0012-links-that-resolve-to-the-wrong-file.md) was filed
about, quoted inside `bug-0012`'s own record, keeping the check silent. Rename or remove
`.tasks/README.md` and six illustrations of a link bug become reported link bugs.

**A comment claims otherwise.** The block above `LINK_RE` in [`validate.py`](validate.py) reads as
though this file's link rule is code-span aware. It is, in one of its two functions.
[`chore-0029`](done/chore-0029-third-copy-of-the-link-rule-in-ci.md) removed the drift between the CI
copy and this one, so the two now agree, on the pre-`bug-0015` behaviour.

**It fired twice while this task set was being written, which is the cost stated as a measurement
rather than a prediction.** Two of the task files filed alongside this one needed a markdown link
quoted as an example, one in a fenced block and one in an inline code span, and `--strict` reported
both as broken links. Both had to be reworded to satisfy the checker, which is exactly what
`chore-0029` describes happening to a `CHANGELOG.md` entry and exactly what `bug-0015` was filed to
stop.

## Scope

**In scope:** give `broken_links()` the same span and fence exclusion `mislabelled_links()` uses, in
both validator copies, and correct the `LINK_RE` comment so it describes what is true.

**Out of scope:**

- The empty-match guard on `--links`, which is
  [`chore-0032`](chore-0032-links-guard-fires-per-run-not-per-pattern.md). Different gap, same
  command, and folding them makes both harder to verify.
- Tilde fences and indented code blocks. `bug-0017` left those open deliberately and neither appears
  anywhere in this repository; leave the seam where it is rather than closing it on the way past.
- Rewriting any existing document to satisfy the new behaviour. Nothing should need it; if something
  does, that is a finding to report rather than a document to edit.

## Implementation notes

`code_span_ranges()` and `fenced_block_ranges()` already exist and are already unioned by
`mislabelled_links()`. The change is to compute the same union in `broken_links()` and skip a match
whose start falls inside it. Reuse the two helpers rather than writing a third scanner: the reason
`bug-0017` kept them separate was that one docstring could not honestly describe both, and that
reasoning does not change with a second caller.

**Both copies move together.** [`validate.py`](validate.py) and the shipped template at
`.agents/skills/init-worktracking/templates/validate.py` are deliberate near-duplicates, because a
scaffolded repository has no way to import from here. `bug-0017` moved both; do the same. Their
docstrings are deliberately retargeted and are expected to differ; the executable code and the
module-level regexes are not.

Cost check before choosing the shape: `broken_links()` runs over every markdown file under `.tasks/`
and every globbed document, so the range computation happens per file rather than per link. Compute
it once per file.

## Risks and rollback

Touches two copies of one module. The failure direction is a check that quietly stops finding real
broken links, which is worse than the false positive it fixes and is exactly what an over-eager
exclusion would produce. `bug-0015` and `bug-0017` both chose "an unterminated fence opens nothing"
for that reason; keep that trade rather than making the scanner more permissive.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [ ] A test with an unresolvable link inside a fenced block, asserting `broken_links()` returns
      nothing. It must fail against the current validator.
- [ ] A test with an unresolvable link inside an inline code span, same assertion, both the single
      and the multi-backtick form.
- [ ] A test that a genuinely broken link **outside** any span or fence is still reported, so the
      exclusion cannot have switched the check off.
- [ ] A test that an unterminated fence does not swallow the rest of the file.
- [ ] Both validator copies carry the same executable change, and a test or an assertion pins that
      they agree.
- [ ] The `LINK_RE` comment states which functions honour the exclusion.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
