---
title: agent-observatory
status: approved
---

# agent-observatory

Behavioral contract for the agent observatory (ROADMAP Epic E, the reporting half of item 7).
Drafted 2026-08-28 by the `spec-author` skill and self-checked to `ready` with the `spec-quality`
lens.

## Problem

This kit asks one question of every skill it ships, in the contribution-bar section of
[`AGENTS.md`](../../AGENTS.md): is this something the author actually uses and has iterated on?
Nothing here can answer it. The bar is applied from memory, one skill at a time, and a skill that
quietly stopped being used looks exactly like one that is working.

The same blindness covers delegated work. [`fix-batch`](../../.agents/skills/fix-batch/SKILL.md)
dispatches a wave of isolated agents, and
[`reconcile-worktrees`](../../.agents/skills/reconcile-worktrees/SKILL.md) lands them, but no record
survives of what the wave cost, which agent took longest, which was retried, or which returned
nothing. `feat-0041` had to write a nine-field evidence contract precisely because a delegated
agent's own report is a claim rather than evidence, and the evidence it asks for is assembled by
hand every time.

**The data to answer all of this already exists and nothing reads it.** The harness writes a
transcript per session, and those transcripts carry per-message skill attribution, per-subagent
duration and token totals, tool outcomes, hook failures, and API errors. On this maintainer's
machine that is 406 transcripts across 23 project directories. The corpus is large enough to be
authoritative and unreadable enough that no one has ever read it.

A third gap is operational rather than analytic. Work now runs across many projects at once, and
there is no single place that says which sessions exist, which are still running, and which are
waiting on a person. The harness shows one session at a time.

What is missing is a reporting surface over data the harness already produces: one that answers what
was used, what it cost, what it produced, and what is running, across every project at once, without
changing anything it reads.

## Goals

1. Report skill usage across every project, including which skills have never been used.
2. Report subagent usage, and reconstruct a dispatched wave as a single unit of work.
3. Report the state of every session across every project, distinguishing running from ended.
4. Report token consumption and an estimated cost, labelled as an estimate.
5. Report run health: hook failures, API errors and retries, and runs that ended abnormally.
6. Report context and quota pressure over time.
7. Update while sessions are running, rather than only on demand.
8. Accept an additional event source without changing what is reported.
9. Change nothing that the harness owns.

## Non-Goals

- **Setting any bound.** No retry limit, token budget, futility threshold, or stop signal. Those are
  Epic E item 7's second half and stay held. This contract produces the distribution such a bound
  would one day be set against, and sets none.
- **Judging whether a skill's output was good.** That is evaluation, held under `feat-0051`. This
  reports what ran and what it cost, never whether it was right.
- **Starting, resuming, interrupting, or ending a session.** The reporting surface performs no
  session mutation of any kind.
- **Shipping to an adopter.** This is maintainer tooling. Nothing here is placed into an adopter's
  tree by the installer, and the portability contract is therefore untouched.
- **Replacing the harness's own session interface.** This reports across sessions; the harness
  remains where a session is worked in.
- **Reconstructing conversation content.** Prompts and responses are not part of what is reported.

## Constraints

- **Standard library only.** No third-party dependency and no package manager, so the acceptance
  command needs no install step on any platform.
- **Windows, macOS, and Linux.** Transcript records carry platform-native working directories, and
  project directories encode path separators in their names, so neither may be assumed POSIX.
- **No network access at any point.** The threat model fixed by `chore-0035` states the kit makes no
  network calls. Cost rates are therefore local data with a recorded date, never fetched.
- **The corpus grows by append and is large.** Re-reading everything on each refresh is not viable,
  so a refresh must cost work proportional to what changed rather than to what exists.
- **Transcripts carry no cost field.** Any monetary figure is derived and is an estimate.
- **A live event source that requires a hook is opt-in and never blocks.** The one committed hook
  registration in this repository is documented in `AGENTS.md` as a closed exception, so any hook
  here is registered by the user at their own scope, follows the reminder shape, and never prevents
  a session from continuing.
- **The harness owns its data.** Everything read here belongs to another program that may be writing
  to it concurrently, including part-written final records.

## Scenarios

