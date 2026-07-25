---
name: new-task
description: Author one or more atomic, agent-ready task files for the .tasks/ work-tracking system, at a gold-standard bar. Turns a rough idea, a bug report, or a ROADMAP.md Feature into task files with honest touched_files, a real parent up-link, resolved depends_on, and a mechanically-verifiable acceptance command, then self-checks them with validate.py. Deliberately elicits and decomposes before writing, because a sharp task is worth 3-10x its authoring time downstream. Assigns collision-safe ids from the existing backlog. Use when the user says "write a task for X", "add this to the backlog", "spec out this bug", "turn this into task files", "break this feature into tasks", or hands over an idea they want made executable. Requires an existing .tasks/ system (run init-worktracking first if absent). Feeds fix-batch: one task file per worktree-isolated agent.
---

# new-task

Author task files that an isolated agent can execute without asking questions. This is the upstream of the work-tracking spine: `new-task` (author) -> `init-worktracking` (the system it writes into) -> `fix-batch` (parallel agents) -> `reconcile-worktrees` (merge back). The quality of everything downstream is capped by the quality of the task file, so this skill spends effort up front on purpose.

## The bar a task file must clear

A good task is self-contained: an agent that reads only `AGENTS.md`, the task file, and the files listed in `touched_files` can finish it correctly. Concretely, every task you write must have:

- **Honest `touched_files`**: the complete read/write surface, discovered by inspecting the repo, not guessed. Too narrow and the agent is blocked; too wide and it wanders and collides with parallel agents.
- **A real `parent`**: the ROADMAP Feature/Epic it serves, so intent is traceable without reading the roadmap. If no Feature fits, propose adding one.
- **Resolved `depends_on`**: ids of tasks that must reach `done/` first; `[]` if none. Never invent an id.
- **A mechanically-verifiable acceptance command**: an exact command (usually the repo's test command scoped to the change) that passes only when the work is done. Not "tests pass" in prose, the literal command.
- **Tight scope with an explicit out-of-scope**: so a well-meaning agent keeps the change atomic.

## Why this skill blocks a little

Both the `spec`/`brainstorm` patterns in mature agent frameworks and hard experience say the same thing: jumping straight to code on an underspecified task wastes far more time than the few minutes of elicitation. So this skill asks its questions and shows its decomposition before writing files. That friction is the feature. Do not skip it for anything non-trivial.

## Procedure

### Step 1: confirm the system exists and learn its state

1. Confirm `.tasks/` exists. If not, this repo has no work-tracking system yet: point the user to the `init-worktracking` skill and stop.
2. Read `AGENTS.md`: the section that lists the repo's technical commands (for the acceptance command), the section that states its conventions, and the section that describes the work-altitude model. Read `.tasks/_TEMPLATE.md` for the exact frontmatter shape.
3. Determine the next available id per type. Prefer `.tasks/.scaffold.json` `id_high_water`; otherwise scan `.tasks/` and `.tasks/done/` for the highest `NNNN` per `type` and continue from there. Ids are stable and never reused.
4. If the input references a ROADMAP Feature, read that Feature. If it references existing tasks (as dependencies), note their ids and whether they are in `done/`.

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
- Identify the source file(s) that change and their corresponding test file(s). If a test file does not exist yet, include the path it should be created at.
- Note the exact scoped test command from the section of `AGENTS.md` that lists the repo's technical commands (for a monorepo, the per-package command that covers these files).

If you cannot find the surface, say so and ask, rather than writing a plausible-looking but wrong `touched_files`.

### Step 4: decompose and identify the parent

- Decide whether this is one atomic task or several. Split when the change spans independent surfaces, has internal ordering (use `depends_on`), or is too large to verify with one command. Keep each resulting task atomic.
- Identify the parent ROADMAP Feature. If none fits, draft a one-line Feature to add to `ROADMAP.md` forward-plan and use it as the parent (offer this addition to the user; do not silently rewrite the roadmap).
- Present the decomposition (titles, ids you will assign, dependencies between them) to the user for a quick confirmation before writing files. This is the last cheap moment to catch a wrong split.

### Step 5: write the task file(s)

For each task, copy `.tasks/_TEMPLATE.md`, assign the next id (filename `<type>-<NNNN>-<slug>.md`, `id` frontmatter equal to the `<type>-<NNNN>` prefix), and fill every section:

- Frontmatter: `id`, `type`, `status: open`, `priority`, `parent`, `depends_on`, `touched_files`, `created` (today, ISO).
- **Problem**: what is wrong or missing and why, pointing at exact code with relative links.
- **Scope**: in-scope change, and an explicit out-of-scope list.
- **Implementation notes**: constraints, intended approach, edge cases, prior art to mirror. Optional if Problem + Scope are unambiguous.
- **Acceptance criteria**: the literal command that must pass, plus concrete checkboxes (new/updated test, existing tests pass, task-specific checks).
- **Definition of done**: keep the template's lifecycle checkboxes.

Follow the repo's own conventions from the conventions section of `AGENTS.md` (do not import another project's style).

### Step 6: self-check and update bookkeeping

1. Run the shipped validator: `python .tasks/validate.py` (or `--strict` if every `touched_files` path already exists). Fix anything it flags. Do not hand over a task file that does not pass.
2. If `.tasks/.scaffold.json` exists, update its `id_high_water` for the types you consumed, so the next author does not collide.
3. If you added a ROADMAP Feature, write that one line now (with user assent).

### Step 7: report and offer the handoff

Summarize the task file(s) written with their ids and one-line titles. Then offer, but do not automatically run, the next step: dispatch the batch to `fix-batch` (parallel worktree-isolated agents), noting that only tasks whose `depends_on` are already in `done/` are safe to dispatch immediately. Do not commit anything unless the user asks.

## Notes

- One task, one agent, one command that proves it. If you cannot write the proving command, the task is not ready; keep eliciting.
- Prefer several small honest tasks over one big vague one. `fix-batch` parallelizes small independent tasks; it cannot rescue a task whose scope is a wish.
- This skill authors work; it does not do it. Stop after the files are written and validated.
