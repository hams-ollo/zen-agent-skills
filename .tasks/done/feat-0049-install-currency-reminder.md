---
id: feat-0049
title: Tell a session when its installed copies have drifted from the kit, instead of waiting for someone to think of running --check
type: feat
status: done
priority: P1
parent: "ROADMAP Epic B #19: drift sensors that run outside the change lifecycle"
depends_on: []
touched_files:
  - .agents/hooks/README.md
  - .codex/hooks.json
  - .opencode/plugins/zen-hooks.mjs
  - scripts/install.py
  - docs/CATALOG.md
  - tests/test_hooks.py
created: 2026-08-18
---

## Problem

Measured on the author's own machine, 2026-08-18, after ten days away:

```text
$ python scripts/install.py --check
0 current, 0 diverged, 0 linked, 0 revised upstream, 42 unknown, 0 error(s).
```

Eighteen installed skills were stale, `review-depth` had never been installed at all,
`.agents/rules/autonomy.md` was absent from both homes, `skill-reachability-reminder.py` was absent
from both homes, and the installed `review-quality.md` was 70 lines against the kit's 207. That state
had persisted for an unknown period. **Nothing reported it.** It was found because a review pass
happened to diff two files by hand.

Every gate stayed green throughout, and correctly so: none of them looks at an install.
`run-checks.py` runs `install.py --dry-run` against a throwaway home in `.tmp/`, which proves the
installer works and says nothing about the real one.

The kit already owns the answer and cannot reach it. Three facts compose into the gap:

1. `install.py --check` decides currency correctly, but only when a human thinks to run it, and
   nothing prompts them.
2. [`skill-reachability-reminder.py`](../../.agents/hooks/skill-reachability-reminder.py) already fires
   at every `SessionStart` and already knows the home. It deliberately does not answer this, and says
   so in its own message: *"it matches skill directories by name, so it confirms they exist, not that
   they are current or that they are this kit's copies. Run `python scripts/install.py --check` for
   that."* So the one thing that runs automatically hands the question back to the human.
3. `MANIFEST = REPO_ROOT / "scripts" / ".install-manifest.json"`
   ([`install.py:85`](../../scripts/install.py)) puts the record **in the source repository**, and a
   manifest entry carries `tool`, `name`, `target`, `mode`, `source` and `digests` with no timestamp.
   An installed skill therefore has no back-pointer to where it came from.

Fact 3 is the structural half and it bounds what this task can honestly fix. Currency is decidable
only from a machine that has the source repository, because that is the only place the comparison
material exists. A session in some unrelated repository cannot answer it at any price, which is why
this task does not try.

## Scope

**In scope:** a new reminder hook that answers the currency question in the one situation where it is
cheap and decidable, namely a session whose project root is a repository holding
`scripts/.install-manifest.json`. When it is, the hook compares the manifest's recorded digests
against that repository's working tree and emits one reminder when the install is stale, when entries
carry no digests at all (the `unknown` state above, where the kit's own currency sensor is
inoperative and nothing says so), or when a skill present in the tree is absent from the manifest.

- **Two new files**, not listed in `touched_files` because that field carries only paths that already
  exist, matching [`feat-0046`](feat-0046-session-start-reachability-hook.md), which created a
  hook and a test module and listed neither:
  `.agents/hooks/install-currency-reminder.py`, in the reminder shape, one job, per the module
  contract in [the hooks README](../../.agents/hooks/README.md); and `tests/test_hooks_currency.py` for
  its behavior.
- Its row in that README's table and in the hooks table in [`CATALOG.md`](../../docs/CATALOG.md).
- Registration in all three adapters, since the hook file is the single source of truth and each
  harness gets a thin pointer: the block `install.py` prints for `--with-hooks`, `.codex/hooks.json`,
  and `.opencode/plugins/zen-hooks.mjs`.
- Tests, including the wiring-consistency assertions in [`test_hooks.py`](../../tests/test_hooks.py)
  that already pin every hook to a registration.

**Out of scope:**

- **The general adopter case**, where the source repository is not present. It is not solvable
  without a new install-time surface, and that is ROADMAP item 19's question, not this one. Say so in
  the hook's docstring so the boundary is visible where someone would otherwise widen it.
- **Adding a timestamp, a version marker, or any other field to the manifest or the install home.**
  That changes the install surface and would require amending
  [`install.md`](../../docs/spec/install.md) under the amendment convention, which is
  [`chore-0033`](../chore-0033-amend-install-spec-for-check-and-with-hooks.md)'s territory and a
  different decision.
- **Extending `skill-reachability-reminder.py`.** See the implementation notes.
- **Registering the new hook in `.claude/settings.json`.** The conventions section of `AGENTS.md`
  records exactly one committed hook registration as a deliberate exception, in the reminder shape,
  and this task does not spend that exception.
- **Making it a gate.** A stale install is a condition a human should see, not one that should stop
  work. Reminders never block.
- **Re-installing anything.** The hook reports; the human runs the installer.

## Implementation notes

**A new hook rather than an extension of the reachability one.** The module contract is one hook, one
job, obvious from the docstring, and the reachability hook's published message explicitly disclaims
currency. Folding currency into it would make that message wrong and would give one file two firing
conditions with different costs: reachability is a directory-name match, currency reads and digests
files. Keep them separate and let both fire on `SessionStart`.

