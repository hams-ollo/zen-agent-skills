---
id: bug-0056
title: revised conflates an edited lens with an untouched stale one, so a new rule never gets reported
type: bug
status: open
priority: P1
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
spec: "docs/spec/install.md"
touched_files:
  - scripts/install.py
  - .agents/hooks/install-currency-reminder.py
  - tests/test_install.py
  - tests/test_hooks_currency.py
created: 2026-08-29
---

## Problem

`_check_entry()` in [`install.py`](../scripts/install.py) takes the adopted branch at line 1135 and
returns at 1182:

```python
        return "revised", ("the kit's copy has changed since this install; yours is yours "
```

That branch compares the **recorded baseline** against the **source**. It never opens the installed
file, so it cannot tell whether the adopter made the module theirs. Two different states get the same
verdict and the same sentence:

- The adopter edited their lens and the kit also moved. `revised` is right, and silence is right.
- The adopter never touched it and the kit moved. Also `revised`, and the message tells them "yours
  is yours to keep" about a file they never made theirs.

`REPORTING_VERDICTS` in
[`install-currency-reminder.py`](../.agents/hooks/install-currency-reminder.py) is `("diverged",
"unknown", "error")`. `revised` is excluded on the stated ground that "firing on it every session
would be crying wolf about a file the adopter was invited to own." That reasoning is correct for the
first state and wrong for the second, and the hook cannot separate them because `--check` did not.

**The consequence, measured on the author's machine on 2026-08-29.** `A10`, the kit's only rule about
untrusted input, landed in [`autonomy.md`](../.agents/rules/autonomy.md) on 2026-08-27 in `f2adc5e`.
Both installed homes:

```text
source autonomy.md digest   : 4eb075628d33 (17247 bytes)

  tool=claude  target=C:\Users\hamsa\.claude\rules
    recorded baseline : 6d10f09b71f2
    installed on disk : 6d10f09b71f2  (12553 bytes)
    -> installed MATCHES the baseline: untouched by the adopter
    contains A10      : False

  tool=opencode  target=C:\Users\hamsa\.agents\rules
    recorded baseline : 6d10f09b71f2
    installed on disk : 6d10f09b71f2  (12553 bytes)
    contains A10      : False
```

Untouched in both homes, two days stale in both, missing the rule entirely, reported `revised` at
exit 0, and silent from the one hook built to report staleness. The session that found this was
itself running with the stale copy in context.

This is the third appearance of the failure `.agents/hooks/README.md` names: "installed,
correct-looking, and doing nothing." The first two were a hook registered under the wrong event and a
hook whose reachability check looked at the wrong directory. This one is a verdict that is right
about the wrong question.

**The information needed to separate the two states is already present.** `installed == recorded`
means untouched, and `_place_adopted()` already draws exactly that line for placement:

> A file differing from the recorded digest is the adopter's and is left alone; a file matching it
> differs only because the kit moved on, so it is ours to refresh.

`_check_entry()` should draw the line its sibling already draws.

## Scope

**In scope:** splitting the adopted verdict so an untouched-but-stale module is distinguishable from
an edited one, and letting the currency hook report the first without reporting the second.

**Out of scope:**

- Changing what `_place_adopted()` does. Placement is correct: an untouched file is refreshed on the
  next install, which is why this is a reporting defect and not data loss. Verified by digesting both
  homes against the baseline.
- Auto-refreshing anything, or having the hook run the installer. The autonomy module's governing
  principle applies to its own distribution: detect and report, never rewrite. Re-installing is the
  person's call.
- Widening currency detection to adopters who do not have the source repository. That boundary is
  stated in the hook's docstring and is ROADMAP Epic B item 19's question.
- Any change to `ADOPTED_ENTRY_NAMES` or to which module is adopted.

## Implementation notes

In the adopted branch of `_check_entry()`, digest the installed tree as well as comparing recorded
against source, then split on whether the installed files still match their baseline:

- installed matches baseline, source has moved: the copy is untouched and out of date. Report it as
  `diverged`, which the currency hook already reports, with a message saying the kit's copy moved and
  a re-install will take it because nothing here is theirs yet.
- installed differs from baseline: keep `revised` and keep the current message, which is correct for
  exactly this case.
- mixed, some files edited and some not: `revised` is the safer word, because something in the module
  is theirs. Say how many files are in each state rather than collapsing it.

Prefer reusing existing words over adding one. `diverged` already means "the installed copy no longer
matches this kit" and that is true here; a seventh verdict would need `VERDICTS` widened in the hook,
which `tests/test_hooks_currency.py` pins against `check()` in both directions, and it would cost a
new concept for a distinction the existing vocabulary expresses.

The digest of the installed tree is the added cost, and it is bounded: this is the adopted module
only, three files today. It is not the per-file read of every skill that the hook's docstring
correctly refuses to do at session start.

## Decisions

- **A premise that turned out false.** This was first held as "the adopted exemption means a rules
  lens can never be refreshed, so a security rule never reaches anyone who has already installed."
  That is wrong, and measuring it is what corrected it: `installed == recorded` in both homes, so
  `_place_adopted()` would refresh on the next run. The defect is that nothing tells anyone to make
  that run.

## Risks and rollback

Touches the installer's check path and a hook that fires at every session start, so it meets the
more-than-one-module rule. The failure direction is a hook that now fires on every session for
adopters who deliberately edited their lens, which is the crying-wolf outcome the exclusion was
written to prevent; that is why the edited case must keep `revised` and keep its silence.

Reversible by reverting one commit. No persisted format changes: the manifest already carries the
digests this needs.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [ ] A test builds an adopted entry whose installed files match the recorded baseline while the
      source has moved, and asserts the verdict is reportable rather than `revised`.
- [ ] A test builds an adopted entry whose installed files differ from the baseline and asserts it is
      still `revised`, still exit 0, and still silent from the hook.
- [ ] A test drives the currency hook over the first case and asserts it emits, and over the second
      and asserts it stays silent.
- [ ] The `VERDICTS` and `check()` vocabularies still agree in both directions, which
      `tests/test_hooks_currency.py` already asserts.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] The `install` conformance matrix is brought up to date, or the deferral is recorded.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
