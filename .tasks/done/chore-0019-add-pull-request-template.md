---
id: chore-0019
title: Add a pull request template that asks for verification evidence and a closing reference
type: chore
status: done
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [chore-0018]
touched_files:
  - .github/PULL_REQUEST_TEMPLATE.md
  - CONTRIBUTING.md
  - .github/workflows/checks.yml
created: 2026-07-28
---

## Problem

The repository has issue templates but no pull request template, so a pull request arrives with
whatever the author happened to type. Two things go missing as a result, and both have already cost
this project real work.

**Verification evidence.** [`CONTRIBUTING.md`](../../CONTRIBUTING.md) names four commands to run before
opening a change. Nothing asks whether they were run, so a reviewer either takes it on faith or runs
them again.

**The closing reference.** The `tracker-links` feature only pays off if the closing keyword actually
lands in the pull request description. GitHub's rules around that line fail silently in four ways, all
documented in [`docs/ISSUE-LINKING.md`](../../docs/ISSUE-LINKING.md): a keyword in the title is ignored,
one keyword before a list closes only the first issue, the keyword is inert unless the pull request
targets the default branch, and each failure produces a pull request that looks right, merges cleanly,
and leaves the tracker wrong. `pr-describe` knows all four, but a contributor writing a description by
hand does not, and the template is the only place they will be told at the moment it matters.

## Scope

**In scope:** add `.github/PULL_REQUEST_TEMPLATE.md` with three short sections, a summary, how the
change was verified, and the closing-reference reminder. Add one sentence to `CONTRIBUTING.md` so the
template is discoverable before a contributor reaches the pull request form.

**Out of scope:** restating the issue-linking rules at length. The template names the three that bite
and links the guide; `docs/ISSUE-LINKING.md` owns the explanation and must stay the single source.
Multiple templates via a `PULL_REQUEST_TEMPLATE/` directory, which requires a query parameter to
select and is not worth it at this volume. Any CI check that enforces the template.

## Implementation notes

- Keep it short. A long template gets deleted wholesale by the first contributor in a hurry, which is
  worse than no template, because then the reviewer cannot tell whether a section was answered or
  removed.
- The four checks belong as a checkbox list, so an unchecked box is visible rather than merely absent.
  Add one line for what a command cannot prove: a skill exercised on real work, which is exactly what
  the contribution bar in `CONTRIBUTING.md` requires and no command can demonstrate.
- **Use an absolute URL for the `docs/ISSUE-LINKING.md` link, not a relative one.** This is a
  deliberate exception to the house-style rule preferring relative links, and the reason is mechanical:
  the template's text is pasted into a pull request description, and a relative path in a description
  does not resolve to the repository file the way it does from a Markdown file in the tree. A relative
  link here would be a dead link in every pull request that used the template, which is the same class
  of silently-wrong-but-looks-right defect the file exists to warn about.
- Show the keyword in a fenced block so a contributor can copy it. Say "description, not title" in
  those words, since that is the failure the guide reports as most common after the target-branch one.
- This shares `CONTRIBUTING.md` with `chore-0018`, which is why `depends_on` names it. The two are not
  parallel-safe; run them in order rather than dispatching both to isolated agents.
- **`.github/workflows/checks.yml` is in `touched_files` because the `doc-sync` pass put it there,
  not because the template needs it.** CI's link check enumerated six root documents by name, so
  `CODE_OF_CONDUCT.md` and this template both landed outside the only check that would catch a dead
  link in them. Replace the hardcoded list with a glob of root-level, `.github/`, and `docs/`
  Markdown rather than adding two more names, since the list itself is the recurring defect. Run the
  script locally before pushing: it newly covers `CLAUDE.md` too, and a link check that goes red on
  the commit that widens it is a bad trade for a governance file.

## Acceptance criteria (mechanically verifiable)

    python .tasks/validate.py --strict

- [x] `.github/PULL_REQUEST_TEMPLATE.md` exists at the path GitHub reads for a default template.
- [x] It has exactly three top-level sections: a summary, a verification section, and the closing-reference reminder.
- [x] All four `CONTRIBUTING.md` commands appear as checkboxes, matching that file verbatim.
- [x] The description-not-title rule, the one-keyword-per-issue rule, and the default-branch rule each appear in one clause or less.
- [x] The `docs/ISSUE-LINKING.md` link is an absolute URL, so it resolves from a rendered pull request description.
- [x] `CONTRIBUTING.md` mentions the template with a working relative link.
- [x] CI's link check covers `CODE_OF_CONDUCT.md` and `.github/PULL_REQUEST_TEMPLATE.md`, and reports
      more documents checked than before with zero broken links.
- [x] All four repository checks still pass: `python scripts/validate-skills.py`,
      `python -m unittest discover -s tests -p "test_*.py"`, `python .tasks/validate.py --strict`,
      `python scripts/build-adapters.py --dry-run`.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in the `AGENTS.md` conventions section followed, with the absolute-link exception above recorded.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.

## Outcome (2026-07-28)

The template is three sections and 27 lines. The four commands are checkboxes copied verbatim from
`CONTRIBUTING.md`, in the same order, so an unchecked box is visible where a missing sentence would
not be. One line covers what no command can prove, which for this repository means the contribution
bar: a skill exercised on real work.

The absolute URL for `docs/ISSUE-LINKING.md` turned out to be less of an exception than the task
assumed. `.github/ISSUE_TEMPLATE/config.yml` already links `CONTRIBUTING.md` by absolute URL for the
same reason, so this is the established convention for `.github/` content that GitHub renders outside
the file tree, not a deviation from house style. (`skill_behavior.yml` uses a third form,
`../blob/main/SECURITY.md`, which also resolves. Two working conventions in one directory is an
inconsistency, not drift, so it was left alone.)

**The `doc-sync` pass earned its place in the lifecycle on its first run.** CI's link check listed six
root documents by name, so `CODE_OF_CONDUCT.md` and this template both landed outside the only check
that would catch a dead link in them, and nothing in either task would have surfaced that. The
hardcoded list was replaced with a glob over root-level, `.github/`, and `docs/` Markdown, because the
list itself is the recurring defect rather than the two names missing from it. Coverage went from 29
documents to 32, the third addition being `CLAUDE.md`, which had never been checked either. The
extracted script was run locally against the tree first and reported zero broken links, so the commit
that widens the check does not also turn it red.

Worth noting for whoever reads this next: the two new documents contribute no relative links today,
both being external-URL only. The fix is still correct, and the reason it is correct is precisely that
nobody would have noticed for as long as that stayed true.
