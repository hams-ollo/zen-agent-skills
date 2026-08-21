---
title: cloud-executable
status: approved
---

# cloud-executable

Behavioral contract for making this repository workable from a cloud agent session, written
2026-08-07 for item 2 of Epic E in [`ROADMAP.md`](../../ROADMAP.md). **Approved by the author on
2026-08-07.**

**Amended 2026-08-20 (`chore-0051`) to repoint `S-017` and `S-018` at an open task: their **Given**
clauses named [`bug-0018`](../../.tasks/done/bug-0018-reinstall-destroys-an-adopter-edited-lens.md),
which closed on 2026-08-08, one day after the runbook that dispatches it was written.** This
amendment is **pending the author's re-approval**. The contract specified a proof run that could not
be performed, and nothing reported it: all seven gates pass, and `validate.py --strict` passes because
the runbook's link to that task resolves correctly into `done/`, so the move made the link more valid
rather than less. The substitute is
[`bug-0020`](../../.tasks/done/bug-0020-check-unknown-remedy-is-wrong-for-the-adopted-lens.md), chosen
because `S-018`'s "the unfixed `install.py`" stays literally true of it and its first acceptance
criterion already requires a test failing against the current message. `status` is left reading
`approved` per the convention in [`README.md`](README.md), for the reason that file gives. Nothing
else in this contract changes, and `S-017` to `S-019` stay **Not-built**, since only the run itself
can move them.

A **forward** spec, and the first here: every other spec in this directory was written against code
that already existed, so it described a contract that already held. This one does not, which moves
where the risk sits. A retrospective spec can be wrong about what the code does, and an audit finds
that. A forward spec can specify something unbuildable, and nothing finds that until someone tries.
`spec-plan-readiness` over this spec plus its task decomposition is the gate for that, and it runs
before any implementation begins rather than after.

## Problem

This repository cannot be worked on from a cloud agent session, for two independent reasons. Both
fail silently, which is why a contract is worth writing before any of it is built.

**A cloud session sees only what is committed.** Nothing under `.claude/` is tracked here
(`git ls-files .claude` returns nothing), and [`install.py`](../../scripts/install.py) places skills
at user scope, under `~/.claude/skills` and `~/.agents/skills`. A cloud session clones the
repository and gets neither. It still starts, still reads `AGENTS.md`, and still does work, so the
repository that builds this kit is the one place the kit is reliably absent, and nothing anywhere
says so. The output looks like work done with the skills and is not.

**A cloud session cannot stop and ask.** Every check here that decides whether a change is
acceptable is either a person reading CI output or a person running seven commands by hand. The 97
acceptance chains across the backlog and its completed tasks run one, two, three, or five commands,
and none of them runs the seven gates in
[`checks.yml`](../../.github/workflows/checks.yml). An unattended agent has no way to
answer "is this acceptable" without a human, and no way to know that the three commands its task
file named are not the seven that gate the merge.

The two compound. A session without the skills produces work that only the missing skills would
have caught, and then has no command to catch it with either.

## Goals

1. One command, runnable with no human present, answers whether a change is acceptable here.
2. That command and CI cannot disagree about what the gates are.
3. The bound of that answer is stated where it will be read, so passing the command is never
   mistaken for passing CI.
4. A session that starts without the kit's skills reachable is told so, at the start, unprompted.
5. The bootstrap changes nothing, and stays silent when it has nothing to report.
6. The bootstrap behaves the same wherever it runs, with no detection of where that is.
7. Real backlog work lands through a cloud session under the autonomy ceiling, proved by an outcome
   the session could not have produced by claiming it.

## Non-Goals

- **Detecting whether a session is cloud-hosted.** There is no shared signal across the harnesses in
  scope, so detection would mean one implementation per harness for a single question, and the
  reachability answer is the same either way.
- **Installing, copying, updating, or repairing anything.** The bootstrap reports. Fixing an
  unreachable install is a person's decision, as it is for `install.py --check` and
  [`check-provenance.py`](../../scripts/check-provenance.py).
- **Answering whether an installed skill is still current.** That is `install.py --check`, which
  already exists.
