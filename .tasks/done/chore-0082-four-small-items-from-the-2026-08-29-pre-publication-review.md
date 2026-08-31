---
id: chore-0082
title: Four small items from the 2026-08-29 pre-publication review, bundled because none is worth its own round trip
type: chore
status: done
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - .agents/hooks/install-currency-reminder.py
  - scripts/install.py
  - scripts/observatory/serve.py
  - tests/test_hooks_currency.py
  - tests/test_install.py
  - tests/test_observatory_serve.py
created: 2026-08-29
---

## Problem

Four items from the
[2026-08-29 pre-publication review](../../docs/reviews/2026-08-29-pre-publication-review.md), each small
enough that four task files would cost more than the work. The bundling follows the precedent
[`chore-0038`](chore-0038-five-small-upkeep-items-from-the-2026-08-08-review.md) set and its caveat
applies here too: this is the exception rather than the pattern, and the reason is written down so a
later reader does not take it as licence.

**1. A session-start hook digests an unbounded tree named by a file it does not control.**
`classify()` in [`install-currency-reminder.py`](../../.agents/hooks/install-currency-reminder.py) line
267 calls `digest_tree(source)`, where `source` is `Path(entry.get("source") or "")` read from the
manifest. `digest_tree` walks `root.rglob("*")` and calls `read_bytes()` on every file, with no bound
on count or size. The hook runs at every session start, and `find_manifest()` walks upward from the
session's working directory, so a manifest at any ancestor is used.

The module's docstring makes cost the property to get right, under the heading "Cost, which is the
thing to get right", and bounds only the no-manifest path: "the manifest is read first and its
absence ends the run." Past that gate there is no bound at all. A manifest entry naming a large
directory turns every session start into a full recursive read of it.

**2. The manifest accumulates entries for homes that no longer exist.** Reversal is scoped to
`--home` by design (`S-007`, `S-012`), so `uninstall()` rewrites only the entries it did not remove.
An entry for a home that was deleted rather than uninstalled is never in `mine`, never pruned, and
counted `diverged` forever.

Observed 2026-08-29, in three steps, because the middle one is what makes this worth more than a
tidy-up. `python scripts/install.py --check` reported `10 current, 52 diverged`. Refreshing the
install took the real entries to current and left `44 current, 20 diverged`, and all twenty of those
were one dead home: a scratchpad `fakehome` under a different session id, left by a run that
installed there and never uninstalled, with `0 of 20` targets still on disk.

**Then `install-currency-reminder.py` was registered in `~/.claude/settings.json`, and it fired on
every session start**, reporting those twenty as "installed copy/copies have gone stale, because the
kit's own copy has changed since they were installed" and naming `doc-author`, `doc-revise`,
`doc-sync`, `fix-batch`, `hooks`, `house-review` among them. None of that was true: the real install
was 44 of 44 current. The litter did not merely inflate a count a person reads, it made a guardrail
assert something false at every startup, which is the crying-wolf failure the hook's own docstring
says gets it uninstalled within a week.

