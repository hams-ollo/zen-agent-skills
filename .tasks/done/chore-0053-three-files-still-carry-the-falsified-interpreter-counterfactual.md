---
id: chore-0053
title: Three files still carry the interpreter counterfactual chore-0052 removed, and one of them now contradicts itself
type: chore
status: done
priority: P2
parent: "ROADMAP Epic E: delegated execution"
depends_on: [chore-0052]
spec: "docs/spec/cloud-executable.md"
scenarios: []
touched_files:
  - docs/spec/cloud-executable.conformance.md
  - docs/spec/cloud-executable.s001-s016.verification.md
  - tests/test_hooks_reachability.py
created: 2026-08-21
---

## Problem

[`chore-0052`](chore-0052-settings-json-defends-its-interpreter-with-a-falsified-counterfactual.md)
removed a counterfactual from `.claude/settings.json`: the claim that the first draft's `python`
"would have failed to launch in the exact environment the exception was granted for". Observation 3 of
the 2026-08-21 reachability run found `/usr/local/bin/python3` **and** `/usr/local/bin/python` both
present on that platform, so the first draft would have launched.

**The same claim is restated in three other places, all still live.** Verified 2026-08-21:

| File | What it says |
|---|---|
| [`cloud-executable.conformance.md`](../../docs/spec/cloud-executable.conformance.md) | the `Bootstrap registration` Proposed Surface row: "the hook would not have launched in the exact environment the committed-settings exception was granted for. Caught by independent verification before any cloud run." |
| [`cloud-executable.s001-s016.verification.md`](../../docs/spec/cloud-executable.s001-s016.verification.md) | "It would have struck **in the exact environment the committed-settings exception was granted for**" |
| [`test_hooks_reachability.py`](../../tests/test_hooks_reachability.py) | `CommittedRegistrationTests`' docstring: the interpreter "was wrong for the only environment the file exists to serve", and "The failure would have been silent in the worst available way" |

**The conformance matrix now contradicts itself**, which is the sharpest of the three. Its Proposed
Surface row asserts the counterfactual, and its own observation section records the falsification
roughly eighty lines below. A reader who stops at the row gets the opposite of what the document
concludes.

`chore-0052`'s agent found two of these and is the reason this task exists. It attributed the
verification record's wording to the test file, so the citations above were re-derived rather than
copied: the phrase it quoted lives in the verification record, and the test docstring makes the same
claim in different words. The third file was found during that check.

## Scope

**In scope:** make all three say what is now known, without changing any behaviour or any verdict.

- Correct the conformance matrix's Proposed Surface row so it no longer asserts the counterfactual,
  and so it agrees with the observation already in the same file rather than being corrected by it.
- Correct the verification record. **Decide first whether it should be corrected at all**, and record
  the decision either way: a `<spec>.verification.md` is a ledger of a run that happened, and
  `AGENTS.md` treats a ledger as something that is added to rather than rewritten. An annotation
  dated 2026-08-21 may be the right shape instead of an edit, which is the same move the matrix used.
- Correct the `CommittedRegistrationTests` docstring's stated reason. **The test's assertions stay
  exactly as they are**: the interpreter is still `python3` and the tests that pin it are still
  right. Only the explanation of why is falsified.

**Out of scope:**

- `.claude/settings.json`, corrected by `chore-0052` and the reference for what the replacement text
  should say.
- Changing the interpreter. It stays `python3`, for the reasons `chore-0052` recorded: it is the
  portable default and `feat-0038`'s Windows Store-alias failure is real and observed.
- Any test assertion. If correcting a docstring appears to require changing what a test asserts, stop:
  that means the finding is larger than this task and belongs in its own.
- Reclassifying any conformance row. The `Bootstrap registration` row stays **Conformed**; what is
  wrong is one sentence of its evidence prose, not the verdict.

## Implementation notes

Read `chore-0052`'s replacement paragraph in `.claude/settings.json` first. It solves the same problem
and the three corrections should agree with it rather than each inventing wording. Two properties of
that paragraph are worth carrying over: it states the platform and the date, because "both are
present" is true of one container on one day and is not a claim about every environment; and it keeps
the record of how the error happened rather than deleting it, since "found by independent verification
before any cloud run" was true and was the tell.

Note that `chore-0052`'s replacement quotes the old claim in past tense to explain the correction, so
a naive grep for the old phrase still matches `.claude/settings.json`. Do not treat that as an
uncorrected instance, and do not write an acceptance check that would.

## Decisions

**The verification record is annotated, not edited. Rejected: correcting the two counterfactual
sentences in place.** The scope asked for this decision before any edit, and the file answers it
itself: its third paragraph declares "A ledger. **The verdict below is `fail` and stays `fail`**",
and records the same-day fixes at the end "rather than by editing the verdict, because a record
rewritten to match a later state stops being evidence of anything". A counterfactual the 2026-08-07
session actually reasoned its way to is part of what that run found, and rewriting it would leave a
record that looks like the session knew something it could not have known. The file already carries
the annotation shape for exactly this, in "Cross-platform limitation closed, 2026-08-07", a dated
`###` subsection appended under the claim it revises, so the correction follows that precedent
rather than inventing a second one. The in-place edit was rejected on the ledger rule; its one
advantage, that a reader cannot stop at the falsified sentence, is bought instead by putting the
annotation immediately after the bullets rather than at the end of the file.

**No frontmatter key records the annotation. Rejected: adding an `annotated: 2026-08-21` key** in the
shape of the conformance matrix's `re_audited`. The matrix's key marks a re-audit that revisited
every row; this is one appended subsection that moves no verdict, and the file's own 2026-08-07
annotation added no key either. Following the file's precedent beat following a neighbouring file's.

**The conformance matrix row was edited in place rather than annotated, deliberately differing from
the verification record.** A matrix states what is true now and is re-audited, which is why it
carries `re_audited` at all; a verification record states what one run found on one date. The
self-contradiction the task names is only fixed by an edit, since the observation eighty lines below
was already an annotation and a reader stopping at the row never reaches it.

**A seam left open: the two falsified sentences in the verification record still read as written.**
That is the intended outcome of annotating rather than editing, not an incomplete correction. A grep
for "in the exact environment" over `docs/spec/` will keep matching that file, and any future check
written over that phrase has to exempt it for the same reason `chore-0052`'s past-tense quotation in
`.claude/settings.json` is exempt.

## Risks and rollback

Three documents across two directories, one of which is a test file, so this section is required.

The real risk is correcting a ledger. A verification record is evidence that a run happened and
reported what it reported; rewriting its reasoning after the fact makes it a worse record even when
the new reasoning is better. That is why the scope asks for a decision before an edit rather than
assuming one.

Reversible by reverting one commit. No behaviour changes and no verdict moves.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] The conformance matrix's `Bootstrap registration` row no longer asserts what `python` would have
      done, and no longer contradicts the observation in the same file.
- [x] The verification record is either corrected or deliberately annotated, with the choice and its
      reason recorded in `## Decisions`.
- [x] `CommittedRegistrationTests`' docstring states a reason that survives the 2026-08-21
      measurement, and **every assertion in that class is unchanged**, proven by diffing the class
      body against the previous revision.
- [x] The interpreter in `.claude/settings.json` is still `python3` and that file is unmodified.
- [x] No conformance row's verdict changes.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
