---
id: bug-0062
title: A refused adapter run still leaves earlier skills' files on disk, so goal 6's no-partial-result promise is half kept
type: bug
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [bug-0060]
spec: docs/spec/build-adapters.md
scenarios: []
touched_files:
  - scripts/build-adapters.py
  - tests/test_build_adapters.py
created: 2026-08-31
---

## Problem

[`bug-0060`](done/bug-0060-a-frontmatter-name-can-write-outside-the-adapter-output-root.md) closes the
path escape and refuses the run at exit 2. It refuses **inside** the per-skill loop in `_main`, so
every skill sorted before the offending one has already been emitted by the time the refusal fires.

Goal 6 of [`build-adapters.md`](../docs/spec/build-adapters.md) is "fail clearly on an unusable
invocation rather than writing a partial result", and `bug-0060`'s own Scope quotes it as the reason
the refusal is run-level rather than a skipped skill. Half of that is now true: the run fails
clearly. The other half is not.

**Measured during `bug-0060`'s independent verification**, on a two-skill fixture with the good
skill sorted first and the bad one second:

```text
base : exit=0  inside out: ['.cursor/rules/aaa-good.mdc', '.github/prompts/aaa-good.prompt.md']
               outside out: ['escaped.mdc', 'escaped.prompt.md']
fixed: exit=2  inside out: ['.cursor/rules/aaa-good.mdc', '.github/prompts/aaa-good.prompt.md']
               outside out: []
```

The escape is gone, which is the bug `bug-0060` was for. The earlier skill's two files remain, and
the run that wrote them reported failure.

This matters more for this tool than the general case, because `--out` defaults to the working
directory, so a partial result lands in whatever project invoked it. `S-017` already reasons about
exactly that hazard from the target-selection end.

## Scope

**In scope:** an unusable tree writes nothing at all.

- A pre-pass over every discovered skill's frontmatter `name`, before the first emitter is
  dispatched, applying the same rule `_main` already applies per skill. The run refuses on the whole
  set or proceeds on the whole set.
- Report every offending skill the pre-pass finds, not only the first, so one run tells an adopter
  everything they have to fix.
- A test asserting that a tree with one bad skill among several leaves **nothing** under the output
  root, not merely nothing outside it. That is the assertion the current tests do not make.
- **Tie `NAME_DESTINATIONS`' keys to the inlining subset of `EMITTERS`**, with an assertion or a
  test. Nothing relates the two mappings today, so an inlining target added to `EMITTERS` and not to
  `NAME_DESTINATIONS` would make a refusal print "no requested target derives a destination from
  it", which would be false. The consequence is a misleading message rather than an escape, since
  `_write`'s containment guard still refuses the write, which is why it rides along here rather than
  carrying its own task. The pre-pass this task adds walks names and targets, so it is the change
  that makes the coupling load-bearing.

**Out of scope:**

- The containment check at `_write`. It stays exactly where `bug-0060` put it: the pre-pass is a
  second line of defence in front of it, not a replacement, and removing the boundary check would
  reintroduce the escape for any path the name rule does not cover.
- Transactional emission, a staging directory, or rollback of files already written. The pre-pass
  makes the refusal precede all writing, which is cheaper and sufficient. A rollback mechanism is a
  much larger change and nothing has asked for one.
- Any behaviour when the tree is valid. A good run must be byte-identical, same file count, same
  destinations, same stdout.
- The spec amendment, which belongs with
  [`chore-0087`](chore-0087-amend-the-build-adapters-spec-for-destination-containment.md) if that
  task's scenario is widened to cover it, or to its own task if not.

## Implementation notes

`discover_skills()` already returns the full sorted list before the loop starts, so the pre-pass has
everything it needs and costs one extra `split_frontmatter` per skill. Reading each `SKILL.md` twice
is the obvious cost; caching the parsed frontmatter from the pre-pass and reusing it in the emit
loop avoids it and is probably worth doing, since `read_text_utf8` can raise `NotUTF8` and doing
that twice gives two chances to report the same failure differently.

`emit_rules_module` runs before the per-skill loop today and writes the shared material, so the
pre-pass has to come before that call as well, not merely before the loop. This is the detail that
makes the fix slightly less trivial than it sounds, and it is the one to get right.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] A tree with one offending skill among several leaves **no file at all** under the output root,
      asserted on the filesystem.
- [ ] That test fails against the current code. Confirm the failure before the fix.
- [ ] The refusal names every offending skill, not only the first.
- [ ] The shared rules module is not written either, so the pre-pass precedes `emit_rules_module`.
- [ ] A valid tree emits byte-identical output: same file count, same destinations, same stdout as
      before the change.
- [ ] `--dry-run` refuses the same input a real run refuses.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
