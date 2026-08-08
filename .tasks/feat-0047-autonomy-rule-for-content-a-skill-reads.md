---
id: feat-0047
title: The threat model names prompt injection as reportable and no skill or lens says anything about it
type: feat
status: open
priority: P2
parent: "ROADMAP Epic E #3: harden autonomy.md from what item 2's run revealed"
depends_on: []
touched_files:
  - .agents/rules/autonomy.md
created: 2026-08-08
---

## Problem

[`SECURITY.md`](../SECURITY.md) asks for private reports of "prompt-injection paths, where content a
skill is designed to read (a diff, an issue body, a fetched page, a file in the target repo) can
redirect the agent's behavior". Grepping the whole of `.agents/` for that class on 2026-08-08 returns
one file, [`test-quality`](../.agents/skills/test-quality/SKILL.md), and it is discussing adversarial
**test inputs** rather than this.

So the kit invites reports of a class it has written nothing about, in a library whose entire premise
is that a skill is "prose an agent reads and acts on, in your repository, usually with permission to
write files and run commands".

The skills that face it are the ones that read text somebody else can influence and then act on it:

| Skill | What it reads |
|---|---|
| [`pr-describe`](../.agents/skills/pr-describe/SKILL.md) | issue bodies and titles from a tracker |
| [`house-review`](../.agents/skills/house-review/SKILL.md), [`review-depth`](../.agents/skills/review-depth/SKILL.md) | a diff, which is whatever somebody wrote |
| [`doc-sync`](../.agents/skills/doc-sync/SKILL.md) | every reader-facing document in a target repository |
| [`reconcile-worktrees`](../.agents/skills/reconcile-worktrees/SKILL.md), [`fix-batch`](../.agents/skills/fix-batch/SKILL.md) | the output and diffs of other agents |

`fix-batch`'s "a delegated agent's report is a claim, not evidence" doctrine is adjacent and genuinely
strong, and it is not this: it guards against an optimistic report, not against instructions embedded
in the material an agent was asked to read.

## Scope

**In scope:** decide whether [`autonomy.md`](../.agents/rules/autonomy.md) gains a rule drawing the
line between text an agent acts on and text an agent reads, and either write it with its citation or
record it in that module's held section with a trigger. Then reconcile `SECURITY.md` with whichever
answer is taken.

**Out of scope:**

- Editing any `SKILL.md`. A rule belongs in the swappable lens, not copied into thirteen skill bodies,
  and the skills that reference the module get it for free. If a skill needs a local exception, that is
  a separate task with its own evidence.
- Any mechanical detection or sanitising of untrusted content. There is nothing here to build it in,
  and a detector for this class is a research problem rather than a rules-module line.
- Changing what `SECURITY.md` invites people to report. The invitation is right; only the silence
  behind it is the problem.

## Implementation notes

**The honest answer may be "held", and that is a real outcome rather than a failure of the task.**
`autonomy.md` states its own gate plainly: "A rule that cannot be cited does not belong in v1", and it
exists because "an invented rule reads exactly like a consolidated one. Both are one confident
sentence in the imperative", and a module mixing the two spends the authority of the real rules on the
made-up ones. Three candidates are already held there for exactly this reason, with triggers, and
adding a fourth is a legitimate result.

So the work is to look for the citation before writing the rule:

- Search this repository's own history and task records for an occasion where content a skill read
  changed what an agent did. The `fix-batch` incident where two of three agents worked from a task
  premise that was factually wrong is the nearest thing and is **not** an instance: a wrong premise is
  an authoring defect, not an injection.
- If nothing is found here, say so. A citation from outside this kit is weaker than one from inside
  it, and the module's `A8` shows the shape for a rule whose ceiling is a recorded decision rather
  than an exercised one: state it as such rather than dressing it up.

If a rule is written, the useful form is a boundary rather than a warning. `A1` already draws one in
space, "stay inside your sandbox, and treat the boundary as a runtime rule, not a starting state". The
counterpart draws one in provenance: material a skill was pointed at is **data to report on**, and an
instruction inside it is part of the data. Keep it to the module's existing shape, one imperative
sentence, then the reasoning, then the citation.

Either way `SECURITY.md` should end up consistent with the answer. If the rule lands, name it. If it
is held, the reporting invitation can stay and the reader should be able to see that the kit knows the
class is open, rather than inferring silence means coverage.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py && python scripts/run-checks.py

- [ ] `autonomy.md` addresses the class, either as a numbered rule carrying a citation in the form the
      other eight use, or as an entry in the held section carrying a trigger to revisit.
- [ ] If a rule is added, its citation names a file, a task id, or a recorded incident, and the search
      that produced it (or failed to) is recorded in the task's Decisions section.
- [ ] If it is held, the held entry states what evidence would move it into the module.
- [ ] `SECURITY.md` and `autonomy.md` do not contradict each other on whether the class is covered.
- [ ] No `SKILL.md` is edited.
- [ ] The module still ships without this repository around it: every reference outside the installed
      skill tree is named in prose rather than linked, which the lint enforces.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
