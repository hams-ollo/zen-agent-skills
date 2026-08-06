---
id: chore-0028
title: Run review-depth through Anthropic's reference validator, which has never seen it
type: chore
status: done
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - .agents/skills/review-depth/SKILL.md
  - docs/ARCHITECTURE.md
created: 2026-08-05
---

## Problem

[`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md) carries this repository's sharpest recorded lesson:
three separate defects shipped in the `description` field over two days, each passing all four gates,
an approved contract, and a clean conformance matrix, because the kit's own regex parser and its own
spec agreed with each other and both disagreed with the schema. None was found from inside. They were
found by running external implementations over the real tree, and the conclusion drawn was that where
a tool reimplements an external standard rather than calling it, conforming to the spec is not
evidence of conforming to the standard.

That external run happened on 2026-07-29 against **19 skills**. `review-depth` was authored on
2026-07-31 and blessed on 2026-08-05, so it is the twentieth skill and **has never been through
Anthropic's `quick_validate.py`**. It passes this repository's own `validate-skills.py`, which is
precisely the evidence the lesson above says is insufficient.

Found while closing [`feat-0035`](feat-0035-draft-review-depth.md). The blessing went ahead
because the gap is narrow and the skill is prose rather than a schema-heavy surface, but updating
`ARCHITECTURE.md`'s claim from "all nineteen pass both" to "all twenty" would have been manufacturing
evidence for a check nobody ran. The sentence was date-anchored to its real measurement instead, and
it now names this task.

## Scope

**In scope:**

- Obtain `quick_validate.py` from Anthropic's official `skill-creator` plugin, the same source the
  2026-07-29 run used, and run it across all 20 skills.
- Fix whatever it reports on `review-depth`, or record that it reports nothing.
- Re-anchor the `ARCHITECTURE.md` sentence to the new run: its date, its count, and its result.
- Decide and record whether this check should be repeatable rather than occasional. It is currently
  a thing someone remembers to do, which is the state the `description` defects were found in.

**Out of scope:**

- Vendoring `quick_validate.py` into this repository. It is Anthropic's, it moves, and a stale copy
  reintroduces exactly the failure this task exists to prevent: a local reimplementation agreeing
  with itself. If a repeatable check is wanted, fetch it at run time or call it from CI, and decide
  that as part of the work above.
- Adding it to required CI in this task. It needs the network and an external artifact, and a check
  that fails when a download is slow gets disabled. Same reasoning as `feat-0043`.
- Re-validating the other 19. They passed on 2026-07-29 and nothing has edited their frontmatter
  since; if the run is cheap, include them and say so, but do not make that the task.

## Implementation notes

The `bug-0008` closeout in [`CHANGELOG.md`](../../CHANGELOG.md) records how the last run was done and
what it caught (`human-handoff`'s description contained `<name>` twice, which the schema rejects
outright, 18 of 19 passing). Read that entry before starting; it names the two schema rules
`validate-skills.py` now enforces as errors and why `version` is deliberately excluded from the
allow-list.

`review-depth`'s description is long. Check it against the harness limit as well as the schema, since
description length was one of the three original defects and `install.py`'s budget report is the
in-repository proxy for it.

## Decisions

- **Rejected: making this check repeatable by automating it.** Both available forms of automation
  defeat the reason the check exists. Vendoring `quick_validate.py` turns Anthropic's validator into
  a local copy that ages into exactly the self-agreeing reimplementation the 2026-07-29 lesson is
  about, so it would pass while the real schema moved. Putting it in required CI makes a gate depend
  on the network and on an artifact this repository does not own, and a gate that fails when a
  download is slow gets disabled, which is worse than no gate because the disabling is invisible.
  Same reasoning as `feat-0043`.
- **Seam left open deliberately: the check stays human-triggered, and the trigger moved from memory
  to a dated claim.** What was fixed is not the running but the forgetting. The `ARCHITECTURE.md`
  sentence now carries the date and the count of the last external run, so it goes visibly stale the
  moment a twenty-first skill is added: the prompt to re-run is a number in a document that no longer
  matches the tree, which a person can check in one glance without the network. Re-running it is one
  subprocess per skill directory (`for d in .agents/skills/*/; do python <path>/quick_validate.py
  "$d"; done`, fetching the file from the official `skill-creator` plugin first), which took under a
  minute across all twenty here. A future task may still want an optional, non-required CI job; this
  one deliberately does not add one.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py && python -m unittest discover -s tests -p "test_*.py"

- [x] `quick_validate.py` has been run across all 20 skills, with the date and the exact result
      recorded in the task closeout.
- [x] Anything it reports on `review-depth` is fixed, or recorded as accepted with a stated reason.
- [x] The `ARCHITECTURE.md` sentence names the new date, count, and result, and no longer points at
      this task as outstanding.
- [x] A decision is recorded either way on whether the check becomes repeatable, with reasoning.
- [x] `scripts/validate-skills.py` still exits 0 with no new errors or warnings.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