**Cost is the thing to get right, because this runs at every session start.** Digesting every
installed file on every start is not acceptable. Read the manifest first and decide from it: if it is
absent, exit silently, which is the common case for a session outside this repository and is the
whole two-stage filtering idea the module contract already describes. Only when the manifest is
present is any digesting justified, and even then prefer comparing against the recorded digests
rather than re-deriving both sides.

**Reuse, do not reimplement.** `install.py` already has the entry-checking logic behind `--check` and
already distinguishes `current`, `diverged` and `unknown`. The hooks contract forbids importing from
this repository, so the hook cannot call it directly; that constraint is deliberate and stands. What
the hook must not do is invent a fourth verdict or a different meaning for the three that exist.
Mirror the vocabulary exactly, and where the logic is genuinely duplicated, assert the agreement in a
test rather than trusting it, the way [`bug-0026`](bug-0026-scaffolded-validator-lost-the-external-check.md)
asks for its two validator copies.

**The silence problem applies to this hook too.** A reminder that finds nothing and a reminder that
crashed both produce no output, which is the failure `bug-0021` recorded when the reachability hook
was measured in a live cloud session and emitted nothing for the wrong reason. Test both directions
explicitly: a stale manifest must produce a message, and a current one must produce none. Proving it
can speak is not optional, and neither test is meaningful without the other.

**Prior art for the shape** is `skill-reachability-reminder.py` itself: `FIRING_SOURCES`, an
`evaluate(payload, home=None)` seam that a test can drive without touching the real home, and
`main(stdin=None, stdout=None)`. Follow it rather than inventing a second shape.

## Decisions

- **Premise that turned out false: `install.py --check` has six states, not three.** This task's
  acceptance criteria and implementation notes say "three states" and name `current`, `diverged` and
  `unknown`, which are three of the six words the printed summary uses. `_check_entry` classifies
  `ok`, `linked`, `revised`, `diverged`, `unknown` and `error`, and `check()` counts all six. The hook
  mirrors all six, and `test_hooks_currency.py` asserts set equality against the `counts` dict parsed
  out of `install.py`, which is the stronger reading of the criterion's operative clause that neither
  side may gain a state the other lacks.
- **Rejected alternative: comparing the installed tree instead of the recorded baseline.** The hook
  compares the manifest's recorded digests against this working tree, per the Scope, so it answers
  "has the kit moved since you installed" and never opens an install home. `--check` compares the
  installed tree against the source, so it also catches a file the adopter edited after installing.
  The hook cannot see that and its docstring says so. Reading the home would cost a second full
  digest at every session start to answer a question `--check` already answers on demand.
- **Seam left open deliberately: `revised` is classified but never reported.** `--check` exits 0 on
  it and leaves the adopter's lens alone, so firing every session about a file they were invited to
  rewrite is exactly the cry-wolf failure the reachability hook's docstring rejects markers for.
  `REPORTING_VERDICTS` names the three that speak, and a test pins the complement.
- **Seam left open deliberately: a narrow `--profile` produces false "never installed" lines.**
  Drafts are excluded, because they are deliberately not installed and a shipped draft would
  otherwise make the hook fire on a correct install. A profile's deselected skills are not
  excludable, because the manifest records no profile, so the message names the profile reading
  alongside the never-installed one rather than pretending it is not there. Closing this needs a
  field in the manifest, which is out of scope here for the reason the Scope already gives.
- **Rejected alternative: reading the recorded `mode` to spot a symlinked entry.** The filesystem is
  read instead, matching `_check_entry`, because a copy can replace a link between runs and trusting
  the record would report `linked` for a copy that really had gone stale.

## Risks and rollback

Touches a new hook, the module contract, three adapter registrations, the installer's printed block,
a reader-facing document, and two test modules, so the more-than-one-module rule fires.

The registration surface is where this fails invisibly. A hook registered on an event the harness
never fires, or pointed at a path that does not resolve, produces exactly the same observable as a
hook that ran and found nothing. `install.py:341` already records that a hook on an unregistered
event is placed and never fires, and `chore-0038` item 3 recorded a registration that resolved only
from the repository root. Verify by running the hook through each registered command from at least
two working directories, not by reading the registrations.

The second risk is cost. If the manifest check is not the first thing the hook does, every session
start on the machine pays for it. Measure the no-manifest path and state the measurement in the
closeout.

Reversible by reverting one commit. Nothing persists state, and an unregistered hook is inert.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [x] A manifest recording digests that no longer match the working tree produces exactly one
      reminder naming what drifted, proven by a test.
- [x] A manifest whose entries carry no digests produces a reminder saying the currency check is
      inoperative until a baseline is recorded, proven by a test.
- [x] A manifest that matches the working tree produces no output and exits 0, proven by a test, so
      silence is demonstrated to mean current rather than broken.
- [x] No manifest present produces no output, exits 0, and reads no other file, proven by a test.
- [x] The hook's verdict vocabulary matches `install.py --check`'s three states, and a test fails if
      either side gains a state the other lacks.
- [x] The hook is registered in all three adapters, the existing wiring-consistency assertions in
      `tests/test_hooks.py` cover it, and the registered command resolves from a subdirectory as well
      as from the repository root.
- [x] The hooks README table and the CATALOG hooks table both list it, with its shape (reminder) and
      firing event.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
