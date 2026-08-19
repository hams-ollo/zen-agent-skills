---
name: pr-describe
description: Draft a pull request description and a matching changelog entry from a branch's diff, in the target repo's own changelog format, without touching GitHub. Determines the PR's commit range (the current branch against its merge-base with the default branch), surveys what changed, then produces a structured PR body plus a changelog line that references the work item when a .tasks/ system is present. Outputs text and surfaces the gh command to apply it; it never creates or edits a PR itself. Use when the user says "describe this PR", "write the PR body", "draft a pull request", "summarize my branch for a PR", "changelog entry for this branch", or is about to open a PR and wants the description and changelog written for them. Drafts only, safe with or without gh installed.
license: MIT
---

# pr-describe

The back half of the work spine: after a branch is built, turn its diff into a pull
request description and a matching changelog entry, both in the target repo's own style.
It is the closing bookend to `project-bootstrap` -> `init-worktracking` -> `new-task`.

It **drafts text; it does not touch GitHub.** It reads the diff and writes two artifacts
for the user to place: a PR body and a changelog entry. Creating or editing the actual PR
stays the user's action, surfaced as a `gh` command they run themselves.

## What it produces

1. **A PR body**: a structured description grounded only in what the diff supports, ready to
   paste into GitHub or apply with `gh`.
2. **A changelog entry**: one line (or block) matching the repo's existing `CHANGELOG.md`
   conventions, referencing the work item id when a `.tasks/` system is present.

## Design choices

Settled decisions (resolved with the author); these four are not up for re-litigation:

- **Produces both** a PR body and a changelog entry from a single pass over the diff.
- **Draft text only, never touches GitHub.** It prints both artifacts and surfaces
  `gh pr create` / `gh pr edit --body-file` for the user to run. It works with or without
  `gh` installed. This mirrors `project-bootstrap`'s configs-only, no-surprise-side-effects rule.
