---
title: sitrep
status: draft
---

# sitrep

Behavioral contract for the sitrep: a personal board generated from a repository's own records, with
an evidence tier on every figure, placed into the person's local sessions when they start. Drafted
2026-09-11 by the `spec-author` skill for Hans Havlik, and self-checked to `ready` with the
`spec-quality` lens. A forward spec: nothing implements it yet.

## Problem

Agent sessions produce work faster than the person directing them can hold its state, and that state
is written down in several places that disagree: task files, the roadmap, the changelog, dated status
documents and published pages. On 2026-09-10, in the `hts-app` repository, a remaining-work figure of
`1,085` sat in several documents while the tool that computes it reported `1,088`.

A status report written from memory is wrong in both directions, and nothing marks which way. The same
day, a hand-written founder queue listed three items and called them the whole list. Reading the task
files found eight, five of them unanswered open questions that no session had surfaced.

Every figure in prose looks equally solid. In one week of planning, four quoted figures were wrong and
read exactly like the right ones: a simulator result quoted as `74` that is about `75` give or take two
across seeds, a run count roughly doubled by counting entries instead of runs, a threshold called
unmeasured that had been measured against 172 items, and a diagnosis built on two mistyped field names
that each returned empty and were read as absence. An untracked local file looks like state too: a
simulator output left in `hts-app`'s `content-engine/out/` reported 70 skills mastered where a fresh
run reported 74.

A prototype in `hts-app` (`scripts/status-page.mjs`, tasks `feat-0059` and `feat-0060`, now parked in
its own draft pull request) showed that deriving the board from the repository works, and how it goes
wrong. It dropped the only P1 from the queue, because it counted a task as answered when a decision
existed anywhere in the file, including above a newer question. It reported nothing in progress while a
worktree held uncommitted work, because no task file ever says `in_progress`. It cleared the person's
"since you last looked" marker whenever any session started. And it drew a blocked count in green.

This kit already reports what agents did, across every project, in
[`agent-observatory`](agent-observatory.md), and Claude Code's Agent View (Anthropic) lists which
sessions are running. Neither says what is true about the work, what is waiting on the person, or how
far to trust a number.

## Goals

1. Generate a board for one repository from its own tracked records, showing what waits on the person,
   what is blocked, what is in flight, and what changed since the person last caught up.
2. Give every figure on the board an evidence tier derived from where the figure came from, never
   higher than its source supports.
3. Place a short sitrep into the person's local interactive sessions when they start, leading with what
   waits on the person, without ever blocking the session or recording a hook failure.
4. Tell every such session how the person expects to be reported to.
5. Keep a "last caught up" watermark that belongs to the person and moves only when they reply.
6. Render the board as a page on two colour axes that never share a role: gear-rarity colours for
   evidence tier, and red, amber, green and grey for status.
7. Produce a board for any git repository, including one with no task tracking.
8. Emit the board as one versioned machine-readable document, so that a later cross-project view reads
   boards rather than re-deriving them.
9. Reach only a person who installed it.

## Non-Goals

- Reporting what agents did, which skills ran, what anything cost, or run health. That is
  `agent-observatory`.
- Listing which sessions are running or waiting for input. That is Claude Code's Agent View.
- A view across every repository at once. The intended home is a later amendment to
  `agent-observatory`; this spec only makes the board readable for it (Goal 8).
- Cloud sessions. Decided by Hans Havlik on 2026-09-11: local sessions first, cloud once proven.
- Blocking anything: no CI gate, no refused commit, no refused session. Decided by Hans Havlik on
  2026-09-11: display only.
- A status line, whose rendering in the Claude desktop app is unverified.
- Session-start registration for any harness other than Claude Code. The board itself runs anywhere
  Python does.
- Pull request state, or anything else that needs a network service. The board reads the local clone
  only; an unmerged branch is visible there, and that is what in flight reports.
- Push notifications.
- Hand-written narrative inside the page.

## Constraints

- Standard-library Python only, running on Windows, macOS and Linux, per the conventions section of
  [`AGENTS.md`](../../AGENTS.md).
