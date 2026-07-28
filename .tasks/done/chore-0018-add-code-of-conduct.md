---
id: chore-0018
title: Add a Contributor Covenant code of conduct and link it from the contributor docs
type: chore
status: done
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - CODE_OF_CONDUCT.md
  - README.md
  - CONTRIBUTING.md
created: 2026-07-28
---

## Problem

The repository is public and takes outside contributions, but it has no code of conduct. Every other
contributor-facing document is in place: [`CONTRIBUTING.md`](../../CONTRIBUTING.md) states the bar,
[`SECURITY.md`](../../SECURITY.md) states the private reporting channel, and
[`.github/ISSUE_TEMPLATE/`](../../.github/ISSUE_TEMPLATE/) covers the two report kinds the project wants.
The code of conduct is the one standard file missing, so GitHub's community profile shows it as absent
and a contributor has nothing to point at if someone behaves badly.

This matters more than the usual boilerplate argument. The most valuable report this project can
receive, per `CONTRIBUTING.md`, is one where a contributor says a skill did something other than what
it promised. That report is an admission that the reporter trusted the kit and got burned, and people
do not file those into a project with no stated conduct expectations.

## Scope

**In scope:** add `CODE_OF_CONDUCT.md` at the repository root, holding Contributor Covenant 2.1 with
its attribution block intact and its contact placeholder replaced by a real channel. Link it from the
repository-layout table in [`README.md`](../../README.md), next to the existing `CONTRIBUTING.md` and
`SECURITY.md` rows, and from `CONTRIBUTING.md`.

**Out of scope:** writing a bespoke code of conduct, or editing the covenant's substance. Adding a
`.github/` copy: GitHub finds the root file, and a second copy is a second thing to keep in sync.
Changing `SECURITY.md`, whose reporting channel this reuses but whose scope is separate.

## Implementation notes

- Use Contributor Covenant **2.1** verbatim, the current version at
  `https://www.contributor-covenant.org/version/2/1/code_of_conduct.html`. It is CC BY 4.0 and is
  meant to be adopted as-is, so keep the Attribution section and its link definitions.
- **Two deliberate house-style exceptions**, both because this is a third-party document adopted
  verbatim rather than prose written here. Its headings are Title Case, and its enforcement ladder
  uses `**Community Impact**` / `**Consequence**` bold labels. Do not sentence-case them: an edited
  covenant is no longer the covenant, and the value of boilerplate is that a reader recognises it on
  sight. Record the exception rather than leaving it to look like an oversight.
- **The contact method must not be a personal email address.** `SECURITY.md` deliberately routes
  private reports through GitHub's private vulnerability reporting rather than publishing an address,
  and this file should not undo that decision by publishing one three files away. Point the covenant's
  enforcement contact at the same private channel and say plainly that it is the only private channel
  the repository has. If the author later wants a dedicated address, that is a one-line edit and their
  call to make, not an agent's.
- Keep both cross-links short. `README.md`'s layout table wants one row. `CONTRIBUTING.md` wants one
  sentence, and its `Reporting problems` section is the natural home, since that is where a reader is
  already being told which channel handles what.

## Acceptance criteria (mechanically verifiable)

    python .tasks/validate.py --strict

- [x] `CODE_OF_CONDUCT.md` exists at the repository root, where GitHub's community profile looks for it.
- [x] No `INSERT CONTACT METHOD` placeholder remains anywhere in the file.
- [x] No email address appears in the file.
- [x] The Attribution section and its five link definitions are present and resolve.
- [x] `README.md`'s repository-layout table has a `CODE_OF_CONDUCT.md` row with a working relative link.
- [x] `CONTRIBUTING.md` references the file with a working relative link.
- [x] All four repository checks still pass: `python scripts/validate-skills.py`,
      `python -m unittest discover -s tests -p "test_*.py"`, `python .tasks/validate.py --strict`,
      `python scripts/build-adapters.py --dry-run`.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in the `AGENTS.md` conventions section followed, with the two covenant exceptions above recorded.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.

## Outcome (2026-07-28)

Contributor Covenant 2.1 landed verbatim at the repository root, with its Attribution section and all
five link definitions intact. The two house-style exceptions the task authorised were taken and are
recorded here rather than left to look like carelessness: the covenant's Title Case headings and its
`**Community Impact**` / `**Consequence**` labels are unchanged, because an edited covenant is no
longer the covenant.

**The contact method is the one substantive decision, and it went the way `SECURITY.md` already
decided it.** The covenant's placeholder wants an address; this repository deliberately publishes
none, routing private reports through GitHub's private vulnerability reporting instead. Publishing a
personal address in the code of conduct would have quietly reversed that choice three files away, so
the enforcement section points at the same private channel and says plainly that it is the only one
the repository has. The form is labelled for security, which is a mismatch worth naming rather than
papering over: the file says so in a clause instead of pretending the fit is clean. Swapping in a
dedicated address later is a one-line edit, and it is the author's call to make, not an agent's.

Both cross-links are one line each: a `README.md` layout-table row beside the existing
`CONTRIBUTING.md` and `SECURITY.md` rows, and a sentence in `CONTRIBUTING.md`'s `Reporting problems`
section, which is where a reader is already learning which channel handles what.

The `doc-sync` pass this closeout ran found that CI's link check enumerated six root documents by
name, so `CODE_OF_CONDUCT.md` fell outside the only check that would catch a dead link in it. The fix
is recorded under `chore-0019`, which owns `checks.yml`, because the same gap covered both new
documents.