- **Committing the repository-scope skill or adapter trees.** Whether `.claude/skills/`,
  `.cursor/rules/`, or `.github/prompts/` should be tracked here is held in Epic E with its own
  trigger. This contract defines how they are counted if they are present, and requires none of
  them to be.
- **Replacing, reducing, or reproducing the CI matrix.** The command is a single-cell check by
  construction.
- **Generalizing to any other repository.** That is the `cloud-ready` skill, Epic E item 4.
- **Scheduled or recurring unattended runs.** Held in Epic E until one manual session has landed.
- **Changing the autonomy ceiling.** Draft pull request, never merge, is fixed here.

## Constraints

- Standard library only, on Windows, macOS, and Linux, per the conventions section of
  [`AGENTS.md`](../../AGENTS.md).
- The bootstrap is a hook and inherits the module contract in
  [`.agents/hooks/README.md`](../../.agents/hooks/README.md): exit 0 always, at most one JSON object
  on stdout, never import from this repository, and expose an injectable `main(stdin, stdout)`.
- A hook registered in a repository-committed `.claude/settings.json` runs in a cloud session; one
  registered in a user-level `~/.claude/settings.json` does not. So the registration has to be
  committed for the hook to exist at all in the case it is written for. Anthropic's cloud-session
  documentation states the same thing from the other direction: to change settings for a cloud
  session, commit settings files to the repository.
- `SessionStart` carries a `source` field whose values are `startup`, `resume`, `clear`, `compact`,
  and `fork`, and those are the available matcher values.
- An account-level environment setup script is not an available mechanism. Anthropic snapshots the
  filesystem after the setup script completes and reuses that snapshot for later sessions, rebuilding
  it only on a change to the script or its allowed hosts, or when the cache expires after roughly
  seven days. So an edited skill can be served stale with nothing reporting it, which is the failure
  class this contract exists to remove.
- The three constraints above were verified against Anthropic's Claude Code documentation on
  2026-08-07, at `code.claude.com/docs/en/hooks`, `/settings`, and `/cloud-environments`. They are
  recorded with their date because a contract resting on another product's behaviour is exactly the
  kind of claim that decays into folklore, which is the reasoning behind the provenance convention in
  `AGENTS.md`.
- `install.py --check` already exits 2 for a home with nothing recorded beneath it, naming the state
  as unrecorded rather than clean (`chore-0031`). Presence therefore needs no second probe, and a
  second one would duplicate that tool's knowledge of where skills live.
- The CI matrix is three operating systems by two Python versions. Any single run of the command
  covers one cell of six.
- The autonomy ceiling for any unattended run: push to a `claude/` branch, open a draft pull
  request carrying the evidence report, never merge.

## Scenarios

### Scenario S-001: one command runs every gate and answers with one exit code

- **Given** a working tree in any state
- **When** the acceptance command runs
- **Then** every gate in the gate set runs, each is named in the output with its own outcome, and
  the run exits zero only when all of them passed.

### Scenario S-002: a failing gate is named, and the gates after it still run

- **Given** a working tree where one gate fails and later gates would pass
- **When** the acceptance command runs
- **Then** the failing gate is named with its output, every remaining gate still runs and reports,
  and the run exits 1.
- **And** the report is complete rather than truncated at the first failure, because an agent with
  no human present gets one round trip and a report naming only the first failure spends another.

### Scenario S-003: a gate that could not run outranks a gate that failed

- **Given** a gate whose command cannot be executed at all, for example because its script is absent
  or the interpreter cannot start it, as distinct from one that executed and returned a failure
- **When** the acceptance command runs
- **Then** that gate is reported as unable to run rather than as passed or failed, and the run exits
  2 whatever the other gates returned, because a run that could not ask the question must not be
  read as having answered it.

### Scenario S-004: the run leaves no installation behind

- **Given** a gate set that installs into a throwaway location to exercise the real placement path
- **When** the acceptance command completes, whether passing or failing
- **Then** everything it placed beneath that location is removed, and no installation outside that
  location is created, modified, or removed, so a run on a development machine cannot disturb a real
  installation the way the sequence did before `bug-0003` scoped reversal to the home it was given.