### Scenario S-001: skill usage is reported from attribution already in the corpus
- **Given** a corpus containing sessions in which skills were used
- **When** a usage report is produced
- **Then** each skill that appears is reported with its name and the number of times it was used,
  and the totals equal the attribution present in the corpus

### Scenario S-002: a skill that has never been used is reported as zero, not omitted
- **Given** a set of installed skills and a corpus in which some of them never appear
- **When** a usage report is produced
- **Then** every installed skill appears in the report, and one that never appears in the corpus is
  reported with a count of zero rather than left out

### Scenario S-003: subagent runs are reported with their outcome and cost
- **Given** a session in which subagents were dispatched
- **When** a usage report is produced
- **Then** each dispatched agent is reported with its type, the model it resolved to, its duration,
  its token total, its tool-call count, and whether it completed or ended without completing

### Scenario S-004: a dispatched wave is reported as one unit of work
- **Given** a session that dispatched several agents against separate isolated workspaces
- **When** that session is reported
- **Then** those agents are reported together as one wave, each with the workspace and branch it was
  given and its own start and end time

### Scenario S-005: re-reporting an unchanged corpus changes nothing
- **Given** a corpus that has been reported once and has not changed since
- **When** a report is produced again
- **Then** the reported figures are identical to the previous run, and no duplicate record is
  introduced by the second run

### Scenario S-006: new records are picked up without re-reading the corpus
- **Given** a corpus that has been reported once, to which a session has since appended records
- **When** a report is produced again
- **Then** the appended records are included in the report, and the records read from the corpus by
  the second run are only those appended since the first

### Scenario S-007: an empty corpus is reported as empty
- **Given** a location containing no transcripts at all
- **When** a report is produced
- **Then** the run reports that it found zero transcripts, and that outcome is distinguishable from a
  run that found transcripts and reported figures from them

### Scenario S-008: an unreadable record is reported rather than silently dropped
- **Given** a corpus containing a record that cannot be parsed, such as a final line still being
  written
- **When** a report is produced
- **Then** the run completes over the records it could read, and states how many records it could
  not read and where, rather than omitting them silently

### Scenario S-009: nothing the harness owns is modified
- **Given** a corpus and the harness's own state directories
- **When** any report is produced, including with a live source active
- **Then** every file the harness owns is byte-for-byte unchanged afterwards

### Scenario S-010: cost is reported as an estimate against a dated rate table
- **Given** sessions whose token consumption is known and models whose rates are present in the rate
  table
- **When** cost is reported
- **Then** the figure is labelled an estimate and is accompanied by the date the rates were recorded

### Scenario S-011: an unpriced model yields no invented cost
- **Given** a session using a model with no entry in the rate table
- **When** cost is reported
- **Then** that session's tokens are still reported, its cost is reported as unknown rather than as
  zero or as a guess, and the model is named as unpriced

### Scenario S-012: a running session is distinguished from an ended one
- **Given** at least one session currently running and at least one that has ended
- **When** the state of sessions is reported
- **Then** each is reported with its project, its branch, and its last activity, and the running one
  is identified as running

### Scenario S-013: the report updates while a session is running
- **Given** a report open against a corpus, and a session that then does further work
- **When** that work produces new records
- **Then** the open report reflects the new work without being requested again

### Scenario S-014: the optional event source is absent and everything still works
- **Given** no optional event source configured, and a session doing work
- **When** a report is produced and left open
- **Then** the report still reflects that work, the run reports no error attributable to the missing
  source, and the delay between a session writing a record and the report reflecting it is stated

### Scenario S-015: an optional event source supplements the corpus without changing the report
- **Given** an optional event source configured and delivering events
- **When** a report is produced
- **Then** the reported figures agree with those derived from the corpus alone, events are attributed
  to the source they arrived from, and no figure is counted twice

### Scenario S-016: run health is reported
- **Given** a corpus containing hook failures, API errors that were retried, and a run that ended
  abnormally
- **When** health is reported
- **Then** each is reported with the session it occurred in, when it occurred, and what it reported,
  including a hook's exit status and an API error's retry count

### Scenario S-017: context and quota pressure are reported over time
- **Given** a corpus containing context-budget records and a quota sample series
- **When** pressure is reported
- **Then** both are reported as series over time, and occasions where a session's context was
  compacted are identifiable

