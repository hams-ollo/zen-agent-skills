---
id: feat-0036
title: Give install.py a mechanical draft marker so no profile distributes an unblessed skill
type: feat
status: open
priority: P1
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
spec: docs/spec/install.md
scenarios: []
touched_files:
  - docs/spec/install.md
  - scripts/install.py
  - scripts/validate-skills.py
  - tests/test_install.py
  - .agents/skills/review-depth/SKILL.md
created: 2026-07-31
---

## Problem

`scripts/install.py` has no way to tell a draft skill from a shipped one, so `--profile all`
distributes an unblessed draft to adopters. Measured 2026-07-31:
`python scripts/install.py --dry-run --profile all --home ./.tmp/zen-home` reports `20 of 20` and
places `review-depth`, which is a draft by every marker this repository uses:
[`feat-0035`](feat-0035-draft-review-depth.md) is `in_progress`, `ROADMAP.md` Epic B item 10 is
unstruck, and [`docs/CATALOG.md`](../docs/CATALOG.md) has no row for it.

[`AGENTS.md`](../AGENTS.md) section 7 states the bar: a freshly drafted skill stays `in_progress`
until it has been used and refined, and only then is it "shipped". `AGENTS.md` is a contract
document, so the code is the suspect and the contract is not to be edited to match it.

**The root cause is that the draft/shipped distinction is prose only.** It lives in `ROADMAP.md` and
`docs/CATALOG.md`, and nothing mechanical carries it, so no tool can act on it. That is why the
installer cannot be blamed for a wrong decision: it is not making one.

**Five documentation claims are false today because of this**, found by the `doc-sync` pass on
2026-07-31 (findings D-001, D-002, D-004, D-005, D-006). Each is true of the blessed set and false of
the tree:

| Document | Claim | Measured |
|---|---|---|
| `README.md:156` | profile table gives `all` as 19 | 20 |
| `README.md:158` | `spine` omits only the two handoff skills | omits three |
| `docs/ARCHITECTURE.md:43` | `spine` "drops the handoff pair" | drops three |
| `docs/ARCHITECTURE.md:43` | only the handoff pair plus the three no-sibling skills are separable | `review-depth` is separable too, since no skill references it |
| `docs/GETTING-STARTED.md:140` | "installs 17 of the 19 skills" | 17 of 20 |

Fixing this task makes all five true again with **no documentation edit**, which is the reason it is
the root fix rather than one repair among six.

## Scope

**In scope:** a mechanical, per-skill draft marker that `install.py` reads, so a draft skill is placed
by no profile, including `all`; the marker applied to `review-depth` as the one current draft; a
scenario added to [`docs/spec/install.md`](../docs/spec/install.md) covering it, since the contract is
silent today; tests proving a draft is placed by no profile.

**Out of scope:** editing `AGENTS.md`, which is a contract and is right; editing the five reader-facing
documents above, which this task makes correct without touching them; blessing `review-depth` or
striking `ROADMAP.md` Epic B item 10, which belongs to `feat-0035`; any change to profile seeds or to
the sibling-closure behaviour beyond making it skip drafts; a general skill lifecycle or status field
for anything other than the draft distinction.

## Implementation notes

- **A bare `status:` frontmatter key is illegal and will fail two validators.**
  `ALLOWED_FRONTMATTER_KEYS` in [`scripts/validate-skills.py:46`](../scripts/validate-skills.py) is an
  allow-list of exactly six properties (`name`, `description`, `license`, `allowed-tools`, `metadata`,
  `compatibility`), sourced from `ALLOWED_PROPERTIES` in Anthropic's `quick_validate.py`. An
  unrecognised key is rejected outright. `bug-0008` exists because a property that looked legal was
  not, and `docs/ARCHITECTURE.md:37` records the lesson: conforming to this kit's own spec is not
  evidence of conforming to the external standard.
