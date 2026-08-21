---
id: chore-0052
title: The committed hook registration defends its interpreter choice with a counterfactual the 2026-08-21 cloud run falsified
type: chore
status: done
priority: P2
parent: "ROADMAP Epic E: delegated execution"
depends_on: []
spec: "docs/spec/cloud-executable.md"
scenarios: []
touched_files:
  - .claude/settings.json
created: 2026-08-21
---

## Problem

[`.claude/settings.json`](../../.claude/settings.json) is the kit's one committed hook registration, and
its `_comment` block carries the decision record for that exception. Defending the `python3`
interpreter, it asserts:

```text
The first draft said `python` and would have failed to launch in the exact
environment the exception was granted for, emitting nothing while the session
proceeded, which is indistinguishable from skills being reachable.
```

**Observation 3 of the 2026-08-21 reachability run falsifies the counterfactual**, on the platform the
sentence is about:

```text
$ command -v python3 ; command -v python ; python3 --version ; uname -s
/usr/local/bin/python3
/usr/local/bin/python
Python 3.11.15
Linux
```

`python` is present. The first draft would have launched.

**The choice of `python3` is correct and is not in question.** It is the safer default across
environments, and the `feat-0038` hazard it cites from the other direction, `python3` on Windows
resolving to the Store alias, is real and observed. What is wrong is the specific claim used to make
the choice sound settled, and the block's own closing sentence is the tell:

```text
Found by independent verification before any cloud run, not after.
```

That is accurate about the process and is exactly the defect. The claim was verified against reasoning
rather than against the environment, and the 2026-08-21 run is the first evidence ever gathered on it.

Why this is worth a task rather than a quiet edit: the block is a **decision record** for the one
place this kit activates a hook on an adopter's behalf, `AGENTS.md`'s conventions section points at it
for the reasoning, and a future reader weighing whether to add a second hook will read these sentences
as established fact. A record that carries one measurably false supporting claim invites either
distrust of the whole block or repetition of the claim.

## Scope

**In scope:** make the interpreter rationale say what is now known.

- Replace the falsified counterfactual with the measurement: both interpreters are present on the
  cloud platform as of 2026-08-21, so `python` would have launched there.
- Keep the decision and restate its actual grounds: `python3` is the portable default, `python` is
  absent on many Linux distributions and on macOS since 12.3, and the Windows Store-alias failure in
  `feat-0038` is the observed hazard in the other direction.
- Correct or drop the closing "Found by independent verification before any cloud run, not after",
  which is what made a reasoned claim read as a verified one.
- Date the measurement and name its source, so the next reader can tell evidence from argument.

**Out of scope:**

- **Changing the interpreter.** `python3` stays. This task corrects why, not what, and a task that
  touched the command would need to weigh the `feat-0038` hazard rather than inherit this finding.
- The rest of the `_comment` block, whose other claims are unaffected and several of which the same
  run confirmed.
- Adding a second hook, or widening the exception. `AGENTS.md` states that is a new decision, and it
  still is.
- [`AGENTS.md`](../../AGENTS.md)'s own conventions section, which points at this file for the reasoning
  and does not restate the interpreter claim. Confirm that rather than assuming it; if it does restate
  it, it is in scope after all.
- The `docs/spec/cloud-executable.conformance.md` observation recording this finding, written at the
  same time as this task and already correct.

## Implementation notes

`.claude/settings.json` is JSON with no comment syntax, so the prose lives in a `_comment` array of
strings and every line is a separate array element. Edit it as JSON, not as prose with line breaks, or
the file stops parsing and the hook stops being registered at all, which fails silently in exactly the
way the block is about.

Keep the block's voice. It is written as a record of a decision and its reasons, not as documentation,
and the correction should read as the same person having learned something rather than as an
annotation bolted on.

State the platform the measurement came from. "Both are present" is true of one cloud container on one
date and is not a claim about every environment, which is the same distinction the original sentence
lost.

## Risks and rollback

One file, and it is the one committed file that changes an adopter's session behaviour, so this
section is required even though the change is prose.

The risk is not the prose, it is the parse. A malformed `settings.json` disables the hook silently,
and no gate here reads that file: `run-checks.py` does not validate it, and nothing tests it for
well-formedness. Verify with `python -c "import json; json.load(open('.claude/settings.json'))"`
before finishing, and confirm the `hooks` object is byte-identical to what it was, since only the
`_comment` array should change.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] `python -c "import json; json.load(open('.claude/settings.json'))"` exits 0.
- [x] The `hooks` object is unchanged, proven by comparing it against the previous revision rather
      than by inspection.
- [x] The falsified counterfactual is gone, and no replacement sentence asserts what `python` would
      have done in an environment nobody measured.
- [x] The interpreter is still `python3`.
- [x] The rationale names the 2026-08-21 measurement, its platform, and both paths it found.
- [x] `AGENTS.md` checked for a restatement of the same claim, and the result stated either way.
- [x] Existing tests still pass, unchanged in intent.

## Decisions

- **A seam left open deliberately.** Two other places in the repository restate the same falsified
  counterfactual, and neither was touched because neither is in `touched_files` and the task's scope
  section names only the conformance file's observation as out of scope, not its matrix rows. They
  are: the `Bootstrap registration committed in .claude/settings.json` row in
  [`cloud-executable.conformance.md`](../../docs/spec/cloud-executable.conformance.md), which says the
  hook "would not have launched in the exact environment the committed-settings exception was granted
  for" and closes "Caught by independent verification before any cloud run"; and the
  `CommittedRegistrationTests` class docstring in [`test_hooks_reachability.py`](../../tests/test_hooks_reachability.py),
  which says "The failure would have been silent in the worst available way". The test's assertion is
  unaffected (`python3` is still correct), only its stated reason is. Left for a follow-up rather than
  widened into here.
- **Rejected: deleting the closing "Found by independent verification before any cloud run, not
  after".** The task allowed correcting or dropping it. It is kept and turned around instead, because
  the sentence is the record of how the error happened, and deleting it removes the only trace of why
  a reasoned claim read as a verified one.
- **Confirmed rather than assumed:** `AGENTS.md` does not restate the interpreter claim.
  `grep -n -i "python3\|interpreter\|first draft" AGENTS.md` returns nothing, so the out-of-scope
  clause holds and no edit was needed there.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
