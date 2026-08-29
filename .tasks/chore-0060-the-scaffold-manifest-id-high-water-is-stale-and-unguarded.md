---
id: chore-0060
title: The scaffold manifest's id_high_water is nine chores and two bugs behind the backlog, and it is the source new-task tells an author to prefer
type: chore
status: open
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: []
touched_files:
  - .tasks/.scaffold.json
  - .agents/skills/new-task/SKILL.md
  - .tasks/validate.py
  - tests/test_tasks_validate.py
created: 2026-08-22
---

## Problem

`.tasks/.scaffold.json` records the highest task id in use per type:

```json
  "id_high_water": {
    "bug": 41,
    "feat": 49,
    "chore": 48,
    "epic": 0
  }
```

The backlog says otherwise. Scanning `.tasks/` and `.tasks/done/` for the highest `NNNN` per type
before this review filed anything:

```text
bug:   0043
chore: 0057
feat:  0049
```

Two bugs and nine chores behind. `feat` is current, which is what makes the drift easy to miss: a
reader who spot-checks one type finds it right.

This is not a cosmetic record. [`new-task`](../.agents/skills/new-task/SKILL.md), Step 1.4, tells
an author which source to trust, in this order:

> Determine the next available id per type. Prefer `.tasks/.scaffold.json` `id_high_water`;
> otherwise scan `.tasks/` and `.tasks/done/` for the highest `NNNN` per `type` and continue from
> there. Ids are stable and never reused.

An agent following that instruction as written today assigns `bug-0042` and `chore-0049`, both of
which are taken. `chore-0049` is an open task in `.tasks/`; `bug-0042` is in `.tasks/done/`.

The collision is caught, and only after the work exists. `.tasks/validate.py` reports it:

```python
    for tid, where in ids_seen.items():
        if len(where) > 1:
            err(where[0], f"duplicate id {tid!r} also in: {', '.join(where[1:])}")
```

So the cost is rework rather than corruption: a task file written, named, and cross-referenced
under a stolen id, discovered at the first `--strict` run and renamed by hand along with anything
that already links to it.

The drift has a single cause, and it is a step that nothing enforces. `new-task` Step 6.2 says:

> If `.tasks/.scaffold.json` exists, update its `id_high_water` for the types you consumed, so the
> next author does not collide.

Searched, to establish nothing checks that it happened:
`grep -rn "scaffold.json\|id_high_water" .agents/ .tasks/README.md AGENTS.md CONTRIBUTING.md tests/ scripts/`
returns six hits, all inside `init-worktracking/SKILL.md` and `new-task/SKILL.md`. No validator,
no gate, and no test reads the file. It is a second source of truth for ids, written by hand,
consulted first, and unguarded, which is the same shape as the drifted link rule `chore-0029`
replaced and the unguarded helper copies in
[chore-0059](chore-0059-the-third-and-fourth-copies-of-the-link-helpers-are-unguarded.md).

**This task is one of five in the same class**, grouped 2026-08-22 rather than worked as unrelated errands: a guard that does not guard. The other four are [`chore-0032`](done/chore-0032-links-guard-fires-per-run-not-per-pattern.md), [`chore-0049`](done/chore-0049-a-checker-for-conformance-matrix-citations.md), [`chore-0058`](done/chore-0058-no-gate-link-checks-the-markdown-under-agents-outside-skills.md), and [`chore-0059`](chore-0059-the-third-and-fourth-copies-of-the-link-helpers-are-unguarded.md). `chore-0058` closed 2026-08-27, and `bug-0045` was the sixth and is closed: it found six of seven gates reporting `ok` over a repository containing nothing. **What the grouping asks of whoever works this one**: when you fix it, look for the next member before you finish, because every member of this class so far was found only by looking after the previous one landed. The pattern behind the class is [`chore-0063`](done/chore-0063-the-repository-has-never-written-down-what-it-keeps-learning.md).

## Scope

**In scope:** make the manifest's `id_high_water` unable to fall behind the backlog silently.
Decide the mechanism, then do it once. Three candidates, in rough order of preference:

1. **Check it in `validate.py`.** The validator already computes every id in the tree, so the
   comparison is nearly free: when `.tasks/.scaffold.json` exists and any recorded high-water is
   below the highest id of that type actually present, report it. A warning rather than an error is
   the right severity, matching how that file treats a judgement about what an author meant, and
   `--strict` promotes it, which is what the backlog gate runs.
2. **Derive it and stop storing it.** Delete the field, and change `new-task` Step 1.4 to scan the
   tree, which is already its stated fallback. This removes the second source of truth entirely.
   It costs `init-worktracking` a seeded value on adoption, which Step 5 of that skill writes.
3. **Leave it and change the instruction.** Reverse Step 1.4's preference so the tree wins and the
   manifest is advisory. Cheapest, and it leaves a field in a shipped manifest that means nothing.

Bring the recorded values up to date as part of whichever route is taken, including the ids this
review consumed: `bug` reaches 46 and `chore` reaches 60 once these task files land.

**Out of scope:**

- The `generator`, `version`, `tier`, `created`, and `files` keys. They describe the scaffold, not
  the backlog, and nothing here says they have drifted.
- `init-worktracking`'s seeding step, unless route 2 is taken, in which case removing the field
  from the template it writes is part of the change rather than a follow-on.
- Renaming any existing task. No collision has occurred; this closes the route to one.
- Any change to how ids are formatted or validated. `ID_RE` is not in question.

## Implementation notes

If route 1 is taken, note that `validate.py` ships as a template into other repositories, so the
check must tolerate the manifest being absent, being unreadable, and holding a type this
repository does not use. A scaffolded tree that has never had a `bug` should not be told its
high-water is wrong. Prefer comparing only the types the manifest actually lists.

The twin at `.agents/skills/init-worktracking/templates/validate.py` must receive the identical
change. `test_the_executable_code_is_identical_in_both_copies` compares the whole module AST of the
two copies, so a one-sided edit fails the test suite rather than shipping, which is the guarantee
working as intended and is worth expecting rather than discovering.

Route 2 touches a shipped skill body and the manifest format an adopter may already carry. Say in
the closeout what an adopter with the old field should do, even if the answer is "nothing, it is
ignored".

## Risks and rollback

Required: `touched_files` spans a data file, a skill body, and the validator with its test, which is
more than one module, and route 2 changes a persisted format that adopters already hold on disk.

The realistic failure for route 1 is a warning that fires on a clean adopter tree, which is the one
outcome `validate.py`'s own comments say to design against. Bound it by running the changed
validator against a scaffolded fixture with no manifest and with an empty one before wiring it into
`--strict`.

Reversible by reverting one commit. Under route 2, an adopter's existing manifest keeps a field
nothing reads, which is inert rather than broken.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] `python .tasks/validate.py --strict` passes, and under route 1 a test proves it reports a
      manifest whose recorded high-water is below an id present in the tree.
- [ ] The mechanism chosen is named in the closeout with the two rejected alternatives and why,
      per the Decisions rule in `.tasks/_TEMPLATE.md`.
- [ ] The recorded values, or their removal, are consistent with the backlog at the moment the task
      closes, shown by pasting the scan output beside the file's contents.
- [ ] Under route 1 or 2, `.tasks/validate.py` and the `init-worktracking` template still compare
      equal, which the existing test enforces.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
