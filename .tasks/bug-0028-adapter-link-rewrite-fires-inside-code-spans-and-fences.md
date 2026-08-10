---
id: bug-0028
title: The adapter link rewriter repoints links inside code spans and fences, silently, in every generated adapter
type: bug
status: open
priority: P2
parent: "ROADMAP Epic A: distribution tooling"
depends_on: []
spec: "docs/spec/build-adapters.md"
scenarios: ["S-003", "S-004", "S-005", "S-006", "S-007", "S-008"]
touched_files:
  - scripts/build-adapters.py
  - tests/test_build_adapters.py
created: 2026-08-10
---

## Problem

`rewrite_links()` in [`build-adapters.py`](../scripts/build-adapters.py) matches every markdown link
in a skill body with a bare `LINK_RE` and repoints it, with no notion of a code span or a fenced
block. So a skill that *shows* a link as an example, rather than making one, has that example
rewritten in each generated adapter: `](../doc-revise/SKILL.md)` inside a fence becomes
`](doc-revise.mdc)` in the Cursor tree and something else again in the plugin tree. The body says one
thing in the kit and a different thing everywhere it ships.

This is the same class as [`bug-0027`](done/bug-0027-skill-lint-fires-inside-fenced-blocks.md), which
closed the gap in `validate-skills.py`, and that task recorded this one as a seam rather than fixing
it: a different file, a different rule, and honestly its own task.

**It is the more dangerous half of the pair, which is why it is filed rather than left as a note.**
`bug-0027` was a false error: loud, in the way, and impossible to miss. This one changes shipped
output and says nothing. Nothing fails, no gate reports it, and the reader who eventually notices is
someone reading an adapter in another repository wondering why a documented example points at a file
that is not there. `SECURITY.md` names "anything that silently does nothing while reporting success"
as a real finding, and silently doing the *wrong* thing while reporting success is the same family.

**It is latent today and reachable tomorrow.** No shipped skill currently writes a link inside a
fence, and until `bug-0027` landed no skill could: the lint refused such a body outright, so this
code path was unreachable by construction. Fixing the lint is exactly what makes this reachable. The
documentation skills (`doc-author`, `doc-revise`, `doc-sync`) are the likeliest first authors of a
fenced example link, because showing markdown is what they are about.

## Scope

**In scope:** teach `rewrite_links()` the same exclusion `check_links()` learned in `bug-0027` and
`broken_links()` learned in [`bug-0023`](done/bug-0023-broken-links-fires-inside-code-spans-and-fences.md).
A link whose opening bracket falls inside an inline code span or a fenced block is emitted unchanged,
exactly as an anchor or an external URL already is.

**Out of scope:**

- `validate-skills.py` and `.tasks/validate.py`. Both already have the rule; this task is the third
  tool, not a revision of the first two.
- Deduplicating the range-finding code across the three tools. `bug-0027` decided deliberately to
  copy rather than import, because the validators have separate lifecycles and one ships as a
  template into other repositories. That decision is not reopened here, and the fourth copy is the
  cost it accepted.
- Amending the contract. See the implementation notes: whether this needs a new scenario is a
  question for the author, not a change to make while fixing the code.

## Implementation notes

`code_span_ranges()` and `fenced_block_ranges()` already exist in `scripts/validate-skills.py`, put
there by `bug-0027`, which took them from `.tasks/validate.py`. Mirror that, and keep the two
module-level regexes character-identical to the originals for the same reason `bug-0027` did: so the
copies can be diffed when the rule next changes.

Compute the ranges once per body rather than once per link. `bug-0023` made exactly that change in
`broken_links()` and the note is worth carrying, since `rewrite_links()` runs inside a `re.sub()`
callback where the naive placement is per match.

**The contract question, which is the author's and not the implementer's.** `docs/spec/build-adapters.md`
carries six scenarios governing this function, `S-003` through `S-008`, and none of them says
anything about a link that is not really a link. `S-008` is the closest: "external and same-page
links are emitted unchanged". The fix arguably wants an `S-018` in the same shape, and every
amendment in this repository so far records the author's explicit instruction. Record the divergence
in `## Decisions` and leave the spec alone unless instructed, which is what `bug-0027` did with its
own `S-009` divergence.

**One thing to check rather than assume**: `rewrite_links()` is not the only consumer of `LINK_RE` in
that file. Confirm whether the same blindness affects anything else there before deciding the fix is
one function wide.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] A link inside a fenced block is emitted byte-identical in every target's adapter.
- [ ] A link inside a single-backtick and a double-backtick inline span is likewise unchanged.
- [ ] A real relative link outside any span or fence is still rewritten exactly as `S-003` through
      `S-008` require, proved by the existing tests still passing unchanged in intent.
- [ ] An unterminated fence suppresses nothing after it, matching the trade `bug-0015`, `bug-0017`,
      `bug-0023`, and `bug-0027` all made, because a detector that ran to end of file would disable
      the rewrite for the rest of the body and report success.
- [ ] The new tests fail against the unchanged `build-adapters.py`, shown rather than asserted.
- [ ] Existing tests still pass.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
