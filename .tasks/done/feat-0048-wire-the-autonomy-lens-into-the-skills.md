---
id: feat-0048
title: Wire autonomy.md into the five skills whose rules it consolidates, and guard the next lens against arriving unwired
type: feat
status: done
priority: P1
parent: "ROADMAP Epic E #3: harden autonomy.md from what item 2's run revealed, then bless it"
depends_on: [feat-0047]
touched_files:
  - .agents/rules/autonomy.md
  - .agents/skills/fix-batch/SKILL.md
  - .agents/skills/verifier-agent/SKILL.md
  - .agents/skills/doc-sync/SKILL.md
  - .agents/skills/spec-conformance/SKILL.md
  - .agents/skills/pr-describe/SKILL.md
  - scripts/validate-skills.py
  - tests/test_validate_skills.py
created: 2026-08-18
---

## Problem

[`autonomy.md`](../../.agents/rules/autonomy.md) opens by calling itself "a **swappable module**, the
third beside [`house-style.md`] and [`review-quality.md`]". No skill composes it. Measured 2026-08-18:

```text
$ grep -rn "autonomy" .agents/skills/
(no output)
```

For comparison, all 20 skills reference `house-style.md` and 5 reference `review-quality.md`. The
asymmetry is not cosmetic, because of what the file itself claims: "**v1 is a consolidation, not an
invention.** Every rule below was already being applied somewhere in this kit, in prose, one skill at a
time, without the thing they have in common ever being named." It then links outward into `fix-batch`,
`verifier-agent`, `doc-sync`, `spec-conformance` and `pr-describe`. None of those five links back.

Two consequences follow. An agent running one of those skills reads its inline prose rule and never
reaches the lens, so the consolidation buys the reader of `autonomy.md` a single view and buys the
agent nothing. And where the inline prose and the lens disagree, which will happen the first time one
of them is edited, nothing says which is canonical.

It is also the gating item under its own epic. ROADMAP Epic E #3 is "harden `autonomy.md` from what
item 2's run revealed, then bless it", and the contribution bar in AGENTS.md is that no skill ships
cold: drafted, used on real work, iterated, then blessed. A module no skill composes cannot be
exercised by using the kit, so it cannot be blessed on this repository's own terms. Its `--check`
machinery, its install path, and `bug-0022`'s deleted-lens reporting all already treat it as a lens.
Only the skills do not.

## Scope

The question this task originally posed (lens or document) was answered by the author on 2026-08-18
before dispatch: **lens**. See the decisions section. What remains is the wiring and the guard.

**In scope:**

- Add a reference to `autonomy.md` from each of the five skills whose rules it consolidates, in the
  same shape those skills already use for `house-style.md` and `review-quality.md`.
- Extend [`validate-skills.py`](../../scripts/validate-skills.py) with a rule that a file in
  `.agents/rules/` presenting itself as a lens has at least one inbound reference from a skill. That
  rule is the durable half: it is what stops the next lens from arriving unwired.

**Out of scope:**

- Changing any rule *in* `autonomy.md`. Whether A1 to A8 are the right ceiling is Epic E #3's other
  half, and it is answered by evidence from a real unattended run, not by this task.
- The five skills' inline autonomy prose. If wiring is chosen, add the reference and leave the prose;
  deciding whether each inline rule should then be deleted in favour of the lens is a second pass that
  needs the reference to exist first.
- Adding a fourth lens. ROADMAP Epic B #20 is held behind this task for exactly this reason.
- `house-style.md` and `review-quality.md`, which are correctly wired.
- Re-opening the lens-versus-document choice. It is settled; see the decisions section.

## Implementation notes

Read `autonomy.md`'s own outbound links first. It names the five skills and, for each, the rule it
claims to have consolidated. That list is the wiring list: a skill gets a reference if and only if the
lens claims one of its rules. Do not add a reference to a skill the lens says nothing about, which
would make the lens look composed without making it load-bearing.

Mirror the existing reference shape rather than inventing one. `house-review` shows the heavy form
(multiple in-body citations at the point each rule is used) and most skills show the light form (one
line in a `## Conventions` section). The light form is right here: the lens states a ceiling, not a
procedure, so the natural sentence is that unattended behaviour follows it.

For the validator rule, the detection has to be cheap and unambiguous. Keying off a self-declaration
in the rules file (a file under `.agents/rules/` whose opening calls itself a swappable module or a
lens) is more honest than hardcoding three filenames, because it fails for the next lens too. Say in
the test why the bound was chosen, matching how `bug-0026` asks its own drift assertion to be bounded.

