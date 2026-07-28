---
id: bug-0005
title: Trim the five skill descriptions that exceed the 1024-character harness limit
type: bug
status: done
priority: P0
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - .agents/skills/agent-handoff/SKILL.md
  - .agents/skills/doc-revise/SKILL.md
  - .agents/skills/init-worktracking/SKILL.md
  - .agents/skills/human-handoff/SKILL.md
  - .agents/skills/doc-author/SKILL.md
created: 2026-07-28
---

## Problem

Five shipped skills carry a `description` longer than 1024 characters, which is the hard upper bound
both harnesses [`install.py`](../../scripts/install.py) targets enforce on that field. Measured with the
same parser [`validate-skills.py`](../../scripts/validate-skills.py) uses:

| Skill | Length | Over by |
|---|---|---|
| `agent-handoff` | 1104 | 80 |
| `doc-revise` | 1088 | 64 |
| `init-worktracking` | 1067 | 43 |
| `human-handoff` | 1066 | 42 |
| `doc-author` | 1049 | 25 |

All five are the older folded-prose descriptions carrying long trigger-phrase lists. Every skill
authored later, including all eight of the Epic B spine, is comfortably under.

The `description` is the only field an agent reads before deciding whether to load a skill, so a field
the harness rejects or truncates is a routing failure, not a cosmetic one, and it fails in the
direction that is hardest to notice: the skill simply never fires.

Two aggravating facts. `validate-skills.py` has a `MIN_DESC_CHARS` floor and no ceiling, so the one
command that exists to catch this class of defect cannot see it (`feat-0032` closes that, and depends
on this task landing first so the new error does not fire on the tree it is added to). And the 19
descriptions total 15,109 characters, all of which compete for the routing budget shared with every
other skill an adopter has installed, so length here is a cost paid by every skill in the kit at once.

## Scope

**In scope:** shorten each of the five `description` fields to 1024 characters or fewer, preserving
the trigger phrases and the sibling-redirect clauses, and cutting prose that restates the body.

**Out of scope:** any change to a skill's body, procedure, or `name`. Any change to the other fourteen
descriptions, which are already under. Adding the validator ceiling, which is `feat-0032`.

## Implementation notes

- **Cut restated body prose, not routing signal.** The description competes for a shared budget and is
  read before the body loads; anything it says about *how* the skill works is read twice by an agent
  that loads the skill and wasted on every agent that does not. What must survive: what the skill does
  in one or two clauses, the trigger phrases, and the "use X instead" redirect, which is what keeps the
  four documentation and handoff skills from firing on each other's work.
- Where three trigger phrases say the same thing in different words (`agent-handoff` has "draft me a
  prompt to trigger a new session", "prompt optimized to trigger a new session", and "craft a prompt I
  can paste into a new session"), keep the distinct phrasings and drop the near-duplicates. Distinct
  wording is what widens matching; a synonym of a phrase already present adds cost and no reach.
- Keep a capability list where it is itself routing signal. `doc-author`'s list of document kinds
  (deployment guide, ADR, architecture doc) is how a request for one of those finds the skill, so
  compress it rather than deleting it. `doc-revise`'s capability list is different: every item in it is
  already restated in its own trigger list, so it is pure duplication.
- **Four of the five are YAML block scalars (`>-`) folded across 13 to 14 lines; `init-worktracking`
  is a single plain line.** Preserve each one's existing form. Note that `validate-skills.py` currently
  counts the `>- ` indicator as three characters of description content, so its reported number for
  those four runs 3 higher than a YAML parser's. `feat-0032` fixes that. To stay green under both the
  buggy and the fixed measurement, land these at 1021 or fewer as the current validator reports them.
- Report the before and after count for each of the five.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [x] All five descriptions are 1024 characters or fewer under `validate-skills.py`'s own parser.
- [x] No description falls below `MIN_DESC_CHARS`, and none loses its trigger-phrase list.
- [x] Each of the five keeps its "use `<sibling>` instead" redirect clause.
- [x] Every sibling skill named in a description still exists in the kit.
- [x] No skill body, `name`, or file other than the five named is changed.
- [x] `python scripts/validate-skills.py` exits 0 with 19 skills, 0 errors, 0 warnings.
- [x] `python scripts/build-adapters.py --dry-run` exits 0 with 38 adapter files.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in the `AGENTS.md` conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.

## Outcome (2026-07-28)

All five are under, with margin. Counts are as `validate-skills.py` reports them, with the real
(YAML-parsed) figure alongside, since `feat-0032` closed the three-character gap between them:

| Skill | Before | After | Real | Cut |
|---|---|---|---|---|
| `agent-handoff` | 1104 | 856 | 853 | 248 |
| `doc-revise` | 1088 | 945 | 942 | 143 |
| `init-worktracking` | 1067 | 874 | 874 | 193 |
| `human-handoff` | 1066 | 923 | 920 | 143 |
| `doc-author` | 1049 | 941 | 938 | 108 |

The kit's total real description budget went from 15,109 to 14,262 characters across 19 skills. Every
trigger-phrase list and every sibling redirect survived; what came out was prose restating the body,
plus one near-duplicate trigger in `agent-handoff` where three phrasings said the same thing.

**Two defects were found in the descriptions while editing them, and both were fixed here because the
edit already touched the exact string.** Neither was in the task's scope as written.

`human-handoff`'s description said "a fresh Claude Code session". That is the harness lock-in in the
kit's most visible field that `chore-0009` was filed to remove, and it removed it from `agent-handoff`
only: the sibling instance survived three days in the field the portability contract cares about most.
It now reads "a fresh agent session". Worth noting as a pattern rather than a one-off, since a hardening
task that fixes one instance of a defect class and leaves its twin is how this kit has been bitten
before.

`init-worktracking`'s description used a spaced hyphen doing em-dash duty ("into the current repository
- AGENTS.md"), against the house style. It is now a colon.

The measurement discrepancy in the implementation notes resolved cleanly: the reported "before" numbers
in the Problem table are the validator's, which ran 3 high for the four block scalars. `feat-0032` fixed
the parser, so the two measurements now agree and the "After" and "Real" columns differ only for the
four skills that use a block scalar.
