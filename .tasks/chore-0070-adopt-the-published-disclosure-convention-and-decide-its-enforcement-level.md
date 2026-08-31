---
id: chore-0070
title: Progressive disclosure is published guidance this kit already follows by accident, guarded by a warning that cannot fail and unenforced in two other respects
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - AGENTS.md
  - scripts/validate-skills.py
  - tests/test_validate_skills.py
created: 2026-08-27
---

## Problem

**This task was revised on 2026-08-27, the day it was filed, because its original framing was wrong.**
It asked which of two conventions this kit has, `references/` or single-file, and treated the answer as
an open judgment. Anthropic has published the answer, and the first version of this task did not know
that because it was written from the engineering blog, which omits the rule, rather than from the
documentation, which states it. The original framing is recorded here rather than deleted, because a
task whose premise moved is exactly the thing this repository asks agents to disclose.

**What the guidance actually says**, from
`platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices`:

```text
"Keep SKILL.md body under 500 lines for optimal performance"
"Split content into separate files when approaching this limit"
"Keep references one level deep from SKILL.md"
"For reference files longer than 100 lines, include a table of contents at the top"
```

The 500-line rule appears three times: in the progressive-disclosure section, under "Token budgets", and
in the shipping checklist. **`MAX_BODY_LINES = 500` in [`validate-skills.py`](../scripts/validate-skills.py)
is that exact number**, so the kit tracked the guidance rather than inventing a threshold.

The reference-depth rule carries a mechanical reason worth quoting, because it is not a matter of taste:

> "Claude may partially read files when they're referenced from other referenced files. When encountering
> nested references, Claude might use commands like `head -100` to preview content rather than reading
> entire files, resulting in incomplete information."

**So the convention is settled and three things about its enforcement are not.** Measured across the
twenty skills on 2026-08-27:

| Published rule | Enforced here | State of the tree |
|---|---|---|
| Body under 500 lines | **warning only** | 0 violations; `fix-batch` at 463 |
| References one level deep from `SKILL.md` | **not checked** | 0 violations |
| Table of contents on references over 100 lines | **not checked** | 0 violations |

The body-length branch appends to `warnings`, not `errors`, and the function ends
`return 1 if errors else 0`, so a skill over 500 lines prints a line and passes the gate. It has never
fired: `python scripts/validate-skills.py | grep -c WARN` returns 0.

That makes it an instance of the sentence `chore-0063` put into `AGENTS.md` the same morning: **a check
that cannot fail is unchecked, whatever it printed.** And two published rules beside it are not checked
at all, so the tree passing them today is luck rather than a guarantee.

## Scope

**In scope:** adopt the published convention explicitly, and settle how the three rules are enforced.

- **State the convention in `AGENTS.md`** as this kit's, citing the guidance rather than asserting it.
  The layout section already lists `references/` among a skill's optional directories; what is missing is
  the rule about when to use it and how deep it may go.
- **Decide the enforcement level for the body-length rule**, and record the rejected option. Error,
  warning-with-a-stated-reason, or removal. **A warning kept by default is the current state and is not an
  outcome.** Note that an error would fail nothing today, since the tree is clean, which makes this
  cheaper to decide now than after a skill crosses the line.
- **Add checks for the two unenforced rules**: reference depth, and a table of contents on references over
  100 lines. Both are decidable from the filesystem, so both can be real checks rather than advice.
- **One worked example, only if the enforcement decision needs it.** `fix-batch` at 463 lines is the
  obvious candidate and the only skill within 40 lines of the limit; `review-depth` at 352 and `doc-sync`
  at 305 are next. **Splitting a skill is not required by this task** and should happen only if the
  decision makes it necessary.

**Out of scope:**

- **The body-shape rule and the lens list**, which are
  [`chore-0069`](done/chore-0069-the-two-body-shapes-rule-is-wrong-on-its-own-list-and-nothing-checks-it.md).
  **That task touches the same three files as this one, so the two cannot share a wave.**
- The third-person description rule, which is a published, mechanically-checkable rule that nothing here
  enforces either. It belongs with a description-focused pass rather than a disclosure-focused one.
  **Report it as a finding rather than folding it in.**
- The 1,024-character description ceiling, already enforced as an error.
- Splitting more than one skill. A sweep is a different task with its own evidence.

## Implementation notes

**One check could still overturn the convention, so run it first.** If a `references/` file does not
survive the inlining adapter targets, then single-file is a constraint here rather than a preference, and
the published guidance cannot be adopted as written. `build-adapters.py` inlines a body for the `cursor`
and `vscode` targets, and `chore-0036` added supporting-file link checking for markdown shipped beside a
`SKILL.md`. **Emit all four distribution paths and look**, rather than reading the code and inferring.
`chore-0062` did exactly this for the lens-link question on 2026-08-27 and found five emitted directories
where it expected four.

The two new checks have close prior art in the same module: `check_supporting_files()` and
`classify_supporting_file()`, added by `chore-0036`, already walk the files beside a `SKILL.md`. Reference
depth is a path-parts count from the skill root; the table-of-contents rule is a scan of the first lines
of a file over a length threshold. Neither needs a new walker.

On the enforcement decision, the honest asymmetry is worth stating in the closeout: this repository has
been burned by warnings nobody reads, and the counter-argument is that a hard error on a guideline whose
own source calls it "for optimal performance" is stricter than the guidance. Both are real. Pick one and
say which.

## Risks and rollback

Three files including the canonical rules document, so this section is required.

The risk is adopting a rule as an error and discovering the emitted adapter trees cannot satisfy it. The
distribution check above is the guard, and it comes first for that reason.

A second risk is scope creep into splitting skills. The convention can be adopted and enforced without
restructuring anything, because the tree is already clean against all three rules.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] `AGENTS.md` states the disclosure convention, including the one-level-deep rule and the reason for
      it, cited rather than asserted.
- [ ] `validate-skills.py` checks reference depth, proven by a test that nests a reference two levels and
      asserts the run reports it.
- [ ] `validate-skills.py` checks for a table of contents on references over 100 lines, proven by a test.
- [ ] The body-length rule sits at a decided enforcement level, and the closeout records the rejected
      option with its reasoning.
- [ ] The closeout states whether a `references/` file survives all four distribution paths, established
      by emitting them rather than by reading the code.
- [ ] The closeout reports how many skills each new check flags on the current tree, as numbers.
- [ ] No skill body is split unless the enforcement decision required it, and if one was, the closeout
      says why.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
