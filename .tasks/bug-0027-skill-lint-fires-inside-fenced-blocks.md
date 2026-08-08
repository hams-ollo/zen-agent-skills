---
id: bug-0027
title: The skill lint reports an example link inside a fenced block, so a skill cannot show one
type: bug
status: open
priority: P2
parent: "ROADMAP Kit mechanics hardening (2026-07-27 review pass)"
depends_on: []
spec: "docs/spec/validate-skills.md"
scenarios: ["S-009"]
touched_files:
  - scripts/validate-skills.py
  - tests/test_validate_skills.py
created: 2026-08-08
---

## Problem

`check_links()` in [`validate-skills.py`](../scripts/validate-skills.py) matches every markdown link
in a `SKILL.md` with a bare regex and resolves each one on disk. It has no notion of an inline code
span or a fenced code block, so a skill body that **shows** an example link fails the lint.

Reproduced 2026-08-08 with a synthetic skill whose body contains a `markdown` fenced block holding
one ordinary link, written to a `references/does-not-exist.md` target:

```text
ERROR demo/SKILL.md: link target does not exist: references/does-not-exist.md
Checked 1 skill(s): 1 error(s), 0 warning(s).   exit: 1
```

**The example above is described rather than shown, and that is the finding twice over.** Writing the
literal fenced link into this task file made `broken_links()` in [`validate.py`](validate.py) report
it, because that function has the same gap in the other validator. See
[`bug-0023`](bug-0023-broken-links-fires-inside-code-spans-and-fences.md), whose reproduction this
is.

No skill in the kit does this today, so the defect is latent rather than live. It is worth closing
anyway, because the skills most likely to want a fenced example link are the documentation ones,
[`doc-author`](../.agents/skills/doc-author/SKILL.md),
[`new-task`](../.agents/skills/new-task/SKILL.md), and
[`init-worktracking`](../.agents/skills/init-worktracking/SKILL.md), and the author who hits it gets
an error whose cause is not visible in the message.

This is the same class as [`bug-0023`](bug-0023-broken-links-fires-inside-code-spans-and-fences.md) in
a different module. `bug-0015` and `bug-0017` taught the backlog validator the rule; nothing carried
it here, and the comment at `LINK_SKIP_PREFIXES` in [`validate.py`](validate.py) notes only that this
script guards a *different* rule about escaping the skill tree, which is true and does not cover the
fence question.

## Scope

**In scope:** make `check_links()` skip a link whose opening bracket falls inside an inline code span
or a fenced code block, and cover it with tests.

**Out of scope:**

- The escape rule. A link that leaves the shipped `.agents/` tree stays an error, and an absolute or
  `file://` link stays an error here even though the backlog validator tolerates one, for the reason
  the `LINK_SKIP_PREFIXES` comment already gives: weakening it would trade a real portability check
  for a cosmetic one.
- Link-checking a skill's supporting files, which is
  [`chore-0036`](chore-0036-link-check-skill-supporting-files.md) and depends on this.
- The sibling-skill reference check, which reads a name rather than a path and is unaffected.

## Implementation notes

The backlog validator already solves this, in `code_span_ranges()` and `fenced_block_ranges()`. Those
two live in a file this script must not import from, since `validate-skills.py` and
[`validate.py`](validate.py) are separate tools with separate lifecycles and one already ships as a
template into other repositories. Reproducing the two helpers here is the honest option; say so in a
comment, name where the rule came from, and keep the two module-level regexes character-identical to
the originals so a later reader can diff them.

Keep the trade the originals made. An unmatched backtick run opens nothing and an unterminated fence
opens nothing, because a scanner that ran an unclosed fence to end of file would switch the link check
off for everything below it and report success, which is worse than the false positive being removed.

**The contract may want a clause.** `S-009` in [`validate-skills.md`](../docs/spec/validate-skills.md)
says a link to a target that does not exist is reported, with no exception for one that renders as
literal text. Per the convention in [`docs/spec/README.md`](../docs/spec/README.md), amending an
approved spec keeps `status: approved`, carries a dated note, and is marked pending the author's
re-approval, and every amendment in this repository so far records the author's explicit instruction.
This task carries none, so record the divergence in the closeout and let the author decide, following
what `chore-0031` did in the same position.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [ ] A test with an unresolvable link inside a fenced block in a `SKILL.md`, asserting no error. It
      must fail against the current `validate-skills.py`.
- [ ] A test with an unresolvable link inside an inline code span, both the single and the
      multi-backtick form.
- [ ] A test that a genuinely broken link outside any span or fence is still an error, so the
      exclusion cannot have switched the check off.
- [ ] A test that a link **escaping** the shipped tree is still an error even inside a fence, or an
      explicit recorded decision that it is not, with the reasoning.
- [ ] A test that an unterminated fence does not swallow the rest of the body.
- [ ] Every real skill still lints clean.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
