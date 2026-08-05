---
id: bug-0014
title: An applied doc-sync correction can break a relative link, and nothing checks it
type: bug
status: open
priority: P1
parent: "ROADMAP Epic B #9: doc-sync"
depends_on: []
spec: docs/spec/doc-sync.md
scenarios: ["S-011"]
touched_files:
  - .agents/skills/doc-sync/SKILL.md
  - docs/spec/doc-sync.conformance.md
created: 2026-08-05
---

## Problem

Scenario `S-011` in [`doc-sync.md`](../docs/spec/doc-sync.md) requires three things of an applied
correction. The edit must change only the drifted claim, leave the surrounding text and the
document's voice intact, and:

> every relative link in the edited document still resolves to a file that exists.

The first two are delegated to [`doc-revise`](../.agents/skills/doc-revise/SKILL.md), correctly:
`doc-sync` step 5 composes it and says "Its discipline governs: do not restate its rules here."
**The third is delegated nowhere.** It is not one of `doc-revise`'s rules, so the composition drops
it, and no clause in either skill instructs a post-edit link check. Found by the `chore-0025`
conformance audit and recorded as the one `to-fix` row in
[`doc-sync.conformance.md`](../docs/spec/doc-sync.conformance.md).

**This is not a wording quibble.** The failure it guards against has already happened here at scale:
`bug-0011` found 101 broken relative links across 36 completed task files, produced by exactly this
class of unchecked edit, with `validate.py --strict` and the CI docs link step both reporting
success because neither looked in the right place. An agent correcting a stale claim is a
plausible way to produce the same defect: rewriting a sentence that contains an inline link, or
correcting a path that appears both as prose and as a link target, changes a live affordance a
reader clicks.

It is also the cheapest possible gap to close, because the tooling already exists. `.tasks/validate.py`
resolves every relative link against the directory the file actually lives in, and the CI step does
the same for root, `.github/`, and `docs/`.

## Scope

**In scope:** add the missing obligation to [`doc-sync`](../.agents/skills/doc-sync/SKILL.md) step 5,
so an applied edit is followed by a link re-check on the edited document, and a link the edit broke
is repaired or the edit is reverted rather than left. Then update the `S-011` row and the
unreconciled set in [`doc-sync.conformance.md`](../docs/spec/doc-sync.conformance.md) to match.

**Out of scope:**

- Changing `doc-revise`. The obligation belongs to the skill that applies a mechanical correction,
  not to the general-purpose editing skill, and pushing it down would make every `doc-revise` run
  carry a check most of them do not need.
- The `skipped` versus `not_audited` divergence in the same matrix. That one is the contract lagging
  the implementation and is `chore-0027`.
- Building a new link checker. Use what `.tasks/validate.py` and the CI step already do.
- Auditing whether past `doc-sync` runs broke any links. `chore-0006` is the only run that applied
  anything; check it if cheap, but do not make this task a sweep.

## Implementation notes

Prefer naming the check over describing it. "Re-check the edited document's relative links" is an
instruction an agent can skip without noticing; pointing at the command that already does it is not.

Consider where the check belongs among step 5's four bullets. It has to come after the write and
before the applied record is emitted, because an applied entry claiming a correction that broke a
link is a worse record than no entry.

The related open work is [`bug-0013`](bug-0013-validator-rejects-file-scheme-links.md), which fixes
those same checkers rejecting `file://` links. The two do not conflict, but a fix here that leans on
the checker inherits whatever `bug-0013` has not yet repaired, so land `bug-0013` first if both are
in flight.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py && python .tasks/validate.py --strict && python -m unittest discover -s tests -p "test_*.py" -v

- [ ] `doc-sync` step 5 states the post-edit link obligation and names the mechanism that satisfies
      it, rather than describing it in the abstract.
- [ ] The instruction states what to do when the check fails (repair or revert), not only that the
      check happens.
- [ ] `doc-sync.conformance.md` `S-011` moves from `Diverged` to `Conformed`, with the new clause
      cited as evidence.
- [ ] The unreconciled set in that matrix drops the `to-fix` row and its count is corrected.
- [ ] No change to `doc-revise`.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
