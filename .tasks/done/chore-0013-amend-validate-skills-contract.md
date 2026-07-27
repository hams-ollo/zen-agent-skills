---
id: chore-0013
title: Amend the approved validate-skills contract to cover the four checks the tool outgrew it by
type: chore
status: done
priority: P1
parent: "ROADMAP Epic B: contract-driven delivery"
depends_on: []
spec: docs/spec/validate-skills.md
scenarios: []
touched_files:
  - docs/spec/validate-skills.md
  - docs/spec/validate-skills.conformance.md
  - scripts/validate-skills.py
  - tests/test_validate_skills.py
created: 2026-07-27
---

## Problem

[`docs/spec/validate-skills.md`](../docs/spec/validate-skills.md) is `status: approved` and describes
eight scenarios. [`scripts/validate-skills.py`](../scripts/validate-skills.py) performs four checks
that appear in none of them:

| Check | Severity | Added by |
|---|---|---|
| A relative link whose target does not exist | error | `feat-0023` (2026-07-25) |
| A `../<name>/SKILL.md` reference to a skill that does not exist | error | `feat-0023` (2026-07-25) |
| A skill asserting both draft and shipped status | warning | `feat-0023` (2026-07-25) |
| A link that escapes the tree the skills are distributed in | error | 2026-07-27 review pass |

The implementation has grown past its contract twice, and both times the response was a note. From
the `feat-0023` changelog entry: "the new behavior goes beyond its approved scenarios, and amending
an approved contract is a separate human decision." That was correct as a boundary (an agent must
not self-approve a contract) but it is not a resolution, and recording it a third time would make it
a habit.

There is a second, sharper cost. [`docs/spec/validate-skills.conformance.md`](../docs/spec/validate-skills.conformance.md)
records `audited: S-001 ... S-008, and all three Proposed Surface elements` with one accepted
divergence. That matrix is honest about what it checked and is nonetheless misleading, because it
certifies full conformance against a contract that now describes less than half of what the tool
does. A reader takes "audited, one accepted divergence" as "this tool is covered". The most valuable
check in the whole validator, the escaping-link check that caught the kit's worst shipping defect,
currently sits outside the contract entirely.

## Scope

**In scope:** amend the spec to cover the four checks, then re-run `spec-conformance` to regenerate
the matrix against the amended contract. A complete draft of the amendment is in Implementation
notes below; it is a draft, not an approval.

**Out of scope:** changing any validator behavior. This is a contract catching up to a verified
implementation, not the reverse. Re-litigating the S-008 accepted divergence, which stands as
recorded. Writing a spec for `install.py` or `build-adapters.py` (the latter is `feat-0026`).

## Implementation notes

The human decision this task needs is only: **accept this amendment, or record the four checks as an
accepted divergence instead.** The recommendation is to amend. An accepted divergence is the right
disposition for a gap you have decided not to close (S-008's natural-language bar is genuinely out of
scope for a stdlib linter); it is the wrong disposition for behavior you deliberately built, tested,
and rely on.

Procedure, respecting the rule that an agent never approves a contract:

1. Set `status: draft` on the spec. It is being reopened, and saying so is the honest state.
2. Apply the amendment below.
3. Run `spec-quality` over the result and revise until `ready`.
4. **A human sets `status: approved`.** Not the agent, and not as part of step 3.
5. Re-run `spec-conformance` to regenerate `validate-skills.conformance.md` against all scenarios.
   Expect S-008 to remain the single accepted divergence.

### Drafted amendment

**Goals**, add a fourth:

> 4. Fail when a skill's cross-references are broken, or when they would break once the skill is
>    distributed away from this repository.

**Non-Goals**, add two:

> - Verifying that a link's target contains what the linking text claims about it.
> - Resolving external URLs, which would require network access.

**Constraints**, add one. This is what makes S-011 unambiguous rather than a rule about path depth:

> - A skill is distributed as a directory alongside its sibling skills and the swappable rules
>   module, without the surrounding repository. A link is therefore legal only if it stays inside
>   that distributed tree: the skill's own files, a sibling skill, or the rules module. A link above
>   it resolves in this repository and dangles everywhere the skill is actually used.

**Scenarios**, add seven. Ids continue from S-008 and are never reused:

> ### Scenario S-009: link to a target that does not exist
>
> - **Given** a `SKILL.md` containing a relative link whose target is not present on disk
> - **When** the validator runs
> - **Then** it records a link-target error naming the unresolved path, and exits non-zero.
>
> ### Scenario S-010: reference to a sibling skill that does not exist
>
> - **Given** a `SKILL.md` referencing a sibling skill that is not present in the kit
> - **When** the validator runs
> - **Then** it records an error naming that skill, and exits non-zero.
>
> ### Scenario S-011: link that escapes the distributed skill tree
>
> - **Given** a `SKILL.md` containing a relative link that resolves above the distributed skill tree,
>   and whose target does exist in this repository
> - **When** the validator runs
> - **Then** it records an error naming the link as non-portable, and exits non-zero. The target's
>   existence in this repository does not satisfy the check, because the skill is not distributed
>   with this repository around it.
>
> ### Scenario S-012: links to the rules module are legal
>
> - **Given** a `SKILL.md` linking to a file in the sibling rules module
> - **When** the validator runs
> - **Then** it records no finding for that link, because the rules module travels with the skills.
>
> ### Scenario S-013: external and same-page links are not resolved
>
> - **Given** a `SKILL.md` containing `http`, `https`, or `mailto` links, or links to an anchor on
>   the same page
> - **When** the validator runs
> - **Then** it records no finding for any of them, and does not attempt to resolve them on disk.
>
> ### Scenario S-014: contradictory status claim warns but does not fail
>
> - **Given** a `SKILL.md` that asserts it is a draft and also records that it shipped
> - **When** the validator runs
> - **Then** it records a warning naming the contradiction, and (absent other errors) exits zero.
>   Only one of the two assertions present is not a contradiction and produces no finding.
>
> ### Scenario S-015: no skills directory
>
> - **Given** an invocation whose target skills directory does not exist
> - **When** the validator runs
> - **Then** it reports the missing directory and exits non-zero, rather than reporting zero skills
>   checked and succeeding.

Note on S-014: the warning severity is deliberate and should be stated as such in the spec, not left
implicit. The phrasing that triggers it is a judgment call, so a false positive must not break a
build. That reasoning is already recorded in the `feat-0023` changelog entry and belongs in the
contract.

Note on scenario coverage: S-009 through S-015 all have existing tests in
[`tests/test_validate_skills.py`](../tests/test_validate_skills.py) except S-015. Either add that
test as part of this task or record the gap explicitly in the regenerated matrix; do not let the
matrix imply coverage that does not exist.

## Acceptance criteria (mechanically verifiable)

    python scripts/validate-skills.py && python -m unittest discover -s tests -p "test_*.py"

- [x] `docs/spec/validate-skills.md` covers all four previously uncontracted checks.
- [x] `spec-quality` returns `ready` on the amended spec.
- [x] A human, not an agent, set `status: approved`.
- [x] `docs/spec/validate-skills.conformance.md` is regenerated and its `audited` set names every
      scenario S-001 through S-016.
- [x] S-008 remains the accepted divergence; no new divergence is silently accepted.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
