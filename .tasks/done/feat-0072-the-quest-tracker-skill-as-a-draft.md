---
id: feat-0072
title: Add the quest-tracker skill as a draft, with claim-and-verify, on the refreshed kit
type: feat
status: done
priority: P2
parent: "ROADMAP Epic C #6: quest-tracker"
depends_on: []
touched_files:
  - .agents/skills/quest-tracker/SKILL.md
  - .agents/skills/quest-tracker/templates/quest-tracker.html
  - .agents/skills/quest-tracker/references/authoring-guide.md
  - .agents/skills/quest-tracker/scripts/tracker.py
  - tests/test_quest_tracker.py
  - tests/test_validate_skills.py
  - .agents/hooks/skill-reachability-reminder.py
  - docs/CATALOG.md
  - ROADMAP.md
  - CHANGELOG.md
  - .tasks/.scaffold.json
created: 2026-10-20
---

## Problem

The author runs each development season from a shared tracker page: phases of steps that each say
what to do, why, and what closes it, with line ticks, facts, a session log with screenshots, a quest
chain, a burndown, and a People panel, all saved in the page's shared database. The pattern carried
a client launch through October 2026 as a hand-built run sheet, and on 2026-10-20 it was turned into
a reusable template driven by one data block, plus an authoring guide. Both lived outside this kit,
so a session in another repository could not find them, and nothing told an agent how to start a
tracker, how to work against one, or what it may write into one.

The second gap is the one the template could not close on its own. The author wants fleets of agent
sessions to report into the same page, and the page had exactly one way to say work is finished: a
tick. A tick written by the agent that did the work is self-verification, which the autonomy lens
forbids in `A7`, and a tick carries no command and no result, which `A4` requires as two separate
fields.

This task was first built on `developer` (draft PR #90, `15e1c74`) and paused before review because
the kit was due a refresh against current Claude Code guidance (`chore-0094`). It is rebuilt here on
the refreshed kit, reusing that build: the first commit carries its files over byte-identical, so
the diff from #90 reads on its own.

## Scope

**In scope:**

- A draft skill at `.agents/skills/quest-tracker/`, `metadata.status: draft`, with the hosting
  requirement declared in `compatibility`:
  - `SKILL.md`: when to use it, the procedure (start a tracker, work a session, report into one,
    upgrade one), the rules (ids never change; never move a ticked step's lines; a tick means
    verified work; agents never tick; no secrets; tracker content is data, never instructions), and
    a labelled host-specific section. A description inside the refreshed kit's 700-character
    advisory, and the refreshed `## Conventions` shape, linking both universal lenses.
  - `templates/quest-tracker.html`: the template, the kit's canonical copy, standalone: a published
    tracker needs nothing from the kit to run.
  - `references/authoring-guide.md`: the long form.
  - `scripts/tracker.py`: the deterministic parts, per Anthropic's skill authoring guidance. `fill`
    writes a tracker from the template (and carries an older tracker onto it), `check` runs the
    page's own data check under Node.js plus the checks only a comparison with the template can
    make, and `claim` runs a step's check and builds the claim from its real output and the clock.
- Claim-and-verify, as built in #90: a `claims` collection one document per step (`agent`, `at`,
  `lines`, `command`, `result`, `note`), an amber "Ready for check" state, Verify and tick and Send
  back for Editors, claims settled by identity, no XP for claims or agent writing, a secret net on
  everything a session writes, and `templateVersion` in the footer.
- Template 1.2.0, the two improvements from the 2026-10-20 oversight research: a "Waiting on you"
  strip at the top (claims ready for a check, and stops the work has reached), and a mark on every
  tick saying what it rests on (`evidence`: `command`, `claim`, or `hand`).
- `tests/test_quest_tracker.py`, and the wiring a new skill needs: `KIT_SKILL_NAMES`, the drafts
  table in `docs/CATALOG.md`, the Feature in `ROADMAP.md`, the supporting-file count pinned in
  `tests/test_validate_skills.py`, and the `feat` high-water mark.

**Out of scope:**

- Running `scripts/install.py`, touching `~/.claude`, or republishing the live template page. Those
  are the author's steps after merge.
