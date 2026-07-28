---
title: tracker-links
status: approved
---

# tracker-links

Behavioral contract for linking a task file to an upstream GitHub issue, and for carrying that link
into the pull request description so merging the pull request closes the issue.

Drafted 2026-07-28 by `spec-author`, whose `spec-quality` self-check returned `needs_revision` on
the first draft and was revised to `ready`. Approved by the author on 2026-07-28, together with the
decision recorded in S-009.

## Problem

The kit's work tracking is entirely local. A task file in [`.tasks/`](../../.tasks/) has an id, a
parent, and acceptance criteria, and none of that is visible to anyone who has not cloned the
repository. A team planning a sprint, assigning work, or reporting progress works in an issue
tracker instead, so today the two halves cannot see each other: the tracker does not know a task
exists, and the task does not know which tracker item it serves.

Closing the loop by hand is the part that decays. Someone opens a pull request, merges it, and the
issue stays open until a human remembers, which means tracker state drifts from reality in the
direction that looks like progress has already been reported.

GitHub already solves this if the right text reaches the right place: a closing keyword in a pull
request description links the issue and closes it on merge. What makes it worth specifying is that
the rules are narrow and every violation fails silently, producing a pull request that looks
correct, merges cleanly, and leaves the tracker wrong.

[`pr-describe`](../../.agents/skills/pr-describe/SKILL.md) already drafts the pull request body and
already reads the `.tasks/` system to reference the work item, so it is the one place in the spine
that holds both halves at once.

## Goals

1. Let a task file name the upstream GitHub issue it serves, in a form that survives review and can
   be read without interpretation.
2. Emit a closing reference in the pull request description, so merging closes the linked issue
   without anyone remembering to.
3. Never emit a reference that will silently fail to close.
4. Reject a malformed reference before it reaches a pull request body.

## Non-Goals

- **Azure DevOps, and every other tracker.** Deferred to the roadmap until one has been used on
  real work, per the kit's contribution bar.
- **Creating, editing, closing, assigning, or reading the state of any issue.** `pr-describe`
  drafts text and does not touch GitHub, and this contract does not change that.
- **Verifying that a referenced issue exists.** That would require a network call from a skill whose
  settled design is to make none.
- **Bidirectional synchronization**, or any mirroring of task files into issues.
- **Issue hierarchy**: sub-issues, parents, issue types, and dependencies.
- **Making the link mandatory.** A task without an upstream issue stays valid.

## Constraints

- GitHub honors a closing keyword only in the pull request description, and only when the pull
  request targets the repository's default branch.
- A single keyword closes only the first issue that follows it, so a reference to several issues
  must repeat the keyword for each.
- Each of those failures is silent. Nothing reports them, so the contract has to prevent them rather
  than detect them afterwards.
- The task file is the source of truth for the link. Nothing reads it back from GitHub.

## Scenarios

### Scenario S-001: a linked task produces a closing reference in the description

- **Given** a task file whose `external` value is `#123`, and a branch whose pull request targets
  the default branch
- **When** the pull request body is drafted
- **Then** the body contains the line `Closes #123`, within the description rather than the title.

### Scenario S-002: several linked tasks each get their own keyword

- **Given** a branch closing three tasks, each with its own `external` value
- **When** the pull request body is drafted
- **Then** each of the three references is preceded by its own `Closes`, rather than one `Closes`
  followed by a list of three.

### Scenario S-003: a task with no upstream reference produces none

- **Given** a task file with no `external` value
- **When** the pull request body is drafted
- **Then** no closing reference is emitted for it, and the run reports no problem.

### Scenario S-004: a non-default base links without closing, and says why

- **Given** a task whose `external` value is `#123`, and a pull request targeting a branch other
  than the repository's default
- **When** the pull request body is drafted
- **Then** the body contains `#123` with no closing keyword before it, and the output states that
  GitHub will not close the issue on merge because the target is not the default branch.

### Scenario S-005: a cross-repository reference is carried through unchanged

- **Given** a task whose `external` value is `owner/repo#123`
- **When** the pull request body is drafted
- **Then** the body contains `Closes owner/repo#123`, with the owner and repository preserved rather
  than reduced to `#123`.

### Scenario S-006: the reference never appears in the title

- **Given** any task with an `external` value
- **When** the pull request body and title are drafted
- **Then** the title contains no issue reference, because GitHub ignores one there.

### Scenario S-007: a malformed reference fails validation

- **Given** a task file whose `external` value is neither `#<digits>` nor `<owner>/<repo>#<digits>`
- **When** the backlog is validated
- **Then** validation fails, naming the task file and the offending value, and exits non-zero.

### Scenario S-008: an absent reference is valid

- **Given** a task file with no `external` key at all
- **When** the backlog is validated
- **Then** validation passes, because the link is optional.

### Scenario S-009: a task completed in the same change still gets a reference

- **Given** a task whose `external` value is `#123`, whose file the branch moves from `.tasks/` to
  `.tasks/done/`
- **When** the pull request body is drafted
- **Then** the body contains `Closes #123`, the same as for a task still open, because the pull
  request is what completes the work.

## Proposed Surface

| Element | Detail |
|---|---|
| `external` | Optional task frontmatter field holding one GitHub issue reference |
| Reference form | GitHub's own syntax, stored verbatim: `#123` for this repository, `owner/repo#123` for another |
| Keyword | `Closes`, one per reference |
| Pull request body | One `Closes <reference>` per linked task, in the description |
| Non-default base | Reference emitted with no keyword, plus a stated reason |
| Validation | A present `external` value must match a recognized reference form; absence is valid |

## Open Questions

None. The one question this spec carried, whether a task moved to `.tasks/done/` in the same change
still gets a reference, was decided yes on 2026-07-28 and is now S-009.
