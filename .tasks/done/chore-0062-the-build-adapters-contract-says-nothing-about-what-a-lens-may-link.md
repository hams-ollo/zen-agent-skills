---
id: chore-0062
title: The build-adapters contract says nothing about what a lens may link, which is why a matrix reading unreconciled none shipped alongside seven dangling links
type: chore
status: done
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [bug-0044]
spec: "docs/spec/build-adapters.md"
scenarios: ["S-019"]
touched_files:
  - docs/spec/build-adapters.md
  - docs/spec/build-adapters.conformance.md
  - docs/spec/README.md
created: 2026-08-22
---

## Problem

[`bug-0044`](bug-0044-rules-module-links-dangle-in-the-inlining-adapter-trees.md) fixed seven links
in the rules module that dangled in every `cursor` and `vscode` adapter tree. While fixing them its
agent established why the defect survived, and that reason is this task:

**every link scenario in the contract is about a skill body.** `S-003` through `S-008` and `S-018`
govern links rewritten by `rewrite_links()`, `S-009` governs the targets those rewritten links land
on, and `S-016` governs escape and only for the `plugin` target. **Nothing in the contract states what
a lens may link, or that the rules module is emitted at all in a form whose links must resolve.**

So [`build-adapters.conformance.md`](../../docs/spec/build-adapters.conformance.md) honestly read
`unreconciled: none` while seven links dangled in shipped output. The audit was not careless; it had
nothing to audit against. That is a contract gap presenting as a clean matrix, which is the failure
mode this repository names as its own enemy.

The portability contract in `AGENTS.md` states the rule in prose for skills: a link that escapes
resolves here and dangles everywhere the material actually runs, silently, because the body still
reads correctly and only the target is absent. The lenses ship by the same paths and the same rule
applies to them, and no scenario says so.

`bug-0044` recorded the owed amendment as unreconciled rather than writing it, which was correct.
This is that amendment.

## Scope

**In scope:** state in the contract what the emitted rules module must satisfy.

- A scenario for it, taking the next free `S-NNN` read from the spec rather than assumed.
- **State the property, not the mechanism.** `bug-0044` fixed this by replacing the links with
  backticked names in the source lenses, after establishing that rewriting them on emit is
  *structurally impossible*: `cursor` and `vscode` share one `Layout`, `main()` dedupes layouts, so
  one emitted rules module serves two different adapter paths and no single link text resolves for
  both. The contract should require that every relative link in an emitted lens resolves in the tree
  it was emitted into, not that lenses avoid links.
- The dated amendment note, `status:` left reading `approved` per the convention in
  [`docs/spec/README.md`](../../docs/spec/README.md), and the re-approval queue updated.
- Close the matrix's unreconciled entry and restate the coverage-proof arithmetic with the numbers.

**Out of scope:**

- `scripts/build-adapters.py` and `tests/test_build_adapters.py`. The implementation and its test are
  `bug-0044`'s. **If writing the scenario reveals the behaviour is wrong, that is a finding to report,
  not a code change**, and it is the most valuable thing this task could produce.
- The lens files themselves. They are swappable modules an adopter is invited to rewrite, and
  `bug-0044` recorded the residual risk plainly: an adopter who already took `autonomy.md` keeps their
  edited copy on re-install and therefore keeps the dangling links with no signal. That residual is
  real and is **not** closed by this amendment; say so rather than implying the contract fixes it.
- [`chore-0058`](chore-0058-no-gate-link-checks-the-markdown-under-agents-outside-skills.md), which
  owns the repository-side lint gap. This task is the contract; that one is the gate.
- Granting the re-approval, which is the author's.

## Implementation notes

Read `bug-0044`'s `## Decisions` first. It records four candidate fixes, why three were rejected, and
the measurement behind calling one structurally impossible rather than merely worse. A scenario
written without that will likely mandate the impossible one.

The scenario must hold for all four distribution paths: the three `build-adapters.py` targets and
`install.py`'s layout. `bug-0044` verified all four and reported `0` dangling across them, so the
property is achievable as stated; confirm that rather than inheriting it.

