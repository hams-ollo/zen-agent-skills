---
id: chore-0090
title: Every commit Copilot Autofix writes carries the AI co-author trailer AGENTS.md forbids, and three of them are on developer
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - AGENTS.md
  - CONTRIBUTING.md
  - .github/PULL_REQUEST_TEMPLATE.md
created: 2026-08-31
---

## Problem

The commit-message convention in [`AGENTS.md`](../AGENTS.md) forbids a `Co-Authored-By` trailer
naming an AI model, and the reason recorded there is mechanical rather than stylistic: the
`main protection` ruleset sets `require_extra_approval_for_unattributed_changes`, the sole human
here authors every pull request, and GitHub does not let an author approve their own pull request.
On 2026-08-21 that deadlocked a 68-commit sync, 44 of them carrying the trailer, and it took an
admin bypass to land.

The rule is written for agents. **GitHub Copilot Autofix is not one of the agents it reaches**, and
every commit it writes carries `Co-authored-by: Copilot Autofix powered by AI` by construction.

Observed on 2026-08-31: three such commits were pushed onto the branch of pull request 82 after it
was opened, merged with it, and are now ancestors of `developer`. Their ids are `9581809`,
`fe05847` and `dcd3d5b`.

**Their content was reverted and their history was not.** `developer` carries
`allow_force_pushes: false`, which refuses an admin as well, so the commits cannot be removed
without changing a protection setting. The content revert is
[pull request 83](https://github.com/hams-ollo/zen-agent-skills/pull/83).

**The cost is now smaller than `AGENTS.md` implies, and that is worth recording too.** The
`main protection` ruleset lists `RepositoryRole:always` as a bypass actor, which did not exist at
the time of the 2026-08-21 incident, so the deadlock is now a click rather than an ordeal. That
lowers the urgency; it does not make the rule inert, because the bypass is a manual step on every
affected sync and the whole point of the convention is that nobody should have to take one.

**What the three commits actually changed is the second half of the problem.** Two edited
`docs/reviews/2026-08-31-security-reliability-review.md`, an outside author's ledger of what they
ran and measured, and one set `scenarios: ["S-020"]` on a task whose spec has no `S-020`. So the
tool is not only writing forbidden trailers, it is editing document classes where an automated
correction is the wrong move: a ledger is `doc-sync`'s report-only class, and a `scenarios` field is
a pointer a readiness gate resolves.

## Scope

**In scope:** decide whether Copilot Autofix may commit to this repository, and write the decision
down where it will be found.

The decision belongs to the maintainer. Three shapes, to be chosen between rather than combined:

1. **Turn off its ability to auto-commit**, leaving it to comment or suggest. The setting lives in
   the repository's code-security configuration on GitHub, not in this tree, so this task records
   the decision and the fact that it was applied; it cannot assert it from a file.
2. **Keep it, and add the trailer to whatever the sync process already tolerates**, recording in
   `AGENTS.md` that Autofix is a known exception and that its commits are expected to need the
   bypass.
3. **Keep it, and add a gate** that fails when a commit in the range carries an AI co-author
   trailer, so the cost is paid at the pull request rather than at the sync.

Whichever is chosen, `AGENTS.md`'s commit-message section should say explicitly whether the rule
binds automated tooling as well as agents, since today it addresses agents and Autofix read as
outside it.

**Out of scope:**

- Rewriting `developer`'s history to remove the three commits. Refused by branch protection, and
  the content is already reverted.
- Changing the `main protection` ruleset, its bypass actors, or `developer`'s protection settings.
- Any general policy about other GitHub automation. This is about the one tool that has actually
  committed here.
- Re-litigating the trailer rule itself, which is settled and carries its own incident.

## Implementation notes

If shape 3 is chosen, note that the check cannot live in `run-checks.py` as it stands: that script
gates a working tree, and this is a property of a commit range. `.github/workflows/checks.yml` calls
`run-checks.py` rather than restating gates, per `chore-0029`, so a range check would be a second
job rather than a tenth gate, and that is a deliberate departure worth stating rather than sliding
into.

`AGENTS.md`'s commit-message section already names the three agent kinds it binds (an interactive
session, a worktree agent, a cloud session). Adding a fourth line is the smallest honest edit if
shape 1 or 2 is chosen.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] `AGENTS.md`'s commit-message section states whether the rule binds automated tooling, not only
      agents.
- [ ] The `## Decisions` section of this task records which of the three shapes was chosen and what
      was rejected, per the template's rejected-alternative rule.
- [ ] If shape 1 was chosen, the task records that the setting was changed and by whom, since no
      file in this tree can assert it.
- [ ] If shape 3 was chosen, the new check fails against a commit range containing one of the three
      named commits and passes against a range without one.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
