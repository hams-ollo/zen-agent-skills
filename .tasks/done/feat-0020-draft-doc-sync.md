---
id: feat-0020
title: Draft the doc-sync skill (documentation drift detection, from its own spec)
type: feat
status: done
priority: P1
parent: "ROADMAP Epic B #9: doc-sync"
depends_on: []
touched_files:
  - .agents/skills/doc-sync/SKILL.md
created: 2026-07-25
---

## Problem

ROADMAP Epic B item 9 is `doc-sync`: detect documentation drift caused by code changes or audit a
documentation set, distinguishing current-state documents from human-owned contracts, defaulting to
a code-grounded dry run, requiring explicit approval before updating current-state documentation,
and never silently rewriting a contract document. The behavioral contract is approved at
[`docs/spec/doc-sync.md`](../../docs/spec/doc-sync.md), drafted by `spec-author`, self-checked to
`ready` by `spec-quality`, and approved by the maintainer on 2026-07-25 after two open questions
were resolved into the contract.

The kit ships two documentation skills and neither answers the question that generates the work.
[`doc-author`](../../.agents/skills/doc-author/SKILL.md) writes a document that does not exist.
[`doc-revise`](../../.agents/skills/doc-revise/SKILL.md) edits a document someone has already decided
is wrong. Nothing identifies *which* documents went wrong. During the 2026-07-24 session, shipping a
single skill invalidated four to seven documents each time, and every instance was caught by hand.

The roadmap entry attributes this skill to an upstream `document` workflow. That attribution is
false: the vendored `repoprompt-workflows-main/.agents/workflows/` contains only `Backlog.md`,
`Deep-Review.md`, `Loop.md`, `README.md`, `Spec.md`, and `Test.md`, and no `document` skill exists in
the author's global set. The only surviving trace of the upstream contract is
`repoprompt-workflows-main/.agents/workflows/Loop.md:194`, which says to run `document` in dry-run
mode first and never auto-edit contract documents. That is intent to honor, not source to fold in.
This is an authoring job, and correcting the roadmap attribution is part of it.

## Scope

**In scope:** author `.agents/skills/doc-sync/SKILL.md`, harness-agnostic, delivering scenarios
S-001 through S-015 of the spec: classify every document in scope as current-state, contract, or
ledger by property rather than by filename, defaulting an unclassifiable document to contract;
ground every reported finding in a named repository fact and report nothing that cannot be grounded;
default to a dry run that changes no file; report each finding with a stable `D-NNN` id, the
document, its kind, the drifted claim, the evidence, a `grounded` or `suspected` confidence, and a
proposed correction it does not perform; never edit a contract document, reporting the disagreement
as a possible defect in the code instead; skip ledger documents and list the skip with its reason;
return `verdict: clean` with a positive audited set when nothing has drifted; apply corrections only
to current-state documents, only for findings approved by identifier, only if the finding still
reproduces, and only after the human has seen each finding's confidence and evidence; record an
audit trail for every applied change naming the claim corrected, the evidence, and the confidence it
carried; never edit vendored third-party material even when a user names its path; compose
`doc-revise` for editing discipline; and return the report inline unless a destination is supplied.
Cross-link `doc-author`, `doc-revise`, and `spec-conformance`. Mark it a draft in `ROADMAP.md` and
`docs/CATALOG.md`, and correct the false `document` attribution on the roadmap line.

**Out of scope:** blessing the skill, which waits for the dogfood and explicit user sign-off;
changing `doc-author` or `doc-revise`; repointing the dangling `document` references in
`spec-conformance/SKILL.md` and `spec-quality/SKILL.md`, which are the dogfood's known-answer
targets and stay untouched until after the run; hand-fixing any other documentation drift found
while working, for the same reason; building `user-testing` (Epic B #8) or `review-depth`
(Epic B #10); the kit-wide skill evaluation pass (Epic A #8).

## Implementation notes

- Compose [`doc-revise`](../../.agents/skills/doc-revise/SKILL.md) **by reference only**. Do not
  restate its editing rules (preserve voice, smallest sufficient change, verify links); the two must
  not drift. This mirrors how [`verifier-agent`](../../.agents/skills/verifier-agent/SKILL.md) composes
  `spec-conformance`.
- The three document kinds are the skill's core idea and the reason it is not just a linter. State
  the classification as a property test so it travels to repositories this kit has never seen, and
  name the fail-safe: an unclassifiable document is treated as a contract.
- The dry-run default is not a flag, it is the posture. Detection must never change a file.
- Say plainly that there is no exact oracle for prose-versus-code drift and that false positives are
  expected. The `grounded` versus `suspected` split and the stable `D-NNN` ids exist so dismissal
  costs one identifier. Do not claim precision the technique does not have.
- Keep the structure of `verifier-agent/SKILL.md`: intro positioning against siblings,
  `## When to use` / `## When not to use`, `## Inputs`, numbered `## Procedure`, `## Output format`
  with a deterministic schema in a fenced `text` block, `## Notes`, `## Conventions`.
- Follow [`.agents/rules/house-style.md`](../../.agents/rules/house-style.md); keep the body under the
  500-line guideline.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py

- [x] `.agents/skills/doc-sync/SKILL.md` exists with valid frontmatter (`name` equals the directory,
      non-thin `description` saying both what it does and when to use it).
- [x] `scripts/validate-skills.py` exits 0 reporting 19 skills, with no new warnings.
- [x] `python .tasks/validate.py --strict` exits 0.
- [x] `python -m unittest discover -s tests -p "test_*.py"` exits 0, unaffected by this change.
- [x] Body composes `doc-revise` by reference with no inline restatement of its editing rules, and
      cross-links `doc-author` and `spec-conformance`.
- [x] Body names all three document kinds (current-state, contract, ledger), the dry-run default,
      and the never-edit-contract-documents rule.
- [x] Body contains an `## Output format` section defining a deterministic report schema whose
      verdict values are exactly `clean` and `drift_found`, with a stated rule for each.
- [x] Every relative markdown link added resolves to a file that exists.
- [x] No em-dashes; headings sentence case.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md section 6 followed.
- [x] Dogfooded in dry-run mode across this repository's own documentation set, with the findings
      recorded and the skill iterated from what the run taught.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md`
      referencing this task id.
- [x] Skill left as a draft; `ROADMAP.md` and `docs/CATALOG.md` mark it draft (pending sign-off),
      not shipped, and the false `document` attribution on the roadmap line is corrected.