- Every hook honours the contract in [`.agents/hooks/README.md`](../../.agents/hooks/README.md) in the
  reminder shape. Its registration names the interpreter by the rule `hook_interpreter()` in
  [`install.py`](../../scripts/install.py) applies, never a bare `python3`, which on Windows is a
  Microsoft Store stub (`bug-0050`).
- Registration is at user scope only, printed by `install.py --with-hooks` for the person to place. No
  repository commits a sitrep registration.
- The skill enters the kit as a draft (`metadata.status: draft`), which `install.py` places under no
  profile until the author blesses it, per the contribution bar in `AGENTS.md` and `S-015` of
  [`install.md`](install.md).
- Task files are read in the format that
  [`init-worktracking`](../../.agents/skills/init-worktracking/SKILL.md) scaffolds: frontmatter `id`,
  `title`, `status`, `priority` and `depends_on`, with completed tasks under `.tasks/done/`.
- The tier ladder and the status meanings under Proposed Surface are the single definition. The rules
  module that restates them for agents uses the same names.

## Scenarios

### Scenario S-001: an open question with no decision below it waits on the person

- **Given** an open task file whose body has an `Open question` heading and no `Decision` heading
  anywhere below it
- **When** the board is generated
- **Then** the task is listed under waiting on you with the reason `open question`

### Scenario S-002: a decision above a newer question does not answer it

- **Given** an open task file whose body has a `Decision` heading and, below it, an `Open question`
  heading with no `Decision` heading after that
- **When** the board is generated
- **Then** the task is listed under waiting on you with the reason `open question`

### Scenario S-003: a decision below a question answers it

- **Given** an open task file whose `Open question` heading is followed, later in the body, by a
  `Decision` heading
- **When** the board is generated
- **Then** the task is not listed under waiting on you

### Scenario S-004: work held for a human eye waits on the person

- **Given** an open task file with a heading that contains the words `held open for a human eye`, in
  any letter case
- **When** the board is generated
- **Then** the task is listed under waiting on you with the reason `needs a human eye`

### Scenario S-005: a closed task never waits on the person

- **Given** a task file under `.tasks/done/` whose body has an `Open question` heading with no
  `Decision` heading below it
- **When** the board is generated
- **Then** the task is not listed under waiting on you

### Scenario S-006: waiting entries are ordered by priority

- **Given** tasks waiting on the person with different priorities, two of them sharing a priority
- **When** the board is generated
- **Then** waiting on you lists them from P1 downward, and the two with the same priority in id order

### Scenario S-007: a task with an unfinished dependency is blocked

- **Given** an open task whose `depends_on` names a task id that has no file under `.tasks/done/`
- **When** the board is generated
- **Then** blocked lists the task and names each dependency that is not done

### Scenario S-008: uncommitted work in a worktree is in flight

- **Given** a worktree of the repository with uncommitted changes, and no task file carrying
  `status: in_progress`
- **When** the board is generated
- **Then** in flight lists that worktree with its branch and the number of paths git reports as
  changed, carrying tier Purple

### Scenario S-009: a branch with unmerged commits is in flight

- **Given** a local branch holding commits that the integration branch does not contain
- **When** the board is generated
- **Then** in flight lists that branch with the number of those commits

### Scenario S-010: a repository without task tracking still gets a board

- **Given** a git repository with no `.tasks/` directory
- **When** the board is generated
- **Then** the board carries in flight and changed since you caught up, carries the notice
  `no task tracking`, and lists nothing under waiting on you or blocked

### Scenario S-011: changes since the watermark are summarised

- **Given** that since the watermark one task file moved into `.tasks/done/` and another task file
  changed in place
- **When** the board is generated
- **Then** changed since you caught up gives the number of commits since the watermark, lists the
  first task as closed and the second as updated

### Scenario S-012: a count over a tracked file is Purple

- **Given** a figure declared with kind `count` over a JSON file that git tracks
- **When** the board is generated
- **Then** the figure shows the number of elements its selection yields at the current revision,
  carries tier Purple, and names the file as its provenance

### Scenario S-013: a value read from a tracked file is Blue

