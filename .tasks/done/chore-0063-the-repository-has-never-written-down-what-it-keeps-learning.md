---
id: chore-0063
title: The finding this repository keeps making about itself is recorded nowhere durable, so every session rediscovers it or does not
type: chore
status: done
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: []
touched_files:
  - AGENTS.md
created: 2026-08-22
---

## Problem

Across six waves and a deep review, one finding has recurred more than any other and has never been
written into this repository:

> **Every defect that mattered was invisible to a passing build.** The mechanical layer is healthy.
> The defects live in the semantic layer, where nothing automated is looking.

Searched 2026-08-22 across the whole tree:

```text
grep -rl "invisible to a passing build"  ->  no match in AGENTS.md
                                         ->  no match in ROADMAP.md
                                         ->  no match in any lens or skill
```

Each closed task records **its own instance**. Nothing records the class. So the finding survives only
in whichever session happens to be running, and a fresh session either rediscovers it at cost or
proceeds without it.

**That is the same defect the finding is about**, one level up. A thing that is understood but not
written where a reader can find it is exactly what `feat-0047` recorded about prose conventions, what
`bug-0037` recorded about citations, and what `house-style.md` now says about counts beside tables.
This repository is unusually good at noticing that pattern in its artifacts and has not applied it to
its own strongest conclusion.

**The evidence is not thin, which is the bar `autonomy.md` sets.** Six citations, all closed, all
found while every gate was green:

| Task | What passed while it was broken |
|---|---|
| `bug-0045` | Six of seven gates reported `ok` over a repository containing nothing. |
| `bug-0044` | Seven links dangled in every shipped `cursor` and `vscode` tree. |
| `bug-0046` | A `.md` to `.MD` rename dropped two records at exit 0. |
| `bug-0037` | Sixty-five evidence citations, seven pointing at unrelated text. |
| `bug-0040` | A lens named only inside a code fence counted as composed. |
| `bug-0041` | A typo on one field deleted a whole provenance block, silently. |

## Scope

**In scope:** write the finding where every agent working here will read it.

- One short section in `AGENTS.md`, stating the finding and what it implies for an agent: a green
  acceptance run is necessary and not sufficient, and it is evidence about the mechanical layer only.
- Carry the citations. `autonomy.md`'s gate is that a rule which cannot be cited does not belong, and
  the table above is the evidence. Prefer naming three or four of the sharpest to listing all six.
- Say what an agent should **do** differently, not just what is true. A finding with no behavioural
  consequence is a slogan. The candidate consequences are already exercised in this repository: probe
  the behaviour by hand rather than reading the code, construct the empty or degenerate input and see
  what the tool says, and treat a check that cannot fail as unchecked.

**Out of scope:**

- **Adding a gate.** This is a finding about the limits of gates, and answering it with an eighth gate
  would be funny rather than useful. The five open tasks in the guard class are where mechanical
  coverage gets closed, one at a time and on their own evidence.
- `ROADMAP.md`, `CHANGELOG.md`, and the reader-facing documents. This is a rule for agents working
  here, so it belongs with the other rules.
- Rewriting any existing `AGENTS.md` section. The acceptance-command section already says passing is
  necessary but not sufficient, and this extends that thought rather than replacing it. **Read that
  paragraph first**: if it already carries the finding well enough, the honest outcome is a short
  addition there rather than a new section, and saying so is a valid result.
- The lenses. `review-quality.md` governs how a review is written and `autonomy.md` what an unattended
  agent may do; neither is about where defects are found. If the work argues otherwise, that is a
  finding to report rather than a place to widen into.

## Implementation notes

Keep it short. The failure mode for a section like this is a page of doctrine nobody reads, which
would be a worse outcome than the current silence because it would look like the problem was solved.
Three or four sentences plus the citations is the target.

Write it as a finding with evidence, not as an exhortation. "Verify carefully" is advice; "six of
seven gates reported `ok` over a repository containing nothing, and every gate was green the whole
time" is a fact an agent can act on.

Do not overstate it. The mechanical layer being healthy is a real and earned result: the gates catch
what they were built to catch, and several of them have caught real regressions during these waves.
The claim is about what they cannot see, not that they are worthless.

## Decisions

- **Rejected alternative: a new `AGENTS.md` section.** Checked rather than assumed: the existing
  acceptance-command paragraph does not carry the finding. It shares the sentence "necessary but not
  sufficient" and gives a different reason for it, sample coverage across the six-cell CI matrix,
  whose implied remedy is running more cells. The finding is that a full six-cell green run is still
  silent about the semantic layer, which no number of cells closes. So the paragraph does not merely
  under-state the finding, it points away from it. The addition went in as a sibling paragraph
  directly after it, inside `### The acceptance command`, for three reasons: that section already
  defines `run-checks.py` as "every gate that decides whether a change here is acceptable", so it is
  already the section about all the gates; putting the two reasons adjacent is what makes the
  contrast legible, one insufficiency shrinking as you run more cells and the other not; and a new
  `###` heading in a file every agent reads in full is the first step toward the page of doctrine
  this task names as its failure mode. No existing word was changed; the diff is 15 insertions and 0
  deletions.

- **Premise false: this task's own evidence table overstates `bug-0037`.** The table says "Sixty-five
  evidence citations, seven pointing at unrelated text". Sixty-five is right and is confirmed in that
  task's closeout ("65 line pointers were re-derived, not 40"). Seven is not: its record names two
  known-wrong rows plus one more found already stale during re-derivation, so three. The only "seven"
  in `bug-0037` is "All seven gates pass", which looks like the source of the conflation. `AGENTS.md`
  says three of sixty-five. The neighbouring row is the opposite case and was also checked:
  `bug-0044`'s "seven links" contradicts its own title, which says six, and is correct, because its
  closeout records "Premise corrected: there are seven dangling link instances, not six."

- **Seam left open: the citations are bare backticked ids, not relative links.** `AGENTS.md` cites
  task ids this way in all six places it already does so (`bug-0011`, `feat-0031`, `chore-0040`,
  `bug-0041`, `bug-0042`, `chore-0029`) and links to none of them, unlike `ROADMAP.md`. The addition
  follows the local convention rather than the house-style link rule, so a later agent does not read
  the unlinked ids as an oversight and "fix" four of them into `.tasks/done/` links.

## Risks and rollback

One file, prose only, so this section is short.

The risk is doctrine inflation. `AGENTS.md` is read in full by every agent at the start of every task,
so every paragraph added is a tax on every future run. This one earns its place only if it changes
behaviour; if the work cannot name what an agent should do differently, the honest outcome is to file
that conclusion and add nothing.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] `AGENTS.md` states the finding, in a section or as an addition to the acceptance-command
      paragraph, with at least three citations to closed tasks.
- [x] It names at least one concrete thing an agent should do differently, and that thing is something
      this repository has actually exercised rather than invented.
- [x] The addition is under roughly fifteen lines, counted.
- [x] No gate is added and no existing `AGENTS.md` section is rewritten.
- [x] The closeout states whether the existing acceptance-command paragraph already carried the
      finding, checked rather than assumed.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