### Scenario S-018: every project is reported in one place
- **Given** a corpus spanning several project directories
- **When** any report is produced
- **Then** it covers all of them by default, each result is attributable to its project, and the
  figures reported when restricted to one project sum, across all projects, to the unrestricted
  figures

### Scenario S-019: the reporting surface offers no session mutation
- **Given** a report open against any session, running or ended
- **When** every action the surface offers is enumerated
- **Then** none of them changes the state of a session, and the actions that reference a session
  resolve to navigation or to a command presented for a person to run

### Scenario S-020: control is available only where the harness exposes it, and its absence degrades
- **Given** a harness that exposes no session-management capability
- **When** a session-directed action is requested
- **Then** the request is declined with the reason stated, the navigation actions of `S-019` remain
  available, and no alternative route to the same effect is attempted

### Scenario S-021: token consumption is reported by kind, not as one number
- **Given** sessions whose messages consumed input, output, cache-read, and cache-creation tokens
- **When** consumption is reported
- **Then** each of those four kinds is reported as its own figure, and the proportion served from
  cache is derivable from them

### Scenario S-022: no data leaves the machine
- **Given** any report, produced with every optional source configured
- **When** the run's outbound network activity is observed for its whole duration
- **Then** no connection to any remote host is attempted, including for rate data

## Proposed Surface

**Reports.** Each answers one question and is available over the whole corpus or one project.

| Report | Question it answers | Scenarios |
|---|---|---|
| Fleet | Which sessions exist, where, and which are running? | `S-012`, `S-018` |
| Skills | Which skills are used, how often, and which never are? | `S-001`, `S-002` |
| Waves | What did a dispatched wave run, cost, and produce? | `S-003`, `S-004` |
| Cost and pressure | What was consumed, and how close to a limit? | `S-010`, `S-011`, `S-017`, `S-021` |
| Health | What failed, and how often? | `S-016` |

**Reported figures.**

| Figure | Basis | Reported as |
|---|---|---|
| Skill use count | Attribution present in the corpus | An exact count |
| Subagent run | Dispatch record and its result | Type, resolved model, duration, tokens, tool calls, outcome |
| Wave | The set of agents one session dispatched | Members, each with its isolated workspace and branch |
| Tokens | Per-message consumption | Exact counts, split by input, output, cache read, and cache creation (`S-021`) |
| Cost | Tokens against the rate table | An estimate, with the rate table's date |
| Session state | Presence in the harness's live registry | Running or ended, with last activity |
| Health event | Hook, API, and termination records | The event, its session, its time, and what it reported |

**Sources.**

| Source | Required | Provides |
|---|---|---|
| Session transcripts | yes | Every figure above except live session state |
| Live session registry | yes | Which sessions are running now (`S-012`) |
| Quota sample series | no | The quota half of `S-017` |
| Rate table | yes | The basis for `S-010`, local and dated |
| Optional event stream | no | Lower latency for `S-013`, per `S-014` and `S-015` |

**Guarantees.**

| Guarantee | Scenario |
|---|---|
| Nothing the harness owns is modified | `S-009` |
| Re-running changes no figure | `S-005` |
| Refresh cost is proportional to change | `S-006` |
| An empty or unreadable input is stated, never absorbed | `S-007`, `S-008` |
| No session is mutated by the reporting surface | `S-019`, `S-020` |
| No data leaves the machine | `S-022` |

## Open Questions

1. **How is the rate table kept current, given no network access?** Rates change and a stale table
   silently misstates every cost figure. *Recommendation:* record the date in the table, surface that
   date beside every cost figure per `S-010`, and treat updating it as a normal maintenance task
   rather than automating a fetch that the threat model forbids.

2. **Does the corpus need pruning, and on what basis?** It grows without bound, and the harness
   prunes its own history on a schedule this contract does not control. *Recommendation:* report
   over whatever is present and add no retention policy in this contract, since a figure that
   silently changes when old data expires is worse than one that grows.

3. **Is one machine the boundary?** Every source named here is local, so a second machine produces a
   second corpus with no shared identity. *Recommendation:* scope this contract to one machine, and
   leave any cross-machine question to Epic F, which is where multi-participant workspaces already
   live.
