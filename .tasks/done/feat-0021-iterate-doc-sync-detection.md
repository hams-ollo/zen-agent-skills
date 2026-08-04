---
id: feat-0021
title: Iterate doc-sync detection from the drift its own dogfood missed
type: feat
status: done
priority: P1
parent: "ROADMAP Kit hardening (2026-07-25 review pass)"
depends_on: []
touched_files:
  - .agents/skills/doc-sync/SKILL.md
created: 2026-07-25
---

## Problem

[`doc-sync`](../../.agents/skills/doc-sync/SKILL.md) was blessed on 2026-07-25 after a dry-run dogfood
that reported 12 findings. A read-only review of all 19 skills later the same day found **at least
four drift instances the dogfood missed**, all of exactly the kind `doc-sync` exists to catch:

| Missed | Why the run missed it |
|---|---|
| [`code-review/SKILL.md:26`](../../.agents/skills/house-review/SKILL.md) "the skill overall is a draft" while line 112 says shipped | "draft" was not in the staleness vocabulary, and the contradiction is between two lines 86 apart |
| [`pr-describe/SKILL.md:25`](../../.agents/skills/pr-describe/SKILL.md) same contradiction | same |
| [`project-bootstrap/SKILL.md:23`](../../.agents/skills/project-bootstrap/SKILL.md) same contradiction | same |
| [`test-quality/SKILL.md:10-11`](../../.agents/skills/test-quality/SKILL.md) "The planned `test-author`" | the claim wraps: "The planned" ends line 10, the skill name opens line 11, and matching was line-scoped |

Two root causes, both in the skill's step 2 guidance rather than in its contract:

1. **Claim matching was line-scoped.** Prose wraps, so a stale qualifier and the thing it qualifies
   routinely land on different lines. Any check anchored to a single line will miss those.
2. **The staleness vocabulary was incomplete and ad hoc.** It covered "planned", "future" and "not
   built" but not "draft", which turned out to be the most common stale status word in this repo.

A third, weaker signal: the skill has no guidance for **intra-document contradiction**, where a
document disagrees with itself rather than with the code. All three self-contradictions are of that
shape, and they are detectable without consulting the repository at all.

## Scope

**In scope:** iterate the prose guidance in
[`.agents/skills/doc-sync/SKILL.md`](../../.agents/skills/doc-sync/SKILL.md) step 2 (and step 3 if the
confidence guidance needs it) to close all three causes: state that claim matching spans sentences
and paragraphs rather than lines; require the staleness vocabulary to be derived from the document
set being audited rather than assumed; and add intra-document contradiction as a first-class thing to
look for, grounded in the document itself as its own evidence.

**Out of scope:** amending [`docs/spec/doc-sync.md`](../../docs/spec/doc-sync.md). It is an **approved
contract** and this iteration should fit inside its existing Goals 1 and 8. If you conclude the
contract genuinely must change, stop and report that rather than editing it; only a human sets a
spec's status. Fixing any of the four missed instances, which belong to `chore-0007`. Building any
detection tooling or script; `doc-sync` is a prose skill.

## Implementation notes

- Keep the body under the 500-line guideline. It is currently 242 lines, so there is room, but prefer
  sharpening the existing three habits in step 2 over appending a fourth section.
- An intra-document contradiction is `confidence: grounded` when both halves are quoted, since no
  interpretation is needed: the document asserts A and not-A. Say so, because it is the cheapest
  high-confidence finding available and the run found none.
- The existing step 2 habit "Do not let formatting define what counts as a reference" came from the
  same dogfood. This task extends the same lesson from formatting to line boundaries; consider
  whether the two belong in one habit rather than two.
- Do not weaken the "a claim you cannot tie to a fact produces no finding at all" rule while widening
  the vocabulary. Widening what counts as a stale word must not widen what counts as evidence.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [x] `.agents/skills/doc-sync/SKILL.md` states that claim matching is not line-scoped.
- [x] It states that the staleness vocabulary is derived from the document set rather than a fixed
      list, and names "draft" among the examples.
- [x] It names intra-document contradiction as a detectable class, and classifies it as `grounded`.
- [x] `docs/spec/doc-sync.md` is byte-for-byte unchanged.
- [x] Body remains under 500 lines; `python scripts/validate-skills.py` exits 0 with 19 skills and no
      new warnings.
- [x] `python .tasks/validate.py --strict` exits 0.
- [x] `python -m unittest discover -s tests -p "test_*.py"` exits 0.
- [x] Every relative markdown link added resolves to a file that exists.
- [x] No em-dashes; headings sentence case.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in the `AGENTS.md` conventions section followed.
- [x] Re-run `doc-sync` in dry-run mode over `.agents/skills/` and confirm it now surfaces all four
      instances in the table above. Record the result.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
