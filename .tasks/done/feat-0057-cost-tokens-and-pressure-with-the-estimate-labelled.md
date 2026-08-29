---
id: feat-0057
title: Report tokens by kind and an estimated cost that never invents a figure it cannot derive
type: feat
status: done
priority: P2
parent: "ROADMAP Epic E #7b: reporting"
depends_on: [feat-0054]
spec: docs/spec/agent-observatory.md
scenarios: [S-010, S-011, S-017, S-021]
touched_files:
  - scripts/
  - tests/
  - docs/spec/agent-observatory.md
created: 2026-08-28
---

## Problem

The corpus records what every message consumed and carries no cost field at all, so any monetary
figure is derived. A derived figure presented as a measured one is the failure this task exists to
avoid, and it is easy to reach: a cost column that looks authoritative is more useful-seeming and
less true than one that says what it is.

The contract handles this by requiring the estimate to be labelled and dated (`S-010`) and by
forbidding an invented figure where the model is unpriced (`S-011`).

Read [`docs/spec/agent-observatory.md`](../../docs/spec/agent-observatory.md) for the contract. It is not
restated here.

## Scope

**In scope:** the cost and pressure report.

- Token consumption split by kind, with the cache-served proportion derivable (`S-021`).
- Estimated cost against a local rate table, labelled and carrying the table's date (`S-010`).
- Unpriced models reported as unknown rather than as zero (`S-011`).
- Context and quota pressure as series over time, with compaction occasions identifiable (`S-017`).

Files this task creates, with their exact paths:

- `scripts/observatory/pricing.json`, rates with an `as_of` date

**Out of scope:**

- **Fetching rates.** Open Question 1 in the contract recommends against it and the no-network
  property `S-022` establishes forbids it. The table is local data, updated by hand.
- **Any bound, budget, or alert.** ROADMAP Epic E item 7(c) holds those behind item 5. Reporting how
  close a limit is is inside this task; deciding what to do about it is not.
- **Per-skill or per-agent cost attribution.** `feat-0054` and `feat-0056` own those surfaces; this
  task supplies the figures they may use.
- **Backfilling historical rates.** One rate per model, current as of the table's date. See the notes.

## Implementation notes

**Every cost figure in this repository's history is unverified against a bill.** State the estimate as
an estimate everywhere it appears, not once in a footnote, and give it the table's date so a reader can
judge its age. A single labelled figure is worth more than a precise-looking unlabelled one.

**One rate per model, applied to the whole corpus, is wrong for old sessions and is the right
simplification anyway.** Rates change, the corpus spans months, and per-date rate history is a
maintenance burden with no source that can be fetched. Take the simplification, and say in the report
that historical sessions are priced at current rates rather than leaving the reader to assume
otherwise.

**`S-011` is the scenario most likely to be quietly broken.** A missing rate that yields zero looks
exactly like a free model, and it will happen every time a new model ships. Unknown must be a distinct
reported state, and it must be visible in any total the figure contributes to, so a total covering
unpriced sessions cannot read as complete.

**The quota series and the context-budget records come from different sources with different shapes.**
Confirm what each actually contains before depending on a field, and treat the quota source as
optional per the contract's Sources table: its absence degrades `S-017` to its context half rather
than failing the report.

## Decisions

- **Rejected: pricing input and output only, and leaving the cache kinds unpriced.** The rate
  source names base input and output rates directly and gives the cache kinds as multipliers
  against input, so pricing only the two named ones was the smaller claim. Rejected because
  96.7% of this corpus's input-side tokens are cache reads: the same work costs an estimated
  $1,105.12 priced on input and output alone against $9,378.53 priced on all four, a figure
  eight and a half times too small. A report that
  silently omits its largest kind is `S-011`'s failure applied to a kind instead of a model.
- **Rejected: a formal provenance block on `pricing.json`.** The convention in `AGENTS.md`
  requires a re-fetchable raw URL and a sha256 of the retrieved bytes, and `check-provenance.py`
  scans only `.md` and `.py`. The rates come from a skill bundled with the harness at a local,
  version-stamped path with no URL that checker could fetch, so a block would either dangle or
  carry a digest nobody could reproduce. The same facts are recorded as ordinary JSON fields,
  and the file says why.
- **Seam left open deliberately: the quota sample series has no producer.** The reader, and the
  JSON Lines shape it accepts, are this component's own; nothing on this machine writes such a
  file. The absent path is therefore the one a real run takes, and it is the one exercised
  against the real corpus. Both facts are stated on the page rather than left to be discovered.
- **Premise that turned out false: that a quota source exists to be brought in.** This task's
  notes and `S-017`'s conformance row both say the quota half "comes from a file outside the
  corpus", which reads as though the file is there and unread. It is not: searched on
  2026-08-29 across the harness's whole data directory and across the corpus, no file and no
  record carries a quota sample series. So `S-017`'s quota half is built and unexercised by real
  data rather than merely unwired.
- **`thinking_tokens` is a breakdown of output, not a fifth billable kind.** It arrives from
  `output_tokens_details`, so it is reported as a memo beside the four and is absent from every
  cost figure. Pricing it would charge for the same tokens twice, and the store's fifth column
  invites exactly that.

## Risks and rollback

The task touches more than one module, the rate table it introduces, the quota source it reads, and
the page it renders into, so the deterministic rule fires on the first condition.

**Every risk here is a wrong number presented confidently.** A stale rate table misstates every cost
figure while the report looks exactly as correct as it did the day the rates were right, which is why
`S-010` puts the date beside the figure rather than in a footnote: the mitigation has to be visible
where the number is read.

The sharper failure is `S-011`. A missing rate that yields zero is indistinguishable from a free model,
it happens every time a new model ships, and it silently understates any total it contributes to.
Unknown must be its own state and must propagate into totals, or this report starts lying the first
time the model lineup changes and gives no signal that it has.

Rollback is reverting one commit. The rate table is data rather than state, the store is untouched, and
no figure is persisted, so a bad rate is corrected by editing one file and re-rendering.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] New tests cover S-010, S-011, S-017, and S-021, each named so the scenario it proves is
      identifiable.
- [x] Input, output, cache-read, and cache-creation tokens are each reported separately, and the
      cache-served proportion is derivable from them (S-021).
- [x] Every cost figure is labelled an estimate and accompanied by the rate table's `as_of` date
      (S-010).
- [x] A model absent from the rate table reports tokens, reports cost as unknown rather than zero, and
      is named as unpriced; a total including it says so (S-011).
- [x] Context and quota pressure are reported as series, and compacted sessions are identifiable
      (S-017).
- [x] The report renders correctly with the quota source absent.
- [x] The report states that historical sessions are priced at current rates.
- [x] No network call is made to obtain rates, asserted by a test.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] The `agent-observatory` conformance matrix is updated for S-010, S-011, S-017, and S-021.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