- **Given** a figure declared with kind `value` over a JSON file that git tracks
- **When** the board is generated
- **Then** the figure shows the value at its selection, carries tier Blue, and names the file as its
  provenance

### Scenario S-014: a task entry is Green

- **Given** a task listed anywhere on the board
- **When** the board is generated
- **Then** its entry carries tier Green and names its task file as its provenance

### Scenario S-015: anything from an untracked file is White

- **Given** a figure declared over a file that git does not track, including one declared as a count
  or pinned to a test
- **When** the board is generated
- **Then** the figure carries tier White and is labelled `untracked`

### Scenario S-016: a pinned figure whose test exists is Gold

- **Given** a figure of kind `count` or `value` over a tracked file, pinned to a test name that a
  tracked test file contains
- **When** the board is generated
- **Then** the figure carries tier Gold and names the test

### Scenario S-017: a pinned figure whose test is missing is downgraded and reported

- **Given** a figure pinned to a test name that no tracked test file contains
- **When** the board is generated
- **Then** the figure carries the tier its source earns without the pin, and the board carries a
  notice naming the figure and the missing test

### Scenario S-018: a hand-entered value is White and shows who said so

- **Given** a value entered by hand in the repository's board configuration with a stated source
- **When** the board is generated
- **Then** the value carries tier White and shows its stated source

### Scenario S-019: a count of entries carries the tier of what it counts

- **Given** a count of board entries, such as the number waiting on you, whose entries do not all
  carry the same tier
- **When** the board is generated
- **Then** the count carries the lowest tier among the entries it counts

### Scenario S-020: a figure that cannot be read is a notice, not a guess

- **Given** a figure whose declared file is missing, is not JSON, or holds nothing at the declared
  selection
- **When** the board is generated
- **Then** the board shows no value for that figure and carries a notice naming the figure and what
  went wrong

### Scenario S-021: a first look covers the last seven days

- **Given** a person with no watermark for the repository
- **When** the board is generated
- **Then** changed since you caught up covers the commits on the current branch dated within the last
  seven days, and the watermark kind is `first-look`

### Scenario S-022: a reply moves the watermark to the revision the person was shown

- **Given** a session whose sitrep described revision A, and a commit B made after the sitrep was shown
- **When** the person sends a message in that session
- **Then** the person's watermark for the repository becomes A, the next board lists B under changed
  since you caught up with the watermark kind `caught-up`, and nothing inside the repository changes

### Scenario S-023: a session the person never writes in leaves the watermark alone

- **Given** a session that received a sitrep and in which the person sends no message, such as a
  background or sub-agent session
- **When** that session ends
- **Then** the person's watermark for the repository is what it was before the session started

### Scenario S-024: a watermark on a vanished commit resets to a first look

- **Given** a watermark naming a commit that the repository no longer contains
- **When** the board is generated
- **Then** changed since you caught up covers the last seven days, the watermark kind is `reset`, and
  the board carries the notice `watermark reset`

### Scenario S-025: each person has their own watermark

- **Given** two people who have each installed the sitrep and each have a watermark for the same
  repository
- **When** one of them sends a message after being shown a sitrep
- **Then** that person's watermark moves and the other person's is unchanged

### Scenario S-026: an explicit since leaves the watermark alone

- **Given** a person whose watermark for the repository is revision A
- **When** the board is generated with `--since B`
- **Then** changed since you caught up covers the commits since B, the watermark kind is `explicit`,
  and the person's stored watermark is still A afterwards

### Scenario S-027: a session opens with the sitrep, waiting on you first

- **Given** a person who installed the sitrep
- **When** they start a local interactive session inside a git repository, including a resume, a clear
  or a compaction
- **Then** the session's context contains the sitrep, with its sections in the order waiting on you,
  changed since you caught up, in flight, blocked, notices

### Scenario S-028: a long section is cut short and says how many more

- **Given** a sitrep section holding more entries than the display limit
- **When** the sitrep is produced
- **Then** the section shows its first entries in the section's order, up to the limit, and ends with
  a line giving how many more there are

### Scenario S-029: the session is told how the person expects to be reported to