### Scenario S-005: CI calls the command instead of restating the gates

- **Given** the continuous integration workflow
- **When** it runs
- **Then** it invokes the acceptance command rather than listing the gates itself, so a gate added
  to or removed from one is present in the other without a second edit.
- **And** this is the shape `chore-0029` established after an inline copy of the link rule drifted
  from the rule itself and let a correctly quoted changelog entry pass locally and fail in CI.

### Scenario S-006: the bound of the answer is stated in both places it will be read

- **Given** any completed run of the acceptance command
- **When** it reports its outcome
- **Then** the summary names the operating system and Python version the run used, so its answer is
  never read as covering the matrix it did not execute.
- **And** `AGENTS.md` states in these words that passing the command is **necessary but not
  sufficient**, so an agent reading the rules before it works finds the bound, rather than only an
  agent reading a run that already happened.

### Scenario S-007: passing the command does not make a Windows-only failure pass

- **Given** a change that passes the acceptance command on the platform where it was run and fails
  only on Windows
- **When** the CI matrix runs the same command across its cells
- **Then** the Windows cells fail, the pull request does not become mergeable, and nothing in the
  command's own output claimed otherwise.

### Scenario S-008: a session with no reachable skills is told at the start

- **Given** a session starting in a clone where no kit skill is present at project scope or at any
  user-scope discovery directory, with the bootstrap registered in the repository's committed
  settings
- **When** the session starts
- **Then** the agent receives injected context, before it begins work, stating that no kit skill was
  found at either scope and naming the command that would place them.
- **And** nothing on disk is created, modified, or removed to produce that report.

### Scenario S-009: skills committed at project scope count as reachable

- **Given** kit skills present at the repository's own project-scope discovery directory and none at
  any user-scope directory
- **When** the session starts
- **Then** the bootstrap treats them as reachable and injects nothing, because reachability is the
  question and where they were reached from is not.

### Scenario S-010: a session with reachable skills receives nothing

- **Given** kit skills present at a user-scope discovery directory
- **When** the session starts
- **Then** no context is injected at all.
- **And** silence is the whole of the report in this case, because a bootstrap that speaks on every
  start becomes a line an agent learns to skip, and then says nothing on the one start that mattered.

### Scenario S-011: reachability is not currency

- **Given** kit skills present at a discovery directory, and an installed copy that no longer matches
  its source in this repository
- **When** the session starts
- **Then** the bootstrap injects nothing, exactly as in S-010, because it answers reachability and
  makes no claim about whether what it reached is current.
- **And** its silence therefore means reachable, and never means current. Reading it as current is
  the misinterpretation this clause exists to foreclose, since a stale skill is a valid skill that
  passes every validator and reads correctly.

### Scenario S-012: a present install with no record is reachable, and separately unrecorded

- **Given** skills present at a user-scope directory and no manifest recording them
- **When** the session starts, and `install.py --check` is separately run against the same home
- **Then** the bootstrap injects nothing, because the files are there, and `--check` exits 2 naming
  the state as unrecorded, because nothing recorded them.
- **And** the two answers are both correct and are not in conflict: reachability is a question about
  the filesystem, and the manifest is not consulted to answer it.

### Scenario S-013: only a started session fires the bootstrap

- **Given** a session that is resumed, cleared, compacted, or forked rather than started
- **When** the session-start event fires
- **Then** the bootstrap produces no output, whatever the reachability state is, because those
  sources continue a session whose agent has already been told.

### Scenario S-014: the bootstrap writes nothing, in every case

- **Given** any session start, in any reachability state, reporting or silent
- **When** the bootstrap runs
- **Then** no file anywhere is created, modified, or removed, including any cache, marker, or log of
  its own.

### Scenario S-015: an unreadable payload leaves the session unchanged

- **Given** input the bootstrap cannot parse, or a failure inside it
- **When** it runs
- **Then** it emits no output and exits zero, so a session is never broken by the guardrail meant to
  protect it, per the hooks module contract.

### Scenario S-016: the bootstrap does not vary by where it runs

