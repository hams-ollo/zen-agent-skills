---
id: bug-0021
title: The reachability bootstrap counts a foreign skill library as reachable, so it is silent in the cloud session it exists for
type: bug
status: open
priority: P1
parent: "ROADMAP Epic E #2: make this repository cloud-executable"
depends_on: []
spec: "docs/spec/cloud-executable.md"
scenarios: ["S-008", "S-010"]
touched_files:
  - .agents/hooks/skill-reachability-reminder.py
  - tests/test_hooks_reachability.py
  - docs/spec/cloud-executable.md
created: 2026-08-08
---

## Problem

`_has_skill()` in [`skill-reachability-reminder.py`](../.agents/hooks/skill-reachability-reminder.py)
returns true for **any** directory containing a `SKILL.md`. The contract asks a narrower question.
The Proposed Surface row in [`cloud-executable.md`](../docs/spec/cloud-executable.md) reads "at least
one **kit skill** directory present at the repository's project-scope discovery directory, or at any
user-scope discovery directory `install.py` targets", and `S-008`'s **Given** is "a clone where no
**kit skill** is present at project scope or at any user-scope discovery directory".

So a machine carrying somebody else's skill library satisfies the implementation and not the
contract, and the hook stays silent in exactly the state `S-008` says it must speak.

Measured 2026-08-08 in a live cloud session on branch
`claude/developer-branch-review-j26u9s`, with none of this kit installed:

```text
$ echo '{"hook_event_name":"SessionStart","source":"startup","cwd":"/home/user/zen-agent-skills"}' \
    | python3 .agents/hooks/skill-reachability-reminder.py
(no output)

$ ls ~/.claude/skills | head
algorithmic-art  brain-dump  brand-guidelines  canvas-design
docx  pdf  pptx  xlsx  skill-creator  theme-factory      ... 24 total

$ reachable(repo_root, Path.home())
True
```

None of those 24 directories belongs to this kit. `doc-sync`, `fix-batch`, `house-review`,
`new-task`, `verifier-agent`, and `spec-author` are all absent, and the session proceeded with the
report suppressed.

**This falsifies a recorded prediction.**
[`cloud-executable.verification.md`](../docs/spec/cloud-executable.verification.md) writes seven
falsifiable predictions before the Phase 4 proof run. Prediction 1 is *"The session reports `NO
SKILLS REACHABLE` at startup (`S-008`), falsified if nothing appears, or it appears when skills were
reachable."* Nothing appeared. The proof run is still owed, and running it against the current code
would produce a result nobody can read: "nothing appeared" would be indistinguishable between a
broken hook and a correct hook meeting a populated home.

**The failure shape is the one the hook was written to remove.** A cloud container that ships its own
`~/.claude/skills` is not an edge case, it is the default on the platform this epic targets, so the
committed `.claude/settings.json` exception buys nothing where it was granted. The module docstring
does say "it cannot tell whose skills it found", but that sentence only ships inside `REPORT`, the
string that never prints when the hook is silent.

## Scope

**In scope:** make `reachable()` answer the contract's question. Decide and implement how a kit skill
is recognised at a discovery directory, extend
[`test_hooks_reachability.py`](../tests/test_hooks_reachability.py) with a case that fails against the
current hook, and reconcile `cloud-executable.md` with whatever is built.

**Out of scope:**

- Any environment detection. `S-016` forbids it, and a populated foreign home is not a cloud signal.
- Currency. `S-011` is unchanged: the hook answers reachability and never claims the skills are
  current. Do not call `install.py --check` from the hook, for the reason its own docstring gives.
- Widening `.claude/settings.json` beyond the one reminder registered there. That exception is
  written up in the conventions section of [`AGENTS.md`](../AGENTS.md) and is not this task's to
  bend.
- The Phase 4 proof run itself. This task makes its result readable; it does not run it.

## Implementation notes

Three candidate recognitions, and the choice is the task's real work. State which was taken and why
in the module docstring, since the next reader will ask.

1. **Name the kit's own skills.** A directory whose name matches one this repository ships. Exact and
   self-contained, and it goes stale the moment the catalog changes unless it is derived at runtime,
   which a hook cannot do without importing from this repository, forbidden by
   [the hooks module contract](../.agents/hooks/README.md).
2. **Read the install manifest.** Authoritative, and it makes a portable hook depend on one
   repository's script layout, which the docstring already rejects for the currency question.
3. **Narrow the claim instead of the check.** Keep counting any skill, and report when none of *this
   repository's* skills is present, using a marker the kit places at install time.

Whatever is chosen, the silence contract in `S-010` still holds: a session with the kit's skills
reachable receives nothing. Do not trade the noise property for the correctness one.

**The spec may need an amendment rather than the code moving to it.** If the honest answer is that a
hook cannot tell whose skills it found, then the contract is wrong and `S-008` needs rewriting, not
the hook. Per the convention recorded in [`docs/spec/README.md`](../docs/spec/README.md), an
amendment to an approved spec keeps `status: approved`, carries a dated note, and is marked pending
the author's re-approval. Do not silently rewrite the scenario to match the code.

## Risks and rollback

Touches the hooks module and an approved contract. The risk is a false positive in the other
direction: a recognition too narrow reports "no skills reachable" to an adopter who installed a
subset, and a reminder that cries wolf is uninstalled within a week, which costs more than the miss
it fixes. Cover the adopter-with-a-partial-install case in a test.

Reversible by reverting one commit; the hook writes nothing and holds no state.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [ ] A test that places a foreign skill library at user scope, with no kit skill anywhere, and
      asserts the hook reports. It must fail against the current hook.
- [ ] A test that places kit skills at user scope beside a foreign library and asserts silence
      (`S-010`).
- [ ] A test that places kit skills at project scope only and asserts silence (`S-009`).
- [ ] The empty-discovery-directory case still counts as unreachable, so `--uninstall` leaving the
      parent behind does not read as success.
- [ ] No environment detection is introduced; the existing `S-016` test still passes unchanged.
- [ ] The hook still writes nothing, exits 0 on malformed input, and imports nothing from this
      repository.
- [ ] Either the code matches the contract's "kit skill" wording, or `cloud-executable.md` is amended
      to match what a hook can honestly answer, dated and marked pending re-approval, with the
      `docs/spec/README.md` re-approval queue extended.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