- **Given** a person who installed the sitrep
- **When** a session starts inside a git repository
- **Then** the session's context carries the reporting rules listed under Proposed Surface, alongside
  the sitrep

### Scenario S-030: a sitrep that cannot be produced never stops the session

- **Given** a git repository in which the board cannot be produced, such as one holding a task file
  that cannot be read, or git itself failing
- **When** a session starts there
- **Then** the session start is not blocked, the session's transcript records no hook failure for
  it, and its context carries one line saying the sitrep could not be produced and why

### Scenario S-031: outside a git repository nothing is added

- **Given** a person who installed the sitrep
- **When** they start a session in a directory that is not inside a git repository
- **Then** nothing is added to the session's context, and the session's transcript records no hook
  failure

### Scenario S-032: a person who has not installed it sees nothing

- **Given** one person who installed the sitrep and another who did not, both working in the same
  repository
- **When** the second person starts a session there
- **Then** that session's context carries no sitrep and no reporting rules

### Scenario S-033: status and evidence never share a colour

- **Given** a board holding waiting, blocked, in-flight, closed and planned entries, and figures of
  every tier
- **When** the page is rendered
- **Then** waiting and blocked entries are marked red, in-flight amber, closed green and planned grey,
  each tier appears in its own rarity colour, and no status is marked with a tier colour nor any tier
  with a status colour

### Scenario S-034: every figure on the page shows its tier and provenance

- **Given** a board with figures of every tier
- **When** the page is rendered
- **Then** each figure shows its value, its tier by name and by colour, and its provenance

### Scenario S-035: the page is written only where asked

- **Given** a request for the page at a path
- **When** the page is rendered
- **Then** exactly one file is created or replaced, at that path

### Scenario S-036: generating a board changes nothing in the repository

- **Given** a repository with a clean or a dirty working tree
- **When** the board is generated as text, as a document, or as a page
- **Then** the working tree, the index, every ref and the history are unchanged, apart from the page
  file when the requested page path lies inside the repository

### Scenario S-037: the board needs no network

- **Given** a machine with no network connection
- **When** the board is generated
- **Then** the board is complete, and at no point does the sitrep open a network connection

### Scenario S-038: the board is available as one versioned document

- **Given** any git repository
- **When** the board is requested with `--json`
- **Then** the output is one JSON document carrying the schema version, the repository, the revision it
  describes, when it was generated, the watermark and its kind, and the same entries, figures, tiers
  and notices that the page shows

### Scenario S-039: a repository with no integration branch reports no branches and says so

- **Given** a repository whose board configuration declares no integration branch, with no remote named
  `origin` and no branch named `main`
- **When** the board is generated
- **Then** in flight lists no branches, still lists worktrees with uncommitted changes, and the board
  carries the notice `no integration branch`

## Proposed Surface

### Terms

| Term | Meaning |
|---|---|
| person | whoever installed the sitrep on this machine |
| local interactive session | a session the person started on their own machine and types into |
| repository | one clone, including every worktree of it |
| current branch | the branch checked out where the board is generated |
| board | everything the sitrep derives for one repository |
| sitrep | the board's short text form, added to a session's context |
| watermark | per person and per repository: the revision that person last caught up to, stored outside the repository |
| integration branch | the branch finished work merges into |
| tracked | held by git at the current revision |
| tracked test file | a tracked file whose name starts with `test_` or contains `.test.` or `_test.` |

### Command

| Invocation | Does | When omitted |
|---|---|---|
| `sitrep` | prints the sitrep as text | changed since uses the person's watermark |
| `sitrep --json` | prints the board as one JSON document | no document |
| `sitrep --html <path>` | writes the page to `<path>` and to nowhere else | no page is written |
| `sitrep --since <rev>` | uses `<rev>` for changed since, for this run only; the watermark does not move | the person's watermark |

### When it runs in a session (Claude Code)

| Moment | Effect |
|---|---|
| the session starts, resumes, is cleared, or is compacted | adds the sitrep and the reporting rules to the session's context |
| the person sends a message | moves that person's watermark for the repository to the revision the session's most recent sitrep described; adds nothing to the context |

### Sitrep sections

