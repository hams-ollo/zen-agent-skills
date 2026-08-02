---
id: chore-0007
title: Clear seven stale status claims across six shipped skills
type: chore
status: done
priority: P2
parent: "ROADMAP Kit hardening (2026-07-25 review pass)"
depends_on: []
touched_files:
  - .agents/skills/code-review/SKILL.md
  - .agents/skills/pr-describe/SKILL.md
  - .agents/skills/project-bootstrap/SKILL.md
  - .agents/skills/test-quality/SKILL.md
  - .agents/skills/spec-conformance/SKILL.md
  - .agents/skills/spec-quality/SKILL.md
created: 2026-07-25
---

## Problem

Six shipped skills carry status claims that stopped being true. Three of them contradict themselves
inside a single file, saying they are a draft and that they shipped.

**Self-contradictory (says draft and shipped):**

| Location | Claim | Contradicted by |
|---|---|---|
| [`code-review/SKILL.md:26`](../../.agents/skills/house-review/SKILL.md) | "the skill overall is a draft pending field iteration" | line 112, "Shipped 2026-07-24, blessed after dogfooding" |
| [`pr-describe/SKILL.md:25-26`](../../.agents/skills/pr-describe/SKILL.md) | "the skill overall is a draft pending field iteration" | line 124, "Shipped 2026-07-24, blessed" |
| [`project-bootstrap/SKILL.md:23-24`](../../.agents/skills/project-bootstrap/SKILL.md) | "the skill overall is still a draft pending field iteration" | line 100, "Shipped 2026-07-24" |

**Stale forward-references to skills that now exist:**

| Location | Claim | Fact |
|---|---|---|
| [`test-quality/SKILL.md:10-11`](../../.agents/skills/test-quality/SKILL.md) | "The planned `test-author` skill composes this lens" | `test-author` shipped 2026-07-24 |
| [`code-review/SKILL.md:110`](../../.agents/skills/house-review/SKILL.md) | "a future `test-quality`" | `test-quality` shipped 2026-07-24 |
| [`spec-conformance/SKILL.md:12`](../../.agents/skills/spec-conformance/SKILL.md) | "`verifier-agent`, a planned kit skill" | `verifier-agent` shipped 2026-07-24 |
| [`spec-quality/SKILL.md:16`](../../.agents/skills/spec-quality/SKILL.md) | "`spec-author` (a planned skill in this kit)" | `spec-author` shipped 2026-07-24 |

These misinform any agent reading the skill and undercut the kit's claim that its own documentation
tracks reality.

## Scope

**In scope:** correct all seven claims in the six named files. For the three self-contradictions,
keep the "settled decisions" framing (those decisions genuinely are settled) and drop only the
draft-status assertion. For the four forward-references, drop the "planned" or "future" qualifier and
let the existing link stand.

**Out of scope:** any other edit to these six files. Re-litigating the settled design decisions the
contradictory sentences introduce. `code-review:109`'s "Future direction (not built yet): a multi-lens
deep-review" is still accurate, since `review-depth` is unbuilt; leave it, but see the note below.

## Implementation notes

- Follow [`doc-revise`](../../.agents/skills/doc-revise/SKILL.md): smallest sufficient change, preserve
  each file's voice, do not reformat surrounding prose that is fine.
- `test-quality:10-11` splits its claim across two lines ("The planned" ends line 10, the skill name
  opens line 11). Read the sentence, not the line.
- `spec-conformance:12` and `spec-quality:16` were the two files repointed by `chore-0006`; this is a
  different defect in the same paragraphs, so re-read them as they stand now.
- Optional, if it reads naturally: `code-review:109`'s deep-review note could name
  [`review-depth`](../../ROADMAP.md) as the roadmap item that covers it, rather than describing it
  anonymously. Not required.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [x] No shipped skill asserts it is a draft. `grep -rn "is a draft\|is still a draft" .agents/skills/`
      returns nothing.
- [x] `grep -rn "planned \`\?test-author\|future \`\?test-quality\|planned kit skill\|a planned skill" .agents/skills/`
      returns nothing.
- [x] Each of the seven claims listed above is corrected.
- [x] `python scripts/validate-skills.py` exits 0 with 19 skills and no new warnings (watch the
      description length floor: `spec-conformance`'s frontmatter is edited by this task only if the
      claim is in it, which it is not).
- [x] `python -m unittest discover -s tests -p "test_*.py"` exits 0.
- [x] No line other than those carrying a stale claim is changed.
- [x] No em-dashes; headings sentence case.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in the `AGENTS.md` conventions section followed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