- **Given** two sessions with the same reachability state, one cloud-hosted and one local
- **When** each starts
- **Then** both produce byte-identical output, because nothing in the bootstrap inspects the
  environment it is running in.

### Scenario S-017: the proof run lands as a draft pull request carrying its evidence

- **Given** [`bug-0020`](../../.tasks/done/bug-0020-check-unknown-remedy-is-wrong-for-the-adopted-lens.md)
  dispatched to a cloud session under the autonomy rules module
- **When** the session completes its work
- **Then** the work is on a branch whose name carries the `claude/` prefix, a pull request exists in
  **draft** state, its body carries a report meeting the nine-field evidence contract from
  [`feat-0041`](../../.tasks/done/feat-0041-delegate-evidence-contract-for-fix-batch.md) including
  the acceptance command's verbatim output, and nothing has been merged.

### Scenario S-018: the proof's evidence is a test that failed before the change

- **Given** the same dispatched task, whose acceptance requires a regression test that fails against
  the unfixed `install.py` and passes against the fixed one
- **When** the session reports
- **Then** the report shows that test failing before the change and passing after, so the proof rests
  on an outcome the session could not have produced by writing plausible text.
- **And** this is why the proof task is a defect in code rather than a change to a skill body: the
  acceptance command for a prose task passes whatever the prose says, so it could not distinguish a
  session that did the work from one that only appeared to.

### Scenario S-019: a proof run whose gates fail still reports

- **Given** the same dispatched session, where the acceptance command exits non-zero
- **When** the session completes
- **Then** it still opens a draft pull request whose report carries the failing verbatim output and
  names the failure, rather than abandoning the work, retrying until something passes, or reporting
  a result the command did not produce.

## Proposed Surface

| Element | Detail |
|---|---|
| Acceptance command | `python scripts/run-checks.py`, no flags |
| Gate set | The seven currently in [`checks.yml`](../../.github/workflows/checks.yml): skill lint, the test suite, backlog validation, adapter dry run, install dry run, the install/re-install/uninstall sequence, and the globbed link check |
| Throwaway home | `./.tmp/zen-home`, the location the existing CI steps already use |
| Exit code | 0 every gate passed, 1 at least one gate failed, 2 at least one gate could not run; 2 outranks 1, as in `install.py --check` and `check-provenance.py` |
| Output | One line per gate naming it and its outcome, the failing gate's own output where one failed, then a summary carrying the counts and the operating system and Python version the run used |
| CI wiring | One workflow step invoking the command, replacing the seven that restate it |
| `AGENTS.md` | Names the command and states that passing it is necessary but not sufficient |
| Bootstrap hook | A member of the [`.agents/hooks/`](../../.agents/hooks/README.md) module in the **reminder** shape, on the `SessionStart` event with a `startup` matcher |
| Bootstrap registration | Committed in the repository's own `.claude/settings.json`, since a user-level registration does not reach a cloud session |
| Bootstrap output | Nothing when skills are reachable; otherwise one `hookSpecificOutput.additionalContext` object stating that no kit skill was found at either scope and naming the command that would place them |
| Reachable | At least one kit skill directory present at the repository's project-scope discovery directory, or at any user-scope discovery directory `install.py` targets |
| Unattended branch and pull request | Branch prefix `claude/`; pull request opened in draft, carrying the nine-field report |

## Open Questions

1. **Should the bootstrap also fire on `clear`?** A cleared session has lost the context the
   `startup` firing injected, so by the letter of the goal it qualifies. **Recommendation: no for
   v1.** `clear` is a deliberate act by a person who is present, which is the one case this hook is
   not for, and firing there trades the property S-010 protects for a case with a human in it.
   Revisit if a cleared cloud session turns out to be a real shape.
2. **Should task files' acceptance criteria be rewritten to call the command?** The drift between
   those chains and the gate set is part of the problem stated above, so leaving them is leaving half
   the problem. **Recommendation: not in this contract.** The chains stay valid because the command
   is a superset of them, and rewriting the open backlog is a separate pass carrying its own risk of
   touching task files mid-flight. Worth filing once the command exists and has been used.