The twenty entries were pruned by hand on 2026-08-29 (target gone and home gone, via
`install.save_manifest` so the format matched the tool's own writer), after which `--check` reports
`44 current, 0 diverged` and the hook is silent. **That was a one-off repair, not a fix**: the tool
still has no mechanism, so the next throwaway `--home` that is deleted rather than uninstalled
recreates the condition, and the next person to hit it has no `--prune` to reach for.

**3. The bind guard matches `localhost` case-sensitively while the Host guard lowercases.** In
[`serve.py`](../../scripts/observatory/serve.py), `loopback_address()` line 428 reads
`if host.rstrip(".") == "localhost":` while `host_is_loopback()` line 472 reads
`if host.rstrip(".").lower() == "localhost":`. So `--host LOCALHOST` is refused with `NotLoopback`
rather than bound. It fails closed, which is the right direction; two functions reading the same name
two ways is the thing worth fixing.

**4. The report sets no Content-Security-Policy header.** `_send()` at lines 2028 to 2036 sets
`Content-Type`, `Content-Length` and `Cache-Control` and nothing else. The page uses no `innerHTML`
at all, so this is defence in depth rather than a live hole. It is worth adding because it would have
contained [`bug-0055`](bug-0055-a-corpus-value-becomes-an-href-with-no-scheme-check.md) rather than
letting it reach the network, and a header that turns a click-to-execute into a blocked request is
cheap insurance for a surface serving one maintainer's whole session history.

## Scope

**In scope:** the four corrections above.

**Out of scope:**

- Widening the currency hook to adopters without the source repository. That boundary is stated in
  its docstring and is ROADMAP Epic B item 19's question.
- Anything that makes the currency hook run the installer. Detect and report, never rewrite.
- The `uninstall()` `KeyError`, filed as
  [`bug-0053`](bug-0053-uninstall-deletes-then-raises-on-an-optional-manifest-key.md). Item 2 is
  about entries the tool correctly declines to touch, not about entries it mishandles.
- The `href` scheme check, filed as `bug-0055`. Item 4 is the second layer, not the fix.
- Any change to `host_is_loopback()`'s behaviour, which was live-probed against seven header shapes
  and is correct. Item 3 changes the other function.

## Implementation notes

**Item 1:** bound the walk by file count and by total bytes, returning `error` past either. That
verdict already exists in `VERDICTS`, is already in `REPORTING_VERDICTS`, and its message already
covers the shape ("could not be compared at all"). Widen the message rather than adding a seventh
word. Pick the caps generously: the largest real module is the hooks directory, so a cap in the low
thousands of files and tens of megabytes stops a pathological entry without ever firing on a correct
one. The same unbounded walk exists in `install.py`'s `digest_tree()`, and it is deliberately not in
scope: that one runs when a person invoked the installer, not at every session start, and the cost
argument is the hook's.

**Item 2:** prefer a `--prune` over silent pruning, because deleting a record of an install is the
kind of thing the autonomy module says a person decides. If that is too much for one item, the
cheaper half is a line in `--check`'s summary separating "target gone, and so is its home" from
"diverged in place", so the count stops conflating litter with staleness.

**Item 3:** lowercase in `loopback_address()` to match. Do not factor the two functions together:
they answer different questions (what may this bind, versus what may this answer) and the comment on
each explains its own reasoning at length.

**Item 4:** `default-src 'self'` plus whatever the page actually needs. The page has inline
`<style>` and inline `<script>`, so `'unsafe-inline'` is required for both until they are extracted,
and extracting them is out of scope. Say so in the header's comment rather than leaving a reader to
wonder why `'unsafe-inline'` is there. Even with it, `javascript:` URIs are blocked by
`script-src`, which is the containment this item is for.

## Decisions

- **A premise of item 1's own fix that turned out false, caught by its test.** The caps were first
  written as default arguments (`max_files: int = MAX_DIGEST_FILES`). A default is evaluated once
  when the function is defined, so a test raising or lowering the module constant changed the name
  and not the bound, and `classify()` went on digesting the whole tree. They are read at call time
  now. The test would have passed against an untunable cap had it asserted the constant instead of
  the behaviour.
- **A rejected alternative for item 2.** A `--prune` that removes orphaned entries, which this task
  named as the preferred shape. Deleting a record of an install is the kind of thing the autonomy
  module says a person decides, and the cheaper half satisfies the acceptance criterion: `--check`
  now says which entries record a home that is gone, why nothing will ever prune them, and what to
  do instead. The `--prune` remains unbuilt and is not filed, because the twenty real entries were
  removed by hand and no others exist; a flag with no user is speculative work.
- **The home is derived rather than recorded, and the fallback leans one way on purpose.** A
  manifest has never carried the home, and a new key would be unreadable for every entry written
  before it, so `_home_of()` walks up to the `.claude` or `.agents` component. A target with neither
  marker falls back to its own parent, which cannot match a home this tool placed into and so reads
  as "still there". That is the safe direction: this decides only whether `--check` calls an entry
  litter, and calling real litter live costs a line of output where the reverse invites deleting a
  live record.
- **Item 4's acceptance criterion earned its keep, and found two defects that were not this task's.**
  "The report page loads with no console errors" cannot be satisfied by reasoning, so the page was
  loaded in a browser against the real store. It rendered under the policy with no console errors,
  and it showed **"no date recorded"** in the rate table for both `claude-sonnet-5` rows, which
  plainly carry dates. [`bug-0057`](bug-0057-a-flat-rate-table-understates-cost-after-an-expiry-it-records.md)
  had replaced the `expires` field with per-period bounds and left the renderer reading the old key,
  and it had left `HISTORICAL_RATES_NOTE` still claiming the table holds one rate per model. Both
  are fixed here and both are disclosed as work beyond this task's four items, because no test
  caught either: the page-side assertion pinned `entry.expires`, so it moved with the defect.
- **Work beyond `touched_files`, disclosed.** `scripts/observatory/ui/index.html` and the two
  `bug-0057` regressions above; `docs/spec/agent-observatory.conformance.md`, whose `S-010` row cited
  a test this pass renamed and was re-derived rather than repointed, per the citation gate's own
  advice when it caught it.

## Risks and rollback

Touches a hook that fires at every session start, the installer, and the server, so it meets the
more-than-one-module rule.

The one item that can fail invisibly is item 1: a cap set too low makes the hook report `error` on a
correct install, and an `error` verdict is in `REPORTING_VERDICTS`, so it would fire on every session
start and be uninstalled within a week. Verify by running the hook against this repository's real
manifest and confirming it stays silent.

Item 4 can break the page loudly if the policy is too tight; load the report in a browser and check
the console rather than reading the header.

Each item is reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [x] A test drives `classify()` against a manifest entry whose source exceeds the file-count cap and
      asserts the verdict is `error` rather than a completed digest.
- [x] A test asserts the hook stays silent against this repository's own real install shape, so the
      cap cannot have been set below a correct install.
- [x] Entries whose target and home are both gone are distinguishable in `--check`'s output from
      entries that diverged in place, covered by a test.
- [x] `--host LOCALHOST` binds rather than raising `NotLoopback`, covered by a test.
- [x] Every response carries a `Content-Security-Policy` header, covered by a test, and the report
      page loads with no console errors.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
