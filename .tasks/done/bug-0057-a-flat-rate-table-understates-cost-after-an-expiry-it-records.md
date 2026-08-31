---
id: bug-0057
title: A flat rate table silently understates cost after an expiry it records but never applies
type: bug
status: done
priority: P1
parent: "ROADMAP Epic E #7b: reporting"
depends_on: []
spec: "docs/spec/agent-observatory.md"
scenarios: [S-010, S-011]
touched_files:
  - scripts/observatory/pricing.json
  - scripts/observatory/serve.py
  - tests/test_observatory_cost.py
created: 2026-08-29
---

## Problem

[`pricing.json`](../../scripts/observatory/pricing.json) lines 45 to 49:

```json
  "claude-sonnet-5": {
   "input": 2.0,
   "output": 10.0,
   "note": "Introductory rate, which the source table gives as running through 2026-08-31. The standard rate behind it is $3.00 input and $15.00 output. ...",
   "expires": "2026-08-31",
```

That entry's own note says why the intro figure is the one applied: "because every session in this
corpus ran inside that window, so it is the rate those sessions were actually billed at". That is
true on 2026-08-29 and stops being true on 2026-09-01, session by session, with no signal but a
rendered note beside a figure that still looks exactly as right as it did the day it was true.

The understatement is 33 per cent on input and 50 per cent on output, on the model most of this
corpus runs.

`S-010` asks that a cost figure be "reported as an estimate against a dated rate table". The table is
dated and the sessions are dated, and nothing lines the two up.

**This is not a request to introduce a clock.** The file's `rate_notes_note` rules that out and is
right to:

> `expires` is a date this file states, not a date anything compares against a clock, because the
> report derives everything it says from the corpus and introducing `today` would make its output
> depend on when it ran.

That property must survive this change. It does, because **a session's own timestamp is corpus data,
not a clock**: `first_ts` and `last_ts` are already ingested and already in the store. Pricing each
session against the rate in force on its own date introduces no dependency on when the report runs.
Two runs a month apart over the same corpus still produce byte-identical output, which is exactly
what `rate_notes_note` is protecting.

## Scope

**In scope:** a per-model rate history keyed by date, selected against the session's own timestamp,
and the report saying which rate it applied when a model has more than one.

**Out of scope:**

- Fetching rates. `S-022` forbids it and the file's opening states it: "Local data with a recorded
  date, never fetched."
- Any comparison against the current date, anywhere.
- Changing how `S-011` treats an unpriced model. A session whose date falls outside every recorded
  range is unpriced, which is the existing path and needs no new one.
- Cache multipliers and the thinking-token memo, which are separate and correct.

## Implementation notes

The immediate mitigation and the fix are different sizes and should not be confused. **The
mitigation** is editing the two numbers to 3.0 and 15.0 on or after 2026-09-01 and moving 2.0 and
10.0 into whatever history shape lands. That is a one-line correction and it will be wrong again the
next time a rate changes. **The fix** is the history.

The shape that fits the file's existing conventions:

```json
  "claude-sonnet-5": {
   "rates": [
    {"from": null, "until": "2026-08-31", "input": 2.0, "output": 10.0,
     "note": "Introductory rate."},
    {"from": "2026-09-01", "until": null, "input": 3.0, "output": 15.0}
   ]
  }
```

Keep `input` and `output` at the top level as the fallback for a model with a single rate, so the
twelve entries that have never changed do not all grow an array. `models_note` already states that a
key is present or the model is unpriced, with no prefix matching; the same exactness applies to a
date falling in no range.

Selection happens where cost is derived in [`serve.py`](../../scripts/observatory/serve.py), against the
session's `first_ts`. Use the session's start rather than its end, because that is when the run was
priced, and say so in a comment: a session spanning a rate change is a real case and picking one end
silently is how the next reader loses a day.

`rate_notes_note` will need a sentence saying that `expires` is now the boundary of a range rather
than a note, or the field should be dropped in favour of the range bounds. Prefer dropping it: two
representations of the same fact is the drift shape this file's own notes are careful about
everywhere else.

## Decisions

- **A rejected alternative.** Comparing `expires` against the current date and switching rates was
  rejected, because it breaks the property `rate_notes_note` protects: two runs over the same corpus
  would then disagree, and a report that changes when nothing it reports on changed is not a report
  of a corpus.
- **A premise that turned out false, and it moved the join.** The notes above say to select against
  the session's `first_ts`. `cost_report()` does not group by session at all: it groups by model over
  the whole `message` table, so there was no session to select against. Selection is per message
  instead, against `message.ts`, which is strictly more accurate and needed no new join. The query
  now groups by `(model, day)`. Cheap at this corpus's shape and measured rather than assumed: 90
  `(model, day)` rows over 59,447 messages, with every timestamp present and parseable.
- **A rejected alternative on partial coverage.** Pricing the days a model's periods cover and
  reporting the rest as a caveat. Rejected for the reason `load_pricing()` already gives one level
  up: "A half-resolved model would be worse than an unpriced one, because its cost would look like a
  figure while quietly omitting whichever kind had no rate." A day no period covers is that same
  shape across time, so a model with any such day is unpriced, its tokens are still reported per
  `S-011`, and the uncovered dates are named.
- **A guard that matched prose, caught by its own mutation test.** The assertion that rate selection
  reads no clock scanned the source of `rate_in_force` for the word `today`, and failed, because
  that function's docstring explains that `when` is "a date the corpus recorded, never today". That
  is the fifth recorded instance in this repository of an assertion matching a bare word in source
  text rather than a statement. It strips the docstring and comments before looking now, and
  `_code_only` is itself checked against a sample carrying a real clock so stripping the prose has
  not stripped the teeth. Mutation-tested end to end: inserting `time.time()` into `rate_in_force`
  makes the test fail.
- **A seam left open deliberately.** The clock claim is asserted over the source of the two
  selection functions rather than by patching a clock in. A patch proves only the paths it happens
  to reach; a source assertion over both functions proves there are none to reach. The determinism
  check beside it is necessary and proves less: two runs a second apart would agree even if the code
  did read the calendar, and the test says so rather than letting the pair imply more than they show.
- **Measured before and after on the real corpus, and the answer is that nothing moved.** The
  estimate is byte-identical at $10,226.495341, because every message in the corpus predates the
  2026-08-31 boundary. That is the correct outcome and the point of the fix: it is forward-looking,
  it changes no figure anyone has already read, and it starts mattering on 2026-09-01.

## Risks and rollback

Changes a persisted data format, the rate table, so it meets the more-than-one-module rule even
though only one module reads it. An old `pricing.json` must still be readable, since the file is
edited by hand and a half-migrated one is the likely intermediate state: keep the flat `input` and
`output` form working, and let `rates` be the optional override.

Reversible by reverting one commit. The store is untouched; only the derivation changes.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [x] A test prices two sessions of the same model, one dated inside the introductory window and one
      after it, and asserts they receive different rates.
- [x] A test proves the report's output is unchanged when the same corpus is priced twice with
      different system clocks, so no dependency on `today` was introduced.
- [x] A test proves a session whose date falls in no recorded range is reported unpriced under
      `S-011` rather than priced at a guess.
- [x] A test proves a model entry carrying only flat `input` and `output` still prices, so an
      unmigrated table is readable.
- [x] `claude-sonnet-5` carries both rates with their boundary, and the report names which one it
      applied.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] The `agent-observatory` conformance matrix is brought up to date for `S-010` and `S-011`, or the deferral is recorded.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
