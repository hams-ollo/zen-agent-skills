---
name: new-task
description: >-
  Author one or more atomic, agent-ready task files for the .tasks/ work-tracking system, at a
  gold-standard bar. Turns a rough idea, a bug report, or a ROADMAP.md Feature into task files
  with honest touched_files, a real parent up-link, resolved depends_on, and a
  mechanically-verifiable acceptance command, then self-checks them with validate.py. Deliberately
  elicits and decomposes before writing, because a sharp task is worth 3-10x its authoring time
  downstream. Assigns collision-safe ids from the existing backlog. Use when the user says "write
  a task for X", "add this to the backlog", "spec out this bug", "turn this into task files",
  "break this feature into tasks", or hands over an idea they want made executable. Requires an
  existing .tasks/ system (run init-worktracking first if absent). Feeds fix-batch: one task file
  per worktree-isolated agent.
license: MIT
---

# new-task

Author task files that an isolated agent can execute without asking questions. This is the decomposition step of the kit spine: `new-task` -> `fix-batch` (parallel worktree-isolated agents). It writes *into* the `.tasks/` system that `init-worktracking` scaffolds, so `init-worktracking` runs before this skill rather than after it, which is why Step 1 stops and points at it when `.tasks/` is absent. When the input is an approved spec, `spec-plan-readiness` gates the task set before dispatch (Step 7). The quality of everything downstream is capped by the quality of the task file, so this skill spends effort up front on purpose.

## The bar a task file must clear

A good task is self-contained: an agent that reads only `AGENTS.md`, the task file, and the files listed in `touched_files` can finish it correctly. Concretely, every task you write must have:

