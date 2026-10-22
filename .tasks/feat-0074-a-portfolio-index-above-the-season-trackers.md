---
id: feat-0074
title: Give a person running several season trackers one index page saying which project needs them this week
type: feat
status: open
priority: P2
parent: "ROADMAP Epic C #6: quest-tracker"
depends_on: []
touched_files:
  - .agents/skills/quest-tracker/SKILL.md
  - .agents/skills/quest-tracker/scripts/tracker.py
  - .agents/skills/quest-tracker/references/authoring-guide.md
  - .agents/skills/quest-tracker/templates/quest-tracker.html
  - tests/test_quest_tracker.py
  - ROADMAP.md
created: 2026-10-22
---

## Problem

The [`quest-tracker`](../.agents/skills/quest-tracker/SKILL.md) skill runs one season of one
project from one shared page. Its template already answers "what waits on you" for that page,
through the waiting strip added in template 1.2.0. A person running several projects at once has
one tracker per project and no page that answers the question one level up: across all of them,
which project needs me this week, and for what.

- **The first-party views are per tool, not per portfolio.** As read 2026-10-20:
  - Claude Code's agent view lists background sessions across projects, with a "Needs input"
    group and pull request status ([agent view](https://code.claude.com/docs/en/agent-view)).
  - Claude Code Projects shows threads waiting on you in an Overview pane
    ([Projects](https://code.claude.com/docs/en/claude-projects)).
  - Neither knows about a season, its quests, or its blockers.
- **The kit's own boards are per repository.** sitrep is "a board for one repository", and ROADMAP
  Epic E #7d places a view across several repositories in `agent-observatory`'s scope selector,
  as a later amendment. A season tracker is neither: one season can span several repositories,
  and its blockers and waiting items live in the page's own database, not in git.

## Scope

**In scope:**
- **An index format and a way to build it.** A person, or an agent closing a session, can produce
  one page listing every active tracker. Each row gives the project, the tracker's link, the
  current quest, the count of open blockers, what waits on the person (the same items the
  tracker's waiting strip shows), and when the tracker last changed. Rows that wait on the person
  sort first.
- **The deterministic part as a stdlib `tracker.py` subcommand**, for example `index`, matching the
  existing `fill`, `check` and `claim`. It renders the index from a small JSON list the agent
  assembles by reading each tracker with the host's tools.
- **New files**, created at:
  - `.agents/skills/quest-tracker/templates/portfolio-index.html` for the page;
  - `.agents/skills/quest-tracker/references/portfolio-index.md`, if the procedure needs more than
    a section of the existing authoring guide.
- **A procedure step in `SKILL.md`** saying when to refresh the index: at session close, after the
  tracker's own close step.

**Out of scope:**
- Reading trackers without the host's tools.
- A cross-repository git view, which belongs to `agent-observatory` per Epic E #7d.
- Changing the tracker template's data block.
- Any real project's data in the kit.

## Implementation notes

- **Ship placeholder data only.** The kit is public, and template 1.2.1 already removed a client's
  name and private page links (PR #95). The bundled index template carries placeholder rows, and
  `test_no_file_of_the_skill_links_a_private_page` in `tests/test_quest_tracker.py` must keep
  passing. It fails on any `claude.ai/artifact/` link in the skill's files, including a new
  template's.
- **The index is a view.** It never becomes a second place where a tick, a blocker or a claim is
  recorded. Every figure on it links to the tracker it came from.
- **Mirror the existing subcommands** for argument style, exit codes and the stdlib-only rule in
  [`AGENTS.md`](../AGENTS.md)'s conventions section.
- **Shares touched files with `feat-0075`.** Do not dispatch both in one `fix-batch` wave.

## Open question

1. **Does a portfolio view of trackers belong here, beside Epic E #7d's planned cross-repository
   view in `agent-observatory`?** The recommendation is yes, as a separate thing, because a season
   tracker spans repositories and keeps its state outside git. Each row links to the repository's
   board where one exists, rather than duplicating it. If this is accepted, add one sentence to
   ROADMAP Epic C #6 saying so.
2. **Is the index its own page, or a section added to every tracker?** The recommendation is its
   own page. A section on each tracker would repeat every other project's state on every page.

## Decision

Answered by Hamsa on 2026-10-22:

1. **Yes: the index belongs in `quest-tracker`, separate from Epic E #7d's planned cross-repository
   view in `agent-observatory`.** Each row links to the repository's board where one exists. ROADMAP
   Epic C #6 now carries a sentence saying so.
2. **The index is its own page,** not a section on each tracker.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_quest_tracker.py" -v
    python scripts/run-checks.py

- [ ] `tracker.py index` on a fixture list of three trackers renders all three rows in the stated
      order, with rows that wait on the person first, and exits 0.
- [ ] A malformed list entry yields a named error and a non-zero exit, and writes no page.
- [ ] Every row on the rendered page links to its tracker's address from the input.
- [ ] The bundled index template contains placeholder data only, and
      `test_no_file_of_the_skill_links_a_private_page` passes with the new files in place.
- [ ] `SKILL.md` names the refresh step, and stays under the 500-line body guidance.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
