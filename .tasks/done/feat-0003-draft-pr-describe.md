---
id: feat-0003
title: Draft the first version of the pr-describe skill
type: feat
status: done
priority: P1
parent: "ROADMAP Epic A #2 pr-describe"
depends_on: []
touched_files:
  - .agents/skills/pr-describe/SKILL.md
created: 2026-07-24
---

## Problem

The kit ships the front half of the work spine, `project-bootstrap` -> `init-worktracking`
-> `new-task`, but nothing to help *close out* a change. When a branch is ready, the user
still hand-writes the PR description and the matching `CHANGELOG.md` line, by re-reading
their own diff. `pr-describe` (ROADMAP Epic A #2) fills that gap: given the current branch,
it turns the diff into a structured PR body and a changelog entry in the target repo's own
format, so the PR and the ledger come out of one pass and stay in sync.

## Scope

**In scope:** author `.agents/skills/pr-describe/SKILL.md` as a harness-agnostic,
agent-executed procedure that:

1. determines the diff range (current branch vs its merge-base with the default branch) and
   surveys the change;
2. drafts a structured PR body grounded only in what the diff supports;
3. drafts a changelog entry adapted to the repo's existing `CHANGELOG.md` conventions,
   referencing task ids when the `.tasks/` system is present;
4. outputs both as text and surfaces the `gh` command, writing/creating nothing on GitHub.

First draft only.

**Out of scope:** calling `gh` or creating/editing any PR; a large per-repo template
library; blessing the skill (it stays a draft in `ROADMAP.md`/`docs/CATALOG.md` until
iterated on real PRs); building `code-review` or any later skill; changing this kit's own
`CHANGELOG.md` conventions.

## Implementation notes

Settled design decisions (resolved with the author; do not re-litigate in the draft):

- **Produces both** a PR body and a changelog entry from the same diff analysis.
- **Draft text only, never touches GitHub.** It prints/writes the text and surfaces
  `gh pr create` / `gh pr edit --body-file` for the user to run. Safe with or without `gh`
  installed. This mirrors `project-bootstrap`'s configs-only, no-surprise-side-effects rule.
- **Changelog format by inspection.** Read the target repo's `CHANGELOG.md` and match its
  heading/date/id style; fall back to Keep a Changelog when none exists. Mirrors
  `init-worktracking`'s seed-by-inspection principle; do not hardcode this kit's task-log
  line into a portable skill.
- **Default diff range = current branch vs merge-base with the default branch** (the PR's
  actual commit range), with an explicit base/range override. Detect the default branch
  robustly (`git symbolic-ref refs/remotes/origin/HEAD`, fall back to `main`/`master`);
  compute the base with `git merge-base`.

Shape and rigor:

- Mirror the existing skills (`init-worktracking`, `project-bootstrap`): survey first,
  portable, cross-platform (`pathlib`, no POSIX assumptions), agent-executed prose rather
  than a Python script.
- When the `.tasks/` system is present, detect task ids from the branch name/commit
  messages and reference them in the changelog entry (this kit links `feat-NNNN`).
- PR body sections should be adapted to what the diff supports (summary, context/motivation,
  what changed grouped logically, verification/testing, follow-ups), never fabricated.
- The frontmatter `description` must say both what and when and be a little pushy, so
  `scripts/validate-skills.py` passes and the skill triggers reliably.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [ ] `.agents/skills/pr-describe/SKILL.md` exists with valid frontmatter (`name` matches
      directory, non-thin `description`).
- [ ] `scripts/validate-skills.py` exits 0 with the new skill present.
- [ ] Body is under the 500-line progressive-disclosure guideline.
- [ ] SKILL.md documents all four settled decisions above, including the never-touch-GitHub
      rule and the by-inspection changelog behavior.

## Definition of done

- [ ] Acceptance command passes locally.
- [ ] Conventions in AGENTS.md section 6 followed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
- [ ] Skill left as a draft; `ROADMAP.md`/`docs/CATALOG.md` still mark `pr-describe` as
      planned/draft pending field iteration.