- **Changelog format by inspection.** It reads the repo's `CHANGELOG.md` and matches its
  heading, date, and id-reference style, rather than imposing one format. With no changelog
  present, it falls back to the [Keep a Changelog](https://keepachangelog.com) convention.
- **Default range is the branch vs its merge-base with the default branch** (the PR's actual
  commit range), with an explicit base/range override. When the branch is not ahead of base
  (still on the default branch, or the work is uncommitted), it falls back to describing the
  working-tree changes rather than dead-ending.

## Procedure

### Step 1: identify the changeset and survey it

1. Confirm this is a git repo with at least one commit (`git rev-parse --is-inside-work-tree`,
   `git rev-parse HEAD`). If there are no commits yet, say so and stop.
2. Find the current branch: `git rev-parse --abbrev-ref HEAD`.
3. Find the default branch robustly: `git symbolic-ref --quiet refs/remotes/origin/HEAD`
   (strip to the leaf name); if unset, try `origin/main` then `origin/master`, then local
   `main`/`master`. If none resolves, ask the user for the base.
4. Determine what to describe. Compute the base `git merge-base HEAD <default>` and consider
   two sources, honoring any explicit base/range the user gave:
   - **Committed range** `<base>..HEAD`: the commits this branch adds over the default branch.
   - **Working-tree changes**: tracked edits (`git diff HEAD`) plus untracked files
     (`git ls-files --others --exclude-standard`).

   Then pick the changeset:
   - Branch is ahead of base -> describe the committed range. If uncommitted changes also
     exist, note them and offer to fold them in.
   - Committed range is empty (you are on the default branch, or the work is not yet committed
     to a feature branch) -> **fall back to the working-tree changes.** This is the common
     "still on `main` / haven't branched yet" case; do not dead-end on it.
   - Both empty -> there is genuinely nothing to describe; say so and stop.

   When on the default branch, mention that the work is not on a feature branch yet (the user
   may want to `git switch -c` before opening a PR), but still produce the description.
5. Survey, do not dump: `--stat` for the shape and the actual diff for substance. Use
   `git log --oneline <base>..HEAD` for intent **when commits exist**; for an uncommitted
   changeset there are no commit messages, so draw intent from any matching `.tasks/` files,
   the branch name, or the user. Note the files/areas touched and the test files among them.

### Step 2: draft the PR body

Write a description grounded only in what the diff and commits support. Never invent a
section the change does not justify. A typical shape, trimmed to fit the change:

- **Title**: an imperative one-liner (from the branch name or the dominant commit).
- **Summary**: one to three sentences on what this PR does.
- **Context / motivation**: why the change was made (from commit messages, a linked task,
  or the user).
- **What changed**: the substantive changes grouped by area, not a file-by-file restatement
  of the diff.
- **Verification**: how it was checked, from the test files touched or the repo's test
  command; say "not covered by tests" honestly rather than implying coverage that is absent.
- **Follow-ups / out of scope** (optional): only if there is something real to note. When a task
  file this branch completes carries a non-empty `## Decisions` section, fold those entries in
  here, under this heading and under no new one: a rejected alternative, a deliberately open seam,
  or a premise the task got wrong is exactly what a reviewer needs and cannot read off the diff.
  Look in `.tasks/done/` as well as `.tasks/`, the same two places the closing-reference rule below
  already reads. The task template owns which entries are admissible (in this kit, the
  `## Decisions` section of `.tasks/_TEMPLATE.md`), so quote or compress the entries rather than
  re-deriving the list, and emit nothing when the section is absent.

Match the tone and any PR-template headings the repo already uses (check
`.github/PULL_REQUEST_TEMPLATE.md` if present and fill it rather than overriding it).

#### Close the linked issue, when a task names one

A task file may carry an `external` field naming the upstream issue it serves (`#123` for
this repository, `owner/repo#123` for another). When the PR completes such a task, put a
closing reference in the body so merging closes the issue instead of leaving someone to
remember. Emit the value verbatim after the keyword; it is already stored in the syntax
GitHub expects.

Four rules, each of which fails **silently** when broken, producing a PR that looks correct,
merges cleanly, and leaves the tracker wrong:

- **In the description, never the title.** GitHub ignores a closing keyword in a PR title
  and in comments. Only the body counts.
- **Repeat the keyword per issue.** `Closes #1, #2, #3` closes only `#1`. Write
  `Closes #1`, `Closes #2`, `Closes #3`, one per line.
- **Only the default branch closes anything.** You already computed the merge-base against
  the default branch in Step 1, so you know the base. When the PR targets anything else,
  emit the bare reference **without** a keyword and say plainly that GitHub will not close
  the issue on merge because the target is not the default branch. Emitting an inert keyword
  is worse than emitting none: it reads as done and does nothing.
- **A completed task still counts.** A branch usually moves its task file into `.tasks/done/`
  in the same change, so look there as well as in `.tasks/`. The PR is what completes the
  work, so its merge is exactly when the issue should close.

Emit nothing when no task names an issue, and nothing when you cannot tell which task the
branch completes. A missing reference costs a manual close; a wrong one closes someone
else's issue.

The contract behind this is `docs/spec/tracker-links.md` in the Zen Agent Skills repository.
Other trackers use the same shape with a different token, so the rule is the placement, not
the vocabulary.

### Step 3: draft the changelog entry (by inspection)

1. Look for `CHANGELOG.md` (or `HISTORY.md`/`CHANGES.md`). If present, infer its style from
   existing entries: heading structure (e.g. `## [x.y.z]`, `## [Unreleased]`, or a running
   task log), date format, bullet style, and whether entries cite task ids or PR numbers.
2. Produce **one** new entry in that exact style. Keep it to the change's user-visible
   essence, not a diff restatement.
3. If a `.tasks/` system is present, detect the work-item id from the branch name or commit
   messages (e.g. `feat-0003`) and reference it the way existing entries do.
4. If there is no changelog, draft a Keep a Changelog entry (an `## [Unreleased]` section
   with `Added`/`Changed`/`Fixed` as the change warrants).

Do not rewrite existing changelog history. Output the new entry as text; then **offer** to
append just that entry at the correct spot (an additive, never-clobbering local edit) if the
user wants it written for them.

### Step 4: output and offer the gh command

Print both artifacts clearly separated. Then surface, but do not run, the commands the user
can execute themselves, for example:

- Create the PR: `gh pr create --title "<title>" --body-file <file>`
- Update an existing PR: `gh pr edit --body-file <file>`

If `gh` is not installed, say the body is ready to paste into GitHub directly. The skill
never calls `gh` or the GitHub API itself.

## Notes

- Drafts only: it reads the diff and writes text (and, if asked, appends one changelog
  entry locally). It never creates or edits a PR, and never rewrites changelog history.
- Portable by inspection: the changelog format and any PR template come from the target
  repo, not from this kit. Do not hardcode this kit's own conventions into another repo.
- It is the closing bookend of the kit spine: `project-bootstrap` -> `init-worktracking`
  -> `new-task` -> (build) -> `pr-describe`.

## Conventions

**The PR body and the changelog entry follow the target repository's conventions**, discovered by
inspection: its existing `CHANGELOG.md` style, its `.github/PULL_REQUEST_TEMPLATE.md` if present, and
its own voice. That rule is the point of this skill and it outranks anything here. Never impose this
kit's formatting on another repo's changelog.

**Your own output**, the summary you report alongside the two drafts, follows the repo's house-style
module (in this kit, [`.agents/rules/house-style.md`](../../rules/house-style.md)): sentence-case
headings, clickable relative links, named sources, no em-dashes. That file is a swappable default; a
downstream adopter may replace it without touching this skill.

**What you may do with the drafts when nobody is watching** follows the repo's autonomy module (in
this kit, [`.agents/rules/autonomy.md`](../../rules/autonomy.md)), which cites this skill for `A8`:
the agent prepares and a person dispatches, so this skill prints both artifacts and surfaces the
command rather than running it, and never merges. That file is a swappable default too; a downstream
adopter may raise or lower the ceiling without touching this skill.