- **`metadata` is permitted, so that is the natural home**: something of the shape
  `metadata: {status: draft}`. Verify the choice against both validators before building on it, by
  running `validate-skills.py` and, if it is available, Anthropic's `quick_validate.py`. Prefer this
  over the two alternatives: a draft list inside `install.py` is a second source of truth that will
  drift from `ROADMAP.md`, and parsing `docs/CATALOG.md` or `ROADMAP.md` prose makes placement depend
  on wording.
- **Check the interaction with the existing draft/shipped warning.** `DRAFT_STATUS_RE` in
  [`scripts/validate-skills.py:69`](../scripts/validate-skills.py) already matches
  `^\s*status:\s*draft\b`, and it warns only when draft and shipped language both appear. Confirm a
  frontmatter marker does not make that check fire spuriously, and decide deliberately whether
  `validate-skills.py` should start reading the marker as structured data rather than as prose.
- **Preserve the `feat-0033` closure behaviour.** A profile is expanded over sibling references so it
  can never ship a skill whose composed sibling is absent (S-013). Excluding drafts must not break
  that: decide and state what happens if a shipped skill ever references a draft one, since silently
  dropping the reference would reintroduce the dangling-sibling defect S-013 exists to prevent. No
  such reference exists today, verified 2026-07-31: `review-depth` references three siblings and no
  skill references it.
- **Amend the contract rather than diverging from it.** `docs/spec/install.md` is `status: approved`
  and says nothing about drafts, so this is a gap and not a divergence, which is the distinction
  `bug-0009` turned on. Follow the `feat-0033` precedent recorded at `docs/spec/install.md:13`: amend
  the spec on the author's explicit instruction and re-approve it, then add the scenario id to this
  task's `scenarios` field.
- **The description budget figures move.** S-014 reports `core`, `spine`, and `all` totals, and
  excluding a draft changes the `all` figure. Both `install.conformance.md` rows are now dated, so
  re-anchor rather than silently overwrite them.
- `install.py` is standard library only, by design. The CI workflow has no dependency install step and
  states that needing one is a signal to reconsider the change.

## Risks and rollback

Required: this touches more than one module (`scripts/install.py`, `scripts/validate-skills.py`, and a
skill body), and it changes what a published command distributes.

- **The failure that matters is the inverse of today's**: a marker read too eagerly could exclude a
  shipped skill from every profile, so adopters silently stop receiving it on their next re-install.
  That is worse than the current defect, because the current one over-delivers and the inverse
  under-delivers without any signal. Mitigate by asserting per profile that the placed set is exactly
  the expected named set, not merely a count.
- A wrong marker on a skill that a shipped skill references would drop a composed sibling, the exact
  defect S-013 prevents. The closure test must run against the draft-aware resolution, not around it.
- Rollback is one revert: the change is additive (a marker plus a filter) and writes no new persisted
  format. Adopters who installed during the window keep a `review-depth` directory that a later
  `--uninstall` against the same home still removes, since reversal is driven by the recorded
  manifest rather than by the current profile.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py"

- [ ] New tests proving a draft skill is placed by **no** profile: assert the exact placed set per
      profile by name, not only its size, so the inverse failure above cannot pass.
- [ ] A test proving profile closure still holds with a draft present, so S-013 is not weakened.
- [ ] `python scripts/install.py --dry-run --profile all --home ./.tmp/zen-home` reports 19 of 20 and
      does not mention `review-depth`.
- [ ] `python scripts/validate-skills.py` exits 0 with no new errors and no new warnings, with the
      marker present on `review-depth`.
- [ ] `python .tasks/validate.py --strict` exits 0.
- [ ] `python scripts/build-adapters.py --dry-run` exits 0. State deliberately whether adapter
      generation should also skip drafts, and record the decision either way.
- [ ] Existing tests still pass, unchanged in intent.
- [ ] `docs/spec/install.md` carries a new scenario for the behaviour, is re-approved, and its id is
      recorded in this task's `scenarios` field.
- [ ] The five claims in the Problem table are re-checked and confirmed true again, with no edit to
      any of the three documents.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only
      a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing
      this task id.