`depends_on: [feat-0047]` is logical, not a file collision: that task decides whether an
untrusted-content rule enters `autonomy.md`, and wiring a lens whose contents are still moving means
doing the reference pass twice.

## Decisions

- **2026-08-18, author: `autonomy.md` stays a lens and gets wired in.** The alternative on the table
  was to demote it to a plain document, strike the "third beside" claim, and let the five skills keep
  stating their autonomy rules inline. Declined for two reasons. The wiring is what makes the module
  swappable in practice: an adopter who rewrites the ceiling wants that rewrite to reach the skills,
  which it cannot do while no skill reads it. And demoting it would leave ROADMAP Epic E #3 with
  nothing to bless, since a document that no skill composes cannot be exercised by using the kit.
  Recorded here so a later reader does not re-litigate it.

- **2026-08-19, implementation: each reference names the specific rule the lens consolidates from
  that skill, not just the module.** The light `house-style.md` shape was mirrored as instructed, one
  paragraph in each `## Conventions` section, but the sentence cites `A1`, `A2`, `A4` and `A5` in
  `fix-batch`, `A6` in `spec-conformance`, `A7` in `verifier-agent`, `A8` in `pr-describe`, and the
  governing principle in `doc-sync`. The wiring list is the lens's own outbound links, so naming the
  rule at each end makes the pair checkable in both directions: a reader arriving from either file
  can see whether the claim still holds. A bare "follow the autonomy module" would have satisfied the
  validator while leaving the same asymmetry the problem section describes.

- **2026-08-19, implementation: the references do not declare the lens canonical over a skill's
  inline prose.** The problem section names that ambiguity, and it was tempting to settle it here.
  Declined: `autonomy.md`'s own Scope section already says "a skill may state a local exception", so
  a reference asserting the module outranks the skill would contradict the module it is wiring in.
  The reference states that the module is a swappable default and the ceiling may be retuned, which
  is what the `house-style.md` references say. Reconciling each inline rule against the lens is the
  second pass this task already puts out of scope.

- **2026-08-19, implementation: the validator rule keys off a self-declaration in the file's opening
  and requires an inbound reference that names the file.** Two bounds, each chosen against a specific
  failure. The declaration is read only in the first `LENS_DECLARATION_LINES` (10) lines, because
  `LENS_DECLARATION_RE` matches the bare word "lens", which any rules document may use when
  describing its neighbours; all three shipped lenses declare by line 3, so 10 has margin, and the
  test asserts both that margin and an upper bound rather than the bare number. A reference must
  contain the lens's filename (`autonomy.md`), not the bare subject word, or a skill merely
  discussing the topic would satisfy the rule while giving a reader no way to reach the module. A
  prose mention naming the file counts as well as a link, because the portability contract in
  `AGENTS.md` tells a skill to name some files in prose rather than link to them.

- **2026-08-19, implementation: the check runs once over the whole tree, after the per-skill loop.**
  `validate-skills.py` iterated only over `.agents/skills/` and never read `.agents/rules/`, which is
  exactly why the gap was invisible. "No skill references this lens" is a fact about every skill
  together rather than about any one of them, so it is a single pass over `portable_root / "rules"`,
  skipped when no sibling `rules/` directory exists. Placing it inside the per-skill loop would have
  reported the same lens once per skill.

## Risks and rollback

Touches five skill bodies, a lens, the kit-level validator and its tests, so it meets the
more-than-one-module rule. The new validator rule is the part that can fail badly: written too
broadly it fails the build for `house-style.md`-shaped files that are deliberately not lenses, and
written too narrowly it never fires again. Exercise it both ways, with a fixture rules file that is a
lens and one that is not.

The wiring itself is inert by construction. Adding a reference changes what an agent can reach, not
what it must do, so the failure direction is an agent reading one more short file.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [x] Each of the five skills the lens names carries a reference to it, and
      `grep -rl "autonomy" .agents/skills/` lists exactly those five, no more and no fewer.
- [x] `validate-skills.py` fails when a self-declared lens under `.agents/rules/` has no inbound
      reference from any skill, proven by a test that removes the references and asserts the non-zero
      exit.
- [x] The new validator rule is exercised in both directions (a lens without references fails; a
      non-lens rules file without references passes).
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