| Section | Holds | Order |
|---|---|---|
| waiting on you | tasks with an unanswered open question or held for a human eye, each with its reason | priority from P1, then id |
| changed since you caught up | the number of commits since the watermark, tasks closed, tasks updated | closed, then updated, each by id |
| in flight | worktrees with uncommitted changes, then branches with unmerged commits | worktrees first, then branches by most recent commit |
| blocked | open tasks with an unfinished dependency, naming it | priority from P1, then id |
| notices | what the sitrep could not do, and watermark resets | as they arise |

A heading counts as an `Open question` or a `Decision` heading when it is a level-two heading whose text
begins with those words. The display limit is five entries per section in the sitrep. The page and the
document carry every entry.

### Reporting rules carried into every session

1. Lead with what waits on the person.
2. Say what changed since they caught up, not what this session did.
3. Give every figure you state a tier from the ladder below. A figure stated without one reads as Gold.
4. Name what you are least sure about.

### Evidence tiers

The single definition. Each tier has one colour, following the gear-rarity ladder in increasing order,
in both the light and the dark theme.

| Tier | Assigned to |
|---|---|
| White | a figure over a file git does not track; a hand-entered value |
| Green | a task entry, read from a task file |
| Blue | a figure of kind `value` read from a tracked file |
| Purple | a figure of kind `count` computed over a tracked file; an entry read from git's current state |
| Gold | a Blue or Purple figure pinned to a test name that a tracked test file contains |

A count of entries carries the lowest tier among the entries it counts.

### Status

| Status | Colour | Marks |
|---|---|---|
| needs you | red | waiting on you, blocked |
| in progress | amber | in flight |
| done | green | tasks closed since the watermark |
| planned | grey | open tasks neither waiting nor blocked |

### Board document

| Field | Holds |
|---|---|
| `schema_version` | an integer, starting at 1 |
| `repository` | the repository's top-level path and the URL of its `origin` remote, if any |
| `revision` | the revision the board describes |
| `generated` | when the board was generated, in UTC, ISO 8601 |
| `watermark` | the revision changed since starts from, and its kind: `caught-up`, `first-look`, `reset` or `explicit` |
| `waiting`, `blocked`, `in_flight` | entries, each with its tier and provenance |
| `changed` | the number of commits, closed task ids, updated task ids |
| `figures` | each figure's name, value, tier and provenance |
| `notices` | one line each |

### Repository board configuration (optional)

Where it lives is Open Question 3. With none, the board is derived from task files and git alone.

| Field | Holds | When omitted |
|---|---|---|
| `integration_branch` | the branch finished work merges into | the default branch of the remote `origin`; otherwise `main`; if neither exists, no branches are reported and the board carries a notice |
| `figures` | each: `name`, `file` (a JSON file), `kind` (`count` or `value`), `select` (a dotted path to an array or a value, optionally with one `[field=value]` filter on an array) | no declared figures |
| `pins` | each: a figure name and a test name | no pins |
| `manual` | each: `name`, `value`, and `source` (who said so, and when) | no hand-entered values |

## Open Questions

1. **What is the skill called?** The working name is `sitrep` for the skill and its command, with
   "HUD" left as the name for the family of surfaces it feeds. Recommendation: keep `sitrep`. It says
   what the output is, and it does not collide with any skill in this kit or with Claude HUD, a
   separate community status-line plugin.
2. **Can a message from the person be told apart from a prompt no person typed?** `S-022` and
   `S-023` assume the harness distinguishes a person typing from a background, print-mode or
   sub-agent session, and nothing here has verified that it does. Recommendation: before this spec is
   decomposed, run a short spike that records what the harness reports for each kind of session. If
   they cannot be told apart, amend `S-022` so the watermark moves only on an explicit acknowledgement
   from the person, which Hans Havlik considered and ranked second on 2026-09-11.
3. **Where does a repository's board configuration live?** Either committed in the repository, or in
   the person's own configuration keyed by repository. Recommendation: committed in the repository. It
   describes that repository's own files and would drift from them if kept elsewhere, and it does
   nothing unless someone runs the sitrep. The cost is one extra file that a collaborator can see.
