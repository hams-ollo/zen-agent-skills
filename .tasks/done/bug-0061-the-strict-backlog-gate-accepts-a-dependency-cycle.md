---
id: bug-0061
title: The strict backlog gate accepts a dependency cycle, in both copies of the validator
type: bug
status: done
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - .tasks/validate.py
  - .agents/skills/init-worktracking/templates/validate.py
  - tests/test_tasks_validate.py
created: 2026-08-31
---

## Problem

[`validate.py`](../validate.py) checks two things about each `depends_on` entry and nothing about the
graph they form:

    for dep in fm.get("depends_on", []) or []:
        if dep == tid:
            err(rel, f"depends_on lists itself: {dep}")
        elif dep not in all_ids:
            err(rel, f"depends_on unresolved: {dep!r} is not a known task id")

A task naming itself is caught. Two tasks naming each other are not, and neither is any longer ring.
`all_ids` is fully populated by this point, so the information needed is present and unused.

The consequence is specific to how this backlog is dispatched. The lifecycle rule in
[`AGENTS.md`](../../AGENTS.md) is that a task is dispatchable once every id in its `depends_on` is in
`.tasks/done/`, and `fix-batch` applies it. Neither member of a cycle can ever satisfy that, so the
gate certifies as valid a pair that is permanently undispatchable, and the only thing that surfaces
it is a person noticing that a batch has nothing ready.

**Measured on 2026-08-31**, in temporary trackers that were removed afterwards. Two otherwise valid
tasks naming each other:

```text
repo:              exit=0  Checked 2 task files: 0 error(s), 0 warning(s).
scaffold template: exit=0  Checked 2 task files: 0 error(s), 0 warning(s).
```

**The gap is in both copies, and that is the load-bearing half of this task.**
[`templates/validate.py`](../../.agents/skills/init-worktracking/templates/validate.py) is the file
`init-worktracking` scaffolds into an adopter's repository, and it carries the same two checks with
the same omission. `bug-0026` is the recorded incident for fixing only one of them: the `external`
guard and the injectable `main(argv=None)` landed in the copy that authored them, so "every
repository the kit scaffolds got the feature `pr-describe` ships and none of the check that makes it
safe". [`test_tasks_validate.py`](../../tests/test_tasks_validate.py) drives both copies from one
fixture for exactly that reason, and this fix has to arrive through that pairing rather than beside
it.

## Scope

**In scope:** a dependency cycle of any length is an error under `--strict`.

- Build the graph once, after the parse loop that fills `all_ids`, and report **every** cycle rather
  than the first one found.
- Each report names the ordered path that closes the ring, so the reader can see which edge to cut
  without reconstructing it: `feat-0098 -> feat-0099 -> feat-0098`.
- The same change in both copies, in the same commit.
- Tests for a two-node cycle and a three-node cycle, run against both copies through the existing
  paired fixture.

**Out of scope:**

- The existing `depends_on lists itself` diagnostic. It stays: a one-node ring reported as a cycle
  path is a worse message than the direct one, and the direct check is what a reader gets first.
- Edges into `.tasks/done/`. A dependency that is already done is satisfied, not a cycle, and the
  graph must include done ids or every completed dependency becomes a false positive.
- Warning on a long-but-valid dependency chain, or any depth limit. Not a defect, and a bound with
  no observed case behind it is a guess with a number on it.
- `fix-batch`, which reads the same field and is not where the check belongs.

## Implementation notes

Standard library only, per the conventions section of `AGENTS.md`. An iterative depth-first search
carrying its own stack is the shape to use: the recursive form is the obvious one and this runs over
a directory of arbitrary size on three platforms, so a recursion limit is a real failure mode and an
uninteresting one.

Report cycles deterministically. Iterate ids in sorted order and normalise each reported ring to
start at its lowest id, so the same backlog produces the same output on every run and on every
platform. A gate whose message text varies by dictionary ordering is a gate whose output cannot be
diffed.

`err()` is the existing reporting seam and takes a file-relative path. A cycle belongs to a set of
files rather than to one, so decide where it is reported: attaching it to the lowest-id member and
naming the whole path in the message keeps the existing signature and reads correctly. Whatever is
chosen, the count line, `Checked N task files: X error(s)`, has to stay accurate, because
`run-checks.py` parses it.

The two copies are not byte-identical, so apply the change to each rather than copying one file over
the other.

## Decisions

- **Rejected: enumerating every elementary cycle.** Johnson's algorithm, or a simple-path walk
  restarted at every node, reports rings that a back-edge search can miss: one whose nodes all sit
  inside a subtree the walk has already finished hides behind the ring reported there. Both are
  exponential in the worst case, and this gate has to finish on somebody else's backlog, so the
  back-edge search is what shipped. The bound is written into `dependency_cycles()`'s own docstring
  rather than left to be rediscovered, along with the recovery: a hidden ring surfaces on the next
  run, once the edge that was named is cut.
- **Rejected: reporting a cycle as a warning that `--strict` promotes.** That is the shape the two
  other checks shipping into adopter trees use, and it is wrong here for the reason those two give
  in their own comments: they report a judgement (a link that may be mislabelled, a manifest that
  may be stale) and a ring is a fact. `depends_on lists itself` is already an unconditional `err()`,
  and a cycle is the same claim over a longer path.
- **Seam left open deliberately: both README copies still enumerate the old check set.**
  [`.tasks/README.md`](../README.md) and
  [`tasks-README.md.tmpl`](../../.agents/skills/init-worktracking/templates/tasks-README.md.tmpl) carry
  one identical sentence beginning "It verifies frontmatter schema, id uniqueness, that every
  `depends_on` resolves to a real task", which this change leaves incomplete in the same two places
  the validator was. Both are outside this task's `touched_files`, so it is reported as a finding
  and not applied here.

## Risks and rollback

Both copies of a distributed tool change together, which is two audiences: this repository's own
backlog gate, and every repository `init-worktracking` has scaffolded or will scaffold. A false
positive here fails CI for an adopter over a backlog that is actually fine, which is the failure
mode that gets a check switched off.

The mitigation is the acceptance criterion below: run the new code over this repository's real
backlog and require zero cycles reported. Rollback is reverting the one commit; the change adds a
check and holds no state, so nothing has to be undone in either tree, and a scaffolded repository
that already received the fix keeps a strictly more capable validator.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] A two-node cycle is reported as an error under `--strict`, with a non-zero exit.
- [x] A three-node cycle is reported as an error under `--strict`, with a non-zero exit.
- [x] Both cases run against **both** copies of the validator, through the existing paired fixture in
      `test_tasks_validate.py`.
- [x] Those tests fail against the current code. Confirm the failure before the fix.
- [x] The existing `depends_on lists itself` message still fires for a one-node case, unchanged.
- [x] A task depending on an id that is already in `.tasks/done/` is still valid.
- [x] Run against this repository's real `.tasks/` tree, `--strict` reports zero cycles and the same
      error and warning counts as before the change.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
