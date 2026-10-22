---
id: feat-0073
title: List the tasks an agent can start now, and mark a dispatched task so no second session starts it
type: feat
status: open
priority: P2
parent: "ROADMAP Epic E #7d: project board"
depends_on: []
touched_files:
  - .tasks/validate.py
  - .agents/skills/init-worktracking/templates/validate.py
  - .agents/skills/fix-batch/SKILL.md
  - .agents/skills/sitrep/scripts/sitrep.py
  - tests/test_tasks_validate.py
  - tests/test_sitrep_board.py
  - .tasks/README.md
  - .agents/skills/init-worktracking/templates/tasks-README.md.tmpl
created: 2026-10-22
---

## Problem

The kit answers "what exists" and "what is blocked", but nothing answers "what can an agent start
right now", which is the question a dispatcher and a fresh session ask first.

- **The rule exists, but nothing applies it on request.** The lifecycle in
  [`AGENTS.md`](../AGENTS.md) says a task is dispatchable once every id in its `depends_on` is in
  `done/`. [`validate.py`](validate.py) checks that every edge resolves and that no ring closes,
  and its own docstring for `dependency_cycles` notes that a ring's only symptom is "a person
  noticing that a batch has nothing ready". It never lists what is ready.
- **The closest thing is sitrep's board.** `classify()` in
  [`sitrep.py`](../.agents/skills/sitrep/scripts/sitrep.py) already splits open tasks into
  waiting on the person, blocked, and `planned`. But sitrep is a draft, personal, user-scope skill,
  so it is not what `fix-batch` or an adopter's agent can rely on.
- **Nothing marks a task as taken.** `status: in_progress` exists in the schema
  ([`.tasks/README.md`](README.md)), but sitrep's own notes record that no task file in the
  author's repositories sets it. Two sessions picking from the same backlog have no signal that the
  other already started.

Prior art, read 2026-10-20:
- Steve Yegge's Beads answers this with `bd ready` (tasks with no open blockers) and an atomic
  `bd update <id> --claim` ([README](https://github.com/gastownhall/beads)).
- Claude Code's agent teams keep a shared task list in which a pending task with unresolved
  dependencies cannot be claimed, and claiming takes a file lock
  ([agent teams docs](https://code.claude.com/docs/en/agent-teams)).

## Scope

**In scope:**
- **A ready listing.** It names every open task whose `depends_on` ids are all in `done/`, that
  carries no unanswered open question, and whose status is not `in_progress`, ordered by priority.
  It is human-readable by default and has a JSON form for agents.
- **The same listing in the shipped template copy** of `validate.py`, so adopters get it.
- **Taking a task on dispatch.** `fix-batch` sets `status: in_progress` on each task it dispatches,
  in the dispatch commit, and the ready listing then excludes it.
- **One test that checks the ready listing and sitrep agree.** On the same fixture backlog, the
  ready set equals sitrep's `planned` set minus tasks in progress.
- **Documentation** of the listing in both `.tasks/README.md` copies.

**Out of scope:**
- A new frontmatter field for who took a task (see the open question).
- Any locking or database.
- Changing sitrep's board output.
- The cross-repository view, which ROADMAP Epic E #7d places in `agent-observatory`'s scope
  selector.

## Implementation notes

- Reuse the dependency and open-question logic rather than writing a third copy of it. sitrep
  detects an unanswered open question positionally: a `## Open question` heading with no
  `## Decision` heading below it. The ready listing must agree with that rule.
- The two `validate.py` copies already differ, and `chore-0059` tracks a rule copied across files
  with nothing checking that the copies match. Do not add another such pair: whatever the listing
  adds to one copy it adds to both, and a test runs the same fixture through each.
- A take that is only committed in a worktree is invisible to the main checkout until it lands.
  That is why the dispatcher, the one process that sees the whole batch, sets `in_progress` before
  dispatch, rather than each agent setting it on itself.
- The open question below makes this task show as waiting on the person in sitrep. That is
  intended.

## Decisions

- **A rejected alternative: adopting Beads itself.** It would add a Dolt database and a second
  tracker beside `.tasks/` and the quest tracker, the drift problem in reverse. The idea is
  borrowed; the tool is not.

## Open question

1. **Where should the ready listing live?** The recommended home is `validate.py` as a `--ready`
   flag, in both copies. It ships to every adopter through `init-worktracking`, and it is already
   the backlog gate in [`run-checks.py`](../scripts/run-checks.py). `fix-batch` would then call
   it when choosing a batch, which its procedure does not do today. The alternative is sitrep's
   JSON output, which would make the listing depend on a draft, user-scope skill and on
   `feat-0070`.
2. **Is `status: in_progress` set by the dispatcher enough, or is a field naming who took the task
   needed?** The recommendation is that it is enough. A new field changes the persisted format,
   and between worktrees it still cannot be atomic. Avoid the word "claim" for this either way: in
   the `quest-tracker` skill a claim already means an agent's report of finished work awaiting a
   person's check.

## Risks and rollback

This task touches more than one module (both `validate.py` copies, `fix-batch`, and sitrep's
tests), so the rule fires.
- **What could go wrong:** the two copies drift, or `fix-batch` marks a task `in_progress` and then
  fails before dispatch, leaving it hidden from the ready listing.
- **The mitigation:** dispatch must reset the status when it aborts, and that reset is tested.
- **Rollback:** revert the commit. No persisted format changes if open question 2 is answered as
  recommended.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_tasks_validate.py" -v
    python -m unittest discover -s tests -p "test_sitrep_board.py" -v
    python scripts/run-checks.py

- [ ] A fixture backlog with a done dependency, an open dependency, an unanswered open question, an
      answered one, and a task in progress yields exactly the expected ready set, in priority
      order, in both the text and the JSON forms.
- [ ] The same fixture gives the same result through the template copy of `validate.py`.
- [ ] On that fixture, the ready set equals sitrep's `planned` set minus tasks in progress.
- [ ] `fix-batch`'s procedure states that it sets `status: in_progress` in the dispatch commit, and
      resets it when dispatch aborts.
- [ ] Both `.tasks/README.md` copies document the listing.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