Check whether the queue already carries a `build-adapters` row before adding one. It did as of
2026-08-21, carrying two amendments from `feat-0034` and `chore-0043`. If so, extend it. Per
`house-style.md`, do not introduce a count of the table's rows anywhere in that document.

## Decisions

**Rejected: writing S-019 as an abstinence rule.** The matrix's own "what is owed" text proposed "a
lens may therefore link only what sits beside it in every layout, its sibling lenses, naming a skill
in prose instead", which is `bug-0044`'s chosen fix written into the contract. Rejected on the task's
own risk: a contract that forbids links freezes one fix and makes a lens that may not cite the
material it governs, which is the disconnection `AGENTS.md` names when it says a lens nobody points
at is inert. S-019 states the property (every relative link in an emitted lens resolves where the
lens landed) and records the sibling-lens form as what satisfies it today, not as the requirement.

**Rejected: refreshing the matrix rows that cite `emit_shared_assets()`.** Seven evidence cells name
a function `bug-0025` split into `emit_rules_module()` and `emit_skill_assets()`, so they resolve
nowhere. Repairing them would assert a freshness this pass did not establish, since `chore-0062`
declares one scenario and audited one. Reported as a finding instead, per `autonomy.md` A2 and A6.

**Seam left open deliberately: S-019 states a property over four distribution paths and a test holds
three of them.** `TestEmittedRulesModuleResolves` walks `cursor`, `vscode`, and `plugin`. The sibling
`<base>/../rules` that `install.py` places is walked by no test: `tests/test_install.py` asserts the
module lands where a *skill's* `../../rules/<file>` reference resolves and never reads a link out of
a lens, and the suite's only markdown-link regex is in `tests/test_build_adapters.py`. The fourth
path was resolved by hand for this amendment. The gap is flagged in the matrix rather than filled,
because tests are out of this task's scope.

**Seam left open deliberately: the adopter residual is not closed.** An adopter who took the module
before `bug-0044` corrected the links keeps their copy, keeps the dangling links, and gets no signal,
because S-010 and S-014 preserve an existing rules file unread. S-019 says so in its own words rather
than letting the amendment read as if a contract sentence reached files already on someone's disk.

**Premise corrected: the task named only the re-approval queue in `docs/spec/README.md`, and three
other claims there needed the edit.** The queue row was extended as the task said. Beyond it, the
prose above the queue counts `build-adapters` at two amendments, the specs table carries its scenario
count as 18, and the closing paragraph carries a repository-wide arithmetic (158 scenarios, 145 held
by a matrix, and the subtraction between them) that the nineteenth scenario falsifies. All four were
corrected. No new count was introduced.

**Premise refined: `S-009` does state that the rules module is emitted.** The Problem section says
"nothing in the contract states what a lens may link, or that the rules module is emitted at all in a
form whose links must resolve". The first half holds and the second half is half-true: S-009's Then
says the module exists under the output root, and S-010 and S-014 govern the emitted copy. What no
scenario stated was the *form* it is emitted in. The gap is exactly where the task says, one clause
narrower than the task words it.

## Risks and rollback

A contract plus two sibling documents, so this section is required.

The risk is a scenario that forbids links in lenses rather than requiring them to resolve. That would
be simpler to check and would make the lenses worse: a lens that may not point at the skill composing
it is exactly the disconnection `AGENTS.md` warns about when it says a lens nobody points at is inert.
Require resolution, not abstinence.

Reversible by reverting one commit. `status: approved` is left as the convention requires.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] `build-adapters.md` carries a scenario for the emitted rules module's links, with an id taken
      from the spec rather than assumed.
- [x] The scenario requires that every relative link in an emitted lens resolves in the tree it was
      emitted into, and does not mandate any particular fix.
- [x] It holds for all four distribution paths, stated explicitly.
- [x] A dated amendment note is added, `status:` still reads `approved`, and the re-approval queue
      reflects it without introducing a count of the table's rows.
- [x] The matrix's unreconciled entry is closed and the coverage-proof arithmetic restated with the
      numbers.
- [x] The adopter residual `bug-0044` recorded is stated rather than implied away.
- [x] No file under `scripts/` or `tests/` is modified.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
