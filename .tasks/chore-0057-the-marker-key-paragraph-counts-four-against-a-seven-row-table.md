---
id: chore-0057
title: The marker-key paragraph counts four specs against a table that now lists seven, and carries a second positional claim nobody has checked
type: chore
status: open
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: [chore-0056]
touched_files:
  - docs/spec/README.md
created: 2026-08-22
---

## Problem

The paragraph in [`docs/spec/README.md`](../docs/spec/README.md) explaining why the re-approval
convention has no marker key states:

```text
Four do, listed below, and each states its pending state in different words and two of
them at the foot of the document rather than the header. Retrofitting them means editing
four approved contracts, which is the author's pass and not an agent's.
```

The table below it now lists **seven** rows. Both counts are stale.

`git log -S "editing four approved contracts" -- docs/spec/README.md` puts the last change to that
text at `81b2591` (`chore-0030`, 2026-08-06), so it was **not** among the counts `chore-0054`
recomputed on 2026-08-21. A dispatch note asserted it had been, and that assertion was wrong; the
agent working [`chore-0056`](done/chore-0056-the-re-approval-queue-note-refers-to-its-table-by-position.md)
obeyed the bound, left the paragraph alone, and reported the bound as false, which is why this exists.

**It is the same defect `chore-0056` fixed two paragraphs below**, and the fifth instance of the class
overall. The convention against it is now written into
[`house-style.md`](../.agents/rules/house-style.md): never count the rows of a table in prose beside
it, name the row instead. This task is the last known instance predating that rule.

**A second claim in the same sentence has never been checked.** "Two of them at the foot of the
document rather than the header" is a positional assertion about where each spec keeps its pending
note, and no one has verified it against the seven specs. It may have been true of four and be false
of seven, or it may still hold.

## Scope

**In scope:** make both counts correct, or remove them, and settle the unverified positional claim.

- Apply the `house-style.md` rule rather than working around it: prefer removing the counts to
  correcting them, since a corrected count drifts again on the next amendment, which happens roughly
  weekly here.
- **Verify "two of them at the foot of the document" against all seven specs** and state the result.
  If it is wrong, fix it. If it is right, say so in the closeout so the next reader does not re-derive
  it. If it cannot be settled cleanly, that is a finding.
- Keep the paragraph's argument. It is the only place recording why a marker key is not introduced
  yet, and the reasoning (such a key earns its keep only once every spec already in this state
  carries it) is the substance.

**Out of scope:**

- **Introducing the marker key.** The paragraph argues toward it and `README.md` elsewhere records
  that five things read a spec's `status`, so it is a real design question and not a prose fix.
- The re-approval queue table itself, its rows, and any `status` field.
- The paragraph `chore-0056` already rewrote, which is correct as it stands.
- The scenario and total counts recomputed by `chore-0054` on 2026-08-21, which were verified against
  the files and are correct. **Unlike the previous bound on this file, that statement has been
  checked**: the sums were re-derived independently at reconciliation.
- Auditing the rest of the repository for the same class. `house-style.md` now carries the rule, which
  is the durable half; a sweep is separate work and should be argued for on its own.

## Implementation notes

Read `chore-0056`'s rewrite of the neighbouring paragraph first and match its approach rather than
inventing a second style in the same document. It replaced "the fifth row" with "the `house-review`
row" and "the other four" with "the rest of this table", so the fix here is the same move applied to a
harder sentence, since this one counts a subset rather than a complement.

The subset is what makes it harder. "Four do" is a claim about *which* specs already carry a pending
note in prose, and by now that may be all seven, in which case the sentence's premise has changed and
not merely its arithmetic. Establish which specs it is actually about before rewording, because a
sentence that says "all of them" when it means "the ones that do" would be a new error wearing the
fix's clothes.

## Risks and rollback

One file, prose only, so this section is short.

The failure to avoid is fixing the numbers and losing the argument, which is the same risk
`chore-0056` carried. This paragraph is the only record of why the marker key is deliberate rather
than forgotten.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] The paragraph states no count of rows of the table below it, per the `house-style.md` rule.
- [ ] The claim about where specs keep their pending note is verified against all seven, and the
      closeout states what the check found.
- [ ] The argument for why a marker key is not introduced yet survives.
- [ ] No table row, `status` field, or spec is modified.
- [ ] The paragraph `chore-0056` rewrote is unchanged, proven by diff.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
