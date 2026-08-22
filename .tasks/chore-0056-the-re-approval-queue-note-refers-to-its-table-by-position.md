---
id: chore-0056
title: The re-approval queue's note refers to its own table by row position, and both numbers drifted when rows were inserted
type: chore
status: open
priority: P2
parent: "ROADMAP Epic B: contract-driven delivery (the agent-workflow spine)"
depends_on: []
touched_files:
  - docs/spec/README.md
created: 2026-08-21
---

## Problem

The paragraph under the re-approval queue in [`docs/spec/README.md`](../docs/spec/README.md) refers to
its own table by **position**, twice, and both references have drifted:

```text
"The fifth row was missed when this table was first written ...
 `house-review`'s note says ... so it is invisible to the search that finds the other four."
```

`house-review` is **row 4** of the current seven-row alphabetical table, not row 5. Row 5 is
`install`. And there are now **six** other rows, not four. The table was five rows when the sentence
was written; `cloud-executable` was inserted at row 2 by `chore-0051` on 2026-08-20 and
`validate-skills` had already joined, so every row below the insertion point shifted and the count
grew.

**The paragraph's own argument is the reason this matters.** It closes: "A convention carried in prose
can only be found by a reader who already knows every phrasing it has ever taken." That is correct,
and the paragraph has now become an instance of it. Its point, that `house-review`'s note is invisible
to a search because of how it is worded, is still exactly right; only the coordinates pointing at it
are wrong.

Found by `chore-0054`'s agent while extending the same table. It correctly left the sentence alone,
being outside its scope, and disclosed it.

**This is the third distinct instance of a prose count drifting from the thing it describes**, which
is the argument for fixing it by removing the coordinates rather than by correcting them:
`ROADMAP.md` claimed eight autonomy rules and three held candidates against nine and four; `chore-0036`
inherited a claim of ten templates out of nine; and this. Every one was invisible to every gate.

## Scope

**In scope:** make the note refer to its subject by name rather than by position, so it cannot drift
again when a row is inserted.

- Name `house-review` as the row it is about, which the sentence already does in its second clause, and
  drop "the fifth".
- Replace "the other four" with a form that does not carry a count.
- Leave the argument intact. The insight, that a prose convention is findable only by someone who knows
  its phrasings, is the reason the paragraph exists.

**Out of scope:**

- **The marker-key proposal the paragraph argues toward.** It says this table should eventually be
  replaced by a marker key, and `README.md` elsewhere records why there is no third `status` value
  and no marker key yet. That is a real design question with five consumers reading `status`, and it
  is not settled by a prose fix.
- Any row of the table, any `status` field, and any spec.
- The other counts in `README.md`, which `chore-0054` recomputed from the files on 2026-08-21 and
  which are correct.
- Auditing the rest of the repository for positional references. Worth doing and not here; if this fix
  suggests a general rule, say so in the closeout rather than acting on it.

## Implementation notes

Check whether `house-review`'s note still reads as the paragraph describes before rewriting around it.
The sentence asserts that note says "left at `approved` for the author to confirm at closeout" rather
than using the words *pending* or *re-approval*, which is what makes it invisible to a search. If that
wording has since changed, the paragraph's premise is gone and the fix is a different one: say so
rather than preserving an argument about a state that no longer holds.

Prefer removing the count to correcting it. "The other four" corrected to "the other six" is the same
defect with a fresh number, and it will drift again the next time a spec is amended, which happens
roughly weekly here.

## Risks and rollback

One file, prose only, so the more-than-one-module rule does not fire and this section is short.

The one way to get this wrong is to lose the argument while fixing the coordinates. The paragraph is
the only place that records *why* the table is a stopgap, and a tidier sentence that drops the reason
is a worse document than a sentence with a wrong ordinal.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] The paragraph contains no ordinal or count referring to rows of the table it sits under, verified
      by reading it rather than by grep.
- [ ] It still names `house-review` and still states why that note is invisible to a search.
- [ ] The argument for eventually replacing the table with a marker key survives.
- [ ] No table row, `status` field, or spec is modified.
- [ ] The premise was checked: the closeout states whether `house-review`'s note still carries the
      wording the paragraph attributes to it.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
