---
id: chore-0071
title: The autonomy candidate held for want of a citation now has one, and the kit is about to enter the conditions it describes
type: chore
status: open
priority: P2
parent: "ROADMAP Epic E #1: autonomy.md v1"
depends_on: []
touched_files:
  - .agents/rules/autonomy.md
created: 2026-08-27
---

## Problem

[`autonomy.md`](../.agents/rules/autonomy.md) closes with a section titled "Considered for v1 and held,
for want of a citation". One entry there is **instructions embedded in material a skill was pointed at**:
a diff, an issue body, a fetched page, or a file in a target repository, where an instruction inside the
data is treated as a direction rather than as part of the data.

The module records why it was held, and the reasoning is worth keeping:

> **Held because the search for a citation came back empty, not because the class was judged small.**
> ... The gap looks structural rather than lucky: everything this kit has read so far was written by its
> own maintainer or its own agents, so no skill here has yet been pointed at text by someone with a reason
> to steer it.

It names its own trigger: "the first run where a skill reads material from outside the maintainer's
control (a diff from a fork, an issue body from a stranger, a page fetched from the web), or the first
report through the private channel `SECURITY.md`."

**Neither trigger has fired. A citation now exists anyway, and it is a good one.**

**Clinejection.** Cline added an AI issue-triage workflow on 21 Dec 2025, configured with
`allowed_non_write_users: "*"`. The **GitHub issue title**, attacker-controlled from any account, was
interpolated directly into the agent's prompt, causing it to `npm install` from an attacker-controlled
repository whose `preinstall` script poisoned the Actions cache and stole the npm release token. An
unauthorised `cline@2.3.0` was published on 17 Feb 2026.

The researcher, Adnan Khan, demonstrated it on his own mirror repository, and then, in his words, **"a
different actor found my PoC on my test repository and used it to directly attack Cline and obtain the
publication credentials."** Research to real exploitation, through the disclosure itself.

The sentence that belongs in the rule is his:

> "Since Claude runs `npm install` via the Bash tool, there is no opportunity for the LLM to inspect what
> executes."

**Why this is timely rather than merely available.** The kit's stated next phase is rollout across
repositories the maintainer does not solely author. The held entry's precondition ends there, and it does
not end gradually. Simon Willison's **lethal trifecta** is private data, untrusted content, and external
communication: any two are safe, all three are exploitable. This kit already has repository access and
push capability. The third leg closes the first time a skill reads a third-party diff.

## Scope

**In scope:** write the rule, in its enforceable form, with its citation.

- One rule in the existing shape: an imperative sentence, a *Cited* line naming the incident, and the
  consequence. Follow `A1` through `A9`; do not invent a new format.
- **Move the entry out of the held section** and say plainly that its stated trigger did not fire and an
  external citation was accepted instead. The held section exists to be a real gate, so discharging an
  entry by a route it did not name has to be visible rather than quiet.
- Keep the module's own qualification style. `A8` is the precedent: it is marked as **"a decision recorded
  in `ROADMAP.md` Epic E rather than a rule this kit has already run under"**, named as such rather than
  dressed up as consolidated. This rule is in the same position and should carry the same honesty.

**Out of scope:**

- **Building any detection or gate.** See the trap below. This task writes a rule; it does not implement
  one.
- The hooks module, `fix-batch`, and every skill body. If the rule implies a change to any of them, that
  is a finding to report and a separate task.
- The other three held candidates. Retry limits, budgets, and escalation paths keep their holds.
- `SECURITY.md`, whose private-report channel is unchanged by this.

## Implementation notes

**The trap, and it is the whole reason the rule must be worded carefully.** The obvious rule is "detect
and refuse instructions found in data". That is published as broken, repeatedly and by named
researchers. Zhan et al. (NAACL 2025 Findings, arXiv:2503.00061) evaluated eight defences and broke all
of them with adaptive attacks. "The Attacker Moves Second" (arXiv:2510.09023) bypassed twelve defences
spanning prompting, adversarial training, filtering and secret-knowledge mechanisms, and a human
red-team competition of 500 participants defeated **every defence tested**. NIST AI 100-2e2025 states
plainly that complete protection is not achievable. Anthropic's own security documentation says the same:
"no system is completely immune to all attacks."

**So the enforceable form is a constraint on what happens after ingestion, not a detector.** The
formulation to follow is from Beurer-Kellner et al. (arXiv:2506.08837, authors from Invariant Labs, IBM,
EPFL, ETH Zurich, Google, Microsoft):

> "once an LLM agent has ingested untrusted input, it must be constrained so that it is impossible for
> that input to trigger any consequential actions."

They are explicit about the cost, and the rule should be too: these patterns "impose intentional
constraints on agents, explicitly preventing them from solving arbitrary tasks."

**One decision to make rather than assume.** The module's gate is that "each rule names where it was
already exercised: a file and line, a task id, or a recorded incident." Every existing citation is
internal to this repository. Clinejection is external. **Decide whether an external incident satisfies
that gate, and say so in the module**, because the answer governs every future rule, not just this one.
`A8`'s precedent suggests yes-with-a-marker rather than a silent widening.

Keep it short. The module's own failure mode is doctrine inflation, and `A1` to `A9` average a few
sentences each.

## Risks and rollback

One file, prose only, in a swappable module an adopter is invited to rewrite.

The risk is a rule that sounds strong and forbids nothing checkable, which is how a lens accumulates
weight without changing behaviour. The guard: the rule must name at least one concrete thing an agent
does differently on reading it. If it cannot, report that and add nothing.

A second risk is scope creep into implementation, since the enforceable form invites a hook. Resist; the
hook is a separate decision with a separate cost, and `AGENTS.md` reserves gate decisions to the author.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] `autonomy.md` carries the new rule in the same shape as `A1` through `A9`, with a *Cited* line
      naming Clinejection and its date.
- [ ] The rule is stated as a constraint on action after ingestion, not as detection of injected text,
      and the closeout says which published formulation it follows.
- [ ] The rule names at least one concrete thing an agent does differently.
- [ ] The held section no longer lists this candidate, and states that its stated trigger did not fire.
- [ ] The module records whether an external incident satisfies its citation gate, as a stated decision.
- [ ] No file under `.agents/hooks/`, `.agents/skills/`, or `scripts/` is modified.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