- **Honest `touched_files`**: the complete read/write surface, discovered by inspecting the repo, not guessed. Too narrow and the agent is blocked; too wide and it wanders and collides with parallel agents.
- **A real `parent`**: what the task serves, so intent is traceable without reading anything else. Where `ROADMAP.md` exists, that is the Feature or Epic it hangs from, and if no Feature fits, propose adding one. Where it does not, which is the `init-worktracking` **lite** tier, it is one line of free text naming the goal. Required either way, and never a pointer to a file the repo does not have.
- **Resolved `depends_on`**: ids of tasks that must reach `done/` first; `[]` if none. Never invent an id.
- **`spec` and `scenarios`, when the work comes from an approved spec**: the contract path and the `S-NNN` ids this task covers. Omit both when there is no spec. See [Decomposing an approved spec](#decomposing-an-approved-spec).
- **A mechanically-verifiable acceptance command**: an exact command (usually the repo's test command scoped to the change) that passes only when the work is done. Not "tests pass" in prose, the literal command.
- **Risk and rollback notes, when the deterministic rule fires.** Required when the task touches more than one module, changes a persisted data format or protocol, or cannot be safely reversed by reverting one commit. Omit the section entirely when none of the three hold. This is not a judgment call about how risky the work feels: it is the same rule [`spec-plan-readiness`](../spec-plan-readiness/SKILL.md) applies, quoted so the two cannot drift apart, and a task that triggers it without the notes will be blocked at the gate no matter how well the rest is written.
- **Tight scope with an explicit out-of-scope**: so a well-meaning agent keeps the change atomic.

## Why this skill blocks a little

Both the `spec`/`brainstorm` patterns in mature agent frameworks and hard experience say the same thing: jumping straight to code on an underspecified task wastes far more time than the few minutes of elicitation. So this skill asks its questions and shows its decomposition before writing files. That friction is the feature. Do not skip it for anything non-trivial.

## Decomposing an approved spec

Most tasks come from a rough idea or a roadmap Feature, and the procedure below covers those
unchanged. When the input is instead an **approved spec**, this skill is the decomposition step of
the contract-driven spine: [`spec-author`](../spec-author/SKILL.md) drafts the spec, a human sets
`status: approved`, and `new-task` turns it into the ordered task set that
[`spec-plan-readiness`](../spec-plan-readiness/SKILL.md) then gates before any code is written.

That gate blocks on any task not traceable to a scenario and on any scenario with no task, so
decomposition has to produce that mapping rather than leave it to be reconstructed later. Four extra
obligations, all inside the normal procedure:

- **Refuse an unapproved spec.** If `status` is not `approved`, stop and say so. Decomposing a draft
  commits the repo to a contract no human has agreed to, and every task you write inherits it.
- **Cover every scenario exactly once.** Each `S-NNN` maps to at least one task, and every task
  carries the ids it covers in `scenarios` plus the spec path in `spec`. A scenario you deliberately
  do not implement needs a stated rationale, not silence.
- **Split along scenario boundaries, not file boundaries** where the two disagree. A task that
  implements half a scenario cannot be verified against the contract, which is the point of having
  one.
- **Do not restate the spec in the task body.** Point at it. The spec is the contract and it moves;
  a copy in a task file is a second source of truth that will drift.

## Procedure

### Step 1: confirm the system exists and learn its state

1. Confirm `.tasks/` exists. If not, this repo has no work-tracking system yet: point the user to the `init-worktracking` skill and stop.
2. **Check whether `ROADMAP.md` exists**, in the same breath and for the same reason. Its absence is the `init-worktracking` **lite** tier, which ships task files deliberately without a roadmap or a changelog, and it changes what `parent` may name (see Step 4). Absence is a valid state here, not a problem to fix: do not offer to create a roadmap.
3. Read `AGENTS.md`: the section that lists the repo's technical commands (for the acceptance command), the section that states its conventions, and the section that describes the work-altitude model. Read `.tasks/_TEMPLATE.md` for the exact frontmatter shape.
4. Determine the next available id per type. Prefer `.tasks/.scaffold.json` `id_high_water`; otherwise scan `.tasks/` and `.tasks/done/` for the highest `NNNN` per `type` and continue from there. Ids are stable and never reused.
5. If the input references a ROADMAP Feature, read that Feature. If it references existing tasks (as dependencies), note their ids and whether they are in `done/`.

### Step 2: elicit intent (ask before decomposing)

Ask only the questions you cannot answer from the repo. Typically:

- What is the observable outcome or the bug's symptom, precisely?
- What is explicitly out of scope?
- Is there a deadline, priority (P0/P1/P2), or dependency on other in-flight work?
- Is there prior art in the codebase to mirror?

If the user gave enough detail, confirm your understanding in one or two sentences rather than interrogating. Match the depth of questioning to the size of the work.

### Step 3: locate the real files (inspection, not assumption)

Before writing `touched_files`, actually find the surface:

- Grep/search for the function, symbol, config key, or behavior named in the request.
- Identify the source file(s) that change and their corresponding test file(s). `touched_files` carries only paths that already exist, so a test file that does not exist yet does not go there: `validate.py --strict` reports a path that is not in the tree, and `--strict` is what a backlog gate runs. Name the path it should be created at in the **Scope** section instead.
- Note the exact scoped test command from the section of `AGENTS.md` that lists the repo's technical commands (for a monorepo, the per-package command that covers these files).

If you cannot find the surface, say so and ask, rather than writing a plausible-looking but wrong `touched_files`.

**Verify any claim you make *about* the code before writing it into the task.** A task body that says "the regex already handles the anchor form" or "the Devanagari filtering lives in `clean()`" is an assertion the implementing agent will build on, and both of those examples are real premise errors caught by agents mid-batch after being written from a quick read rather than a check. Run the function, grep for the symbol, or read the branch. A wrong premise in a task file is worse than a vague one, because vagueness prompts a question and a confident error prompts compliance.

### Step 4: decompose and identify the parent

- Decide whether this is one atomic task or several. Split when the change spans independent surfaces, has internal ordering (use `depends_on`), or is too large to verify with one command. Keep each resulting task atomic.
- Identify the `parent`, in the form the tier Step 1 detected allows:
  - **With `ROADMAP.md`**: the Feature it serves. If none fits, draft a one-line Feature to add to the forward-plan and use it as the parent (offer this addition to the user; do not silently rewrite the roadmap).
  - **Without one (lite)**: one line of free text naming the goal the task serves, matching the form the repo's own `.tasks/_TEMPLATE.md` seeds. Do not propose adding a `ROADMAP.md`, and do not write a `ROADMAP#N` reference into a repo that has no roadmap to resolve it against: the field exists so intent is readable without the roadmap, which does not require one to exist.
- Present the decomposition (titles, ids you will assign, dependencies between them) to the user for a quick confirmation before writing files. This is the last cheap moment to catch a wrong split.

### Step 5: write the task file(s)

For each task, copy `.tasks/_TEMPLATE.md`, assign the next id (filename `<type>-<NNNN>-<slug>.md`, `id` frontmatter equal to the `<type>-<NNNN>` prefix), and fill every section:

- Frontmatter: `id`, `type`, `status: open`, `priority`, `parent`, `depends_on`, `touched_files`, `created` (today, ISO), plus `spec` and `scenarios` when the task came from an approved spec.
- **Problem**: what is wrong or missing and why, pointing at exact code with relative links.
- **Scope**: in-scope change, and an explicit out-of-scope list. Name every file the task will create here, with the exact path it belongs at, because `touched_files` cannot carry a path that does not exist yet and this is the only place the implementing agent can read where a new file goes.
- **Implementation notes**: constraints, intended approach, edge cases, prior art to mirror. Optional if Problem + Scope are unambiguous.
- **Risks and rollback**: only when the deterministic rule above fires. Check it against the `touched_files` you just wrote, since "touches more than one module" is answerable from that list rather than from intuition. Delete the section when it does not apply.
- **Acceptance criteria**: the literal command that must pass, plus concrete checkboxes (new/updated test, existing tests pass, task-specific checks).
- **Definition of done**: keep the template's lifecycle checkboxes.

Follow the repo's own conventions from the conventions section of `AGENTS.md` (do not import another project's style).

### Step 6: self-check and update bookkeeping

1. Run the shipped validator: `python .tasks/validate.py --strict`. Every `touched_files` path already exists by the rule in Step 3, so `--strict` is the mode to check against, and it is the mode a backlog gate in CI runs. Fix anything it flags. Do not hand over a task file that does not pass.
2. If `.tasks/.scaffold.json` exists, update its `id_high_water` for the types you consumed, so the next author does not collide.
3. If you added a ROADMAP Feature, write that one line now (with user assent).

### Step 7: report and offer the handoff

Summarize the task file(s) written with their ids and one-line titles. Then offer, but do not automatically run, the next step: dispatch the batch to `fix-batch` (parallel worktree-isolated agents), noting that only tasks whose `depends_on` are already in `done/` are safe to dispatch immediately. Do not commit anything unless the user asks.

When the tasks came from an approved spec, the handoff to offer is
[`spec-plan-readiness`](../spec-plan-readiness/SKILL.md): it takes the spec and its task
decomposition together, so it runs on the set you just wrote, and dispatch waits on its verdict. That
gate decides whether implementation may begin at all. Report the scenario coverage you produced
(which scenarios map to which tasks, and any deliberately not implemented) so the gate has something
to check rather than something to reconstruct.

## Notes

- One task, one agent, one command that proves it. If you cannot write the proving command, the task is not ready; keep eliciting.
- Prefer several small honest tasks over one big vague one. `fix-batch` parallelizes small independent tasks; it cannot rescue a task whose scope is a wish.
- This skill authors work; it does not do it. Stop after the files are written and validated.

## Conventions

**Task files follow the target repository's conventions, not this kit's.** Take them from the
conventions section of that repo's `AGENTS.md`, and do not import another project's style into a task
file an agent there will execute.

**Your own output**, the decomposition you present and the summary you report, follows the repo's
house-style module (in this kit, [`.agents/rules/house-style.md`](../../rules/house-style.md)):
sentence-case headings, clickable relative links, named sources, no em-dashes. That file is a
swappable default; a downstream adopter may replace it without touching this skill.
