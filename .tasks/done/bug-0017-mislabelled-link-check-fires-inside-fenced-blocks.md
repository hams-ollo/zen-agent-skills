---
id: bug-0017
title: The mislabelled-link check still fires on links inside fenced code blocks
type: bug
status: done
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [bug-0015]
touched_files:
  - .tasks/validate.py
  - .agents/skills/init-worktracking/templates/validate.py
  - tests/test_tasks_validate.py
created: 2026-08-06
---

## Problem

`bug-0015` taught `mislabelled_links()` to skip a link whose opening bracket falls inside an **inline**
code span. A link inside a **fenced** block, opened and closed by a line of three or more backticks,
is still reported. Found by independent verification of `bug-0015` on 2026-08-06, which probed a
fenced block and got back one finding for a link that renders as literal text and is clickable by
nobody.

`code_span_ranges()` in [`validate.py`](../validate.py) pairs backtick runs **within a single line**, so
a fence, whose delimiters sit on lines of their own with nothing else on them, never pairs with
anything. That is not an oversight in the pairing rule, it is the pairing rule working as designed on
a construct it was not built to see.

**This is the same defect class `bug-0015` closed, one construct over.** The reason it did not close
with it is that `bug-0015` scoped itself to the inline form, because that was the form blocking
`bug-0012`, and full CommonMark parsing was explicitly ruled out.

**The seam is currently undocumented, which is the part worth fixing regardless.** `bug-0015`'s
decision log records the cross-line inline span as a deliberate seam and explains the trade. It does
not mention fenced blocks, so a future reader finds no record that this case was considered at all,
and the next author to meet it will re-derive the analysis from scratch.

## Scope

**In scope:** make `mislabelled_links()` skip a link inside a fenced code block, in
[`.tasks/validate.py`](../validate.py) and in the
[`init-worktracking` template copy](../../.agents/skills/init-worktracking/templates/validate.py), which
carries the identical gap; a test pinning the fenced case; a test proving a genuine mislabelled link
outside any fence is still reported. If the decision instead is to leave the behaviour alone, record
that in this file's decision log with its reasoning and close the task without a code change: the
undocumented seam is the defect either way.

**Out of scope:** `broken_links()`, which is unaffected for the reason `bug-0015` recorded, that a
dangling target inside a code span is still a dangling target worth knowing about; full CommonMark
parsing; the third copy of the link rule inlined in `.github/workflows/checks.yml`, which is
`chore-0029`; the cross-line inline seam, which `bug-0015` recorded as deliberate.

## Implementation notes

**Fences are cheaper than inline spans, not harder.** A fence is a line-level construct: a line whose
first non-whitespace run is three or more backticks opens one, and a line whose run is at least as
long closes it. That is a single pass over lines and needs no interaction with the inline pairing
already there, so the two rules compose by union rather than by replacement.

**Preserve the direction of failure `bug-0015` chose.** Its risk section names over-skipping as the
costlier failure, because a disabled check reports success, and its guard test exists to make that
impossible to ship. An unterminated fence is the exact analogue of the unmatched backtick: prefer
treating it as opening nothing over letting it swallow the rest of the file. Extend the guard rather
than adding a parallel one.

**Keep the two copies in step**, which is the constraint `bug-0011`, `bug-0012`, and `bug-0015` each
honoured in turn: fixing this repository's validator while the template keeps shipping the gap is the
mistake all three avoided.

**This is the least urgent item in its priority band, and `P2` overstates it.** The scale runs `P0`
to `P2` with no lower rung, so `P2` is the floor rather than a judgement. No file in the tree
currently trips this, and the failure is a false positive on a construct authors rarely combine with
path-shaped link text. It is filed because the analysis exists now and will be lost otherwise, not
because anything is broken today. Take it after `bug-0016`, `chore-0029`, `chore-0030`, and
`chore-0031`, all of which describe live problems.

## Decisions

- **Rejected: teaching `code_span_ranges()` to see fences.** A fence is line-level and an inline span
  is character-level, so folding them together would have meant one function with two scanners and a
  docstring that no longer described either. The fix is a separate `fenced_block_ranges()` pass whose
  ranges `mislabelled_links()` unions with the inline ones, which is the composition this file's
  implementation notes predicted and leaves `bug-0015`'s reasoning where a reader can still find it.
- **Seam: only backtick fences are recognised.** A tilde fence (`~~~`) and a four-space indented code
  block are both still invisible to this check, so a mislabelled link inside either is still reported.
  Left open deliberately rather than missed: neither form appears anywhere in this repository, and
  each one added is another construct that can swallow the file if its terminator is mis-parsed. The
  next author meeting one should treat it as the same union, not as a rewrite.
- **Seam: an unterminated fence opens nothing.** It contributes no range at all, so every link below
  a dangling fence is still checked. That is the direction of failure `bug-0015` chose for an
  unmatched backtick run, kept here for the same reason: a detector that ran an unclosed fence to end
  of file would disable the check for the rest of the file and report success.
- **False premise: the two copies were never character-identical in `mislabelled_links()`.** This
  file's acceptance criteria assume they were. At `4777a59` the docstrings of both `mislabelled_links()`
  and `broken_links()` already diverged, deliberately, because the template is retargeted so it never
  names this repository ("the repository this scaffold came from" rather than `.tasks/README.md`).
  What is identical, and what this task kept identical, is the executable code of both functions plus
  every module-level regex. Read the criterion as covering the code, not the prose, or the only way to
  satisfy it is to import this kit's voice into every scaffolded repository.

## Risks and rollback

Required: this touches more than one module (both validator copies plus tests), and it changes what a
shipped scaffold emits.

The failure that costs most is the one `bug-0015` named: a fence detector that treats an unterminated
opening fence as running to end of file switches the check off for everything after it, and reports
success while doing so. Mitigate by extending the existing guard test so a genuine mislabelled link
outside any fence is still reported in a file that also contains a fence.

Rollback is one revert. The change adds a skip condition and writes no persisted format.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python .tasks/validate.py --strict

- [x] A test proving a mislabelled link inside a fenced code block is not reported, failing against
      the current validator.
- [x] A test proving a genuine mislabelled link **outside** any fence is still reported in a file
      that also contains a fenced block, so the fix cannot pass by disabling the check.
- [x] A test covering an unterminated fence, proving it does not suppress findings after it.
- [x] The same skip exists in the template validator, and the two copies remain character-identical
      in `mislabelled_links()`, `code_span_ranges()`, and their module-level regexes.
- [x] Existing tests still pass, unchanged in intent.
- [x] Either the behaviour changed, or a decision not to change it is recorded in this file with its
      reasoning.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason.
- [x] File moved to `.tasks/done/`, `status: done`, **with its relative links re-anchored for the
      extra directory level**; one dated line added to `CHANGELOG.md` referencing this task id.
