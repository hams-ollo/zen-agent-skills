---
id: bug-0037
title: A conformance matrix cites evidence by line number, so an unrelated prose edit above it silently makes the citation point at something else
type: bug
status: open
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: [chore-0046]
spec: "docs/spec/cloud-executable.md"
touched_files:
  - docs/spec/cloud-executable.conformance.md
  - docs/spec/house-review.conformance.md
created: 2026-08-20
---

## Problem

[`cloud-executable.conformance.md`](../docs/spec/cloud-executable.conformance.md) cites its evidence
by line number, 39 times. [`chore-0046`](done/chore-0046-write-conformance-into-the-closeout-lifecycle.md)
added two lines to `AGENTS.md` and shifted everything below them, so two of those citations now point
at unrelated text. Measured 2026-08-20 in that task's own worktree:

```text
matrix cites  AGENTS.md:117        -> now "[.github/workflows/checks.yml] calls this same s..."
matrix cites  AGENTS.md:107-117    -> 107 is now "- **Python** (tooling under scripts/...)"
the cited run-checks.py content    -> actually at AGENTS.md:112 and :115
```

**Nothing reported it and nothing could.** All seven gates pass, because the tests guarding those
claims match on content rather than on line number, and the doc-link checker resolves paths rather
than line anchors. So a matrix, whose entire purpose is to be the evidence a scenario was met, can
point somewhere else without any gate noticing. That is the failure signature this repository names
as its own enemy, occurring inside the artifact the repository uses to prove things.

`chore-0046`'s agent found it, correctly declined to fix it (a matrix is outside a task whose
`touched_files` is `AGENTS.md`, and editing an audit is the audit owner's job), and reported it.

The scope is smaller than it first looks, which is why this is a bug rather than a convention
project. Counted across all eleven matrices: **40 line-number citations in total, 39 of them in
`cloud-executable.conformance.md` and 1 in `house-review.conformance.md`**. Every other matrix
already cites by symbol, quoted text, or test name. So the practice is the exception, not the house
style, and correcting two files brings the set into line rather than inventing a new rule.

## Scope

**In scope:** replace line-number citations with references that survive an edit above them, in the
two matrices that use them, and repair the two that are already wrong.

- Cite the enclosing section heading, the symbol, or a short quoted phrase, whichever the row is
  actually about. Match what the other nine matrices already do rather than inventing a form.
- Re-derive each of the 40 against the current files rather than adjusting the numbers, since a
  citation that was already stale before this wave would otherwise be preserved with a new number.

**Out of scope:**

- The contracts themselves. This changes how a matrix points at evidence, not what any scenario says,
  so no spec is amended and no re-approval row is needed.
- Any file under `scripts/` or `tests/`. The tests already match on content, which is why they did
  not break; that behaviour is correct and stays.
- Adding a gate that checks citations. Worth considering later and not now: a checker for "does this
  quoted phrase still appear in that file" is a real tool with real false-positive risk, and it should
  not be designed inside a bug fix. If the re-derivation turns up more stale rows than the two known
  ones, say so in the closeout, because that count is the argument for or against building it.
- `.tasks/` files and the CHANGELOG, which cite by task id and are unaffected.

## Implementation notes

Do the re-derivation by reading each cited file, not by counting the shift. `chore-0046` moved
`AGENTS.md` by two lines, but that number explains only these two rows; the other 38 have their own
histories and at least some were written weeks ago against files that have changed since.

Prefer the shortest reference that is unambiguous. A section heading is stable across edits within
the section; a symbol name is stable across edits anywhere in the file; a quoted phrase is the most
precise and the most brittle, so use it where the row is about specific wording, which several of the
`cloud-executable` rows genuinely are.

`depends_on: [chore-0046]` is logical, not a file collision: that task is what shifted the lines, and
re-deriving before it lands would produce citations that are stale on arrival.

## Risks and rollback

Two documents and no code, so the more-than-one-module rule does not fire.

The real risk is silent incompleteness: re-deriving 40 citations by hand and getting 38 right leaves
two wrong rows in a document nobody will re-check for months, which is the same state as today with
more confidence attached. State in the closeout how many were re-derived and how many were found
already stale, so the result is a count rather than an assurance.

Reversible by reverting one commit. Nothing depends on the citation form.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] No conformance matrix cites evidence by line number: `grep -ohE '[A-Za-z0-9_./-]+\.(md|py|json|mjs|yml):[0-9]+' docs/spec/*.conformance.md` returns nothing.
- [ ] Every replaced citation was re-derived against the current file, and the closeout states how
      many of the 40 were found already stale.
- [ ] The two known-wrong rows, `AGENTS.md:117` and `AGENTS.md:107-117`, point at the content they
      claim.
- [ ] No spec file is modified and no re-approval row is added.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