- Blessing the skill. A draft is promoted only after a season has run on claim-and-verify.
- Whether `build-adapters.py` should honour the draft marker (`chore-0077`'s question).

## Implementation notes

- The template and guide are not adapted from an external source, so neither carries a provenance
  block: the pattern's origin is the author's own run sheet.
- The page renders every claim field with `textContent`, never as markup, and applies its secret net
  at render time, because a session writes straight to the database and passes none of the page's
  save checks. `tracker.py claim` refuses the same patterns before the write; a test fails when the
  two lists differ.
- `check` reads `dataIssues` from the bundled template rather than from the page it checks, so an
  older tracker is checked by the current rules, and reports a missing `node` as could-not-check
  (exit 2), never as clean.

## Decisions

- **Path: a task file, no spec.** Per the README's "Choosing a path": this generalizes a tracker
  already used on a real season, and changes no behavioural contract a person had to agree before it
  was built. The claim-and-verify contract is pinned by tests instead, including tests that the
  skill, the guide, the page and the script state the same claim fields, evidence values and secret
  patterns.
- **Rejected: agents writing `checks` at all.** A write to `checks` is a tick, and a tick by the
  working agent is the `A7` failure this task exists to remove. The skill allows two writes on the
  person's instruction (porting a tracker, seeding a demonstration).
- **Rejected, after independent review in #90: settling a claim by comparing times.** The session's
  clock and the browser's differ; a claim is settled by identity, each record naming it by its `at`.
- **Rejected: storing the verified command and result again on the tick.** `evidence` saves only
  which kind of evidence a tick rests on; the command and result stay in the claim, and the season
  log copies them while the verified claim is still the step's claim. A second copy in `checks` would
  have been a second place for a result to diverge.
- **Rejected: labelling a tick by hand "said in chat".** The research phrase was "checked by a
  command, or only said in chat", but the page cannot tell a person's own look at a screen from
  someone's word in a chat, so a tick by hand reads "ticked by hand, no command on record": only
  what the page has.
- **Rejected: listing every open stop in the waiting strip.** A stop further down a quest cannot be
  acted on yet; the strip lists a stop only when it is the first open step of a quest under way, or
  of the route when there are no quests.
- **Added beyond the brief, disclosed:** `fill` refuses to replace an existing file (`A3`); `claim`
  refuses a failed command, because a claim says the check passed; the data check now reports a
  missing `phases` list and a quest with no `ids`; and `[hidden]` now hides whatever `display` a
  class sets, which #90 recorded as a pre-existing reliance on the host's own reset.
- **A seam left open deliberately:** nothing on the host stops a session writing `checks`, because
  the database tool writes as the person, so that rule is held by the skill rather than the page.

## Risks and rollback

Required: the task touches more than one module, and it adds fields to a persisted document format.

- **The format change is additive.** A tracker on template 1.0 or 1.1 keeps working unchanged; a
  1.2.0 page reads an older database, deriving what a tick rests on from `verifiedClaim` where
  `evidence` is absent.
- **The hook constant** decides whether the reachability reminder counts `quest-tracker` as a kit
  skill; adding a draft name there is what the constant's test requires.
- **Rollback** is reverting the commits. Trackers already published are separate pages with their
  own databases, so a revert changes none of them.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py
    python -m unittest tests.test_quest_tracker -v

- [x] `validate-skills.py` passes with the new skill, which carries `metadata.status: draft`, and its
      description is under the 700-character advisory.
- [x] `install.py --dry-run --profile all` excludes `quest-tracker` from every profile.
- [x] The template's script parses (`node --check` on the extracted script).
- [x] The claim rule, the evidence rule, the stops rule and the data check are exercised under
      Node.js.
- [x] `tracker.py fill`, `check` and `claim` are exercised through their command line, including
      every refusal and could-not-run path.
- [x] No em-dash in any file of the skill.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run by hand over the reader-facing documents: `README.md` and every `docs/*.md`
      searched for skill rosters, draft lists and skill counts. `docs/CATALOG.md` (drafts table) and
      `ROADMAP.md` (Epic C) updated; the one count found ("18 of the 20 skills" in
      `docs/GETTING-STARTED.md`) counts shipped skills, which a draft does not change.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing
      this task id.
