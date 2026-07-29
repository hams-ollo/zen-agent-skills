---
id: chore-0021
title: Release hygiene for v0.1.0, with the publish steps left to the human
type: chore
status: done
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - README.md
  - CHANGELOG.md
created: 2026-07-28
---

## Problem

The repository is public with no tag, no release, and no topics. Three consequences:

- **Nothing is citable.** `SECURITY.md` says the kit is distributed from `main` and adopters pick up
  fixes by pulling, which is honest and also means nobody can say which version they are running or
  report a bug against one.
- **Nothing is discoverable.** GitHub topics are the search surface for a repository like this one, and
  there are none.
- **Nothing tells a reader how this differs from its neighbours.** The nearest projects by function are
  obra/superpowers (parallel subagent development lifecycle) and GitHub Spec Kit (specify, plan, tasks,
  implement). A reader who knows those two has no way to tell from this README what is different here,
  and the difference is real: neither ships an independent verification stage that can return a
  `blocked` verdict, and the standing critique of spec-driven tooling is that acceptance criteria do not
  run and specs drift from the implementation within hours. `verifier-agent` and `doc-sync` are the
  answers to both, and the README does not say so.

## Scope

**In scope:** prepare a `v0.1.0` release. That means: a short README section stating what the kit is and
is not relative to those two neighbours; a `CHANGELOG.md` release heading grouping what `v0.1.0`
contains; and a written, ordered list of the publish steps for the author to run.

**Out of scope, and human-owned:** creating or pushing the tag, cutting the GitHub release, and setting
the repository topics. A public tag on a public repository is effectively permanent and is the first
thing that looks like a release, so an agent prepares it and a person publishes it. Also out of scope:
the full README positioning rewrite, which is a larger roadmap item; this task adds one section, not a
restructure.

## Implementation notes

- **Do not restructure `CHANGELOG.md`.** It is an append-only ledger and its entries are correct as
  written. A release heading is added above the existing entries, not woven through them, and no
  existing line is edited. This is the constraint most likely to be violated by a well-meaning attempt
  to "organise for the release".
- Derive the release contents from the ledger rather than from memory. Every entry is dated and
  references its task id, so the `v0.1.0` set is what is already recorded.
- **The positioning section is three or four sentences, not a manifesto.** What it must say: this is a
  library of portable skills plus the tooling to distribute them, not a framework and not an agent
  runtime; the distinguishing property is evidence discipline (no skill ships without having been used
  on real work, verification is recorded with evidence, and coverage is stated honestly rather than
  implied); and the two capabilities that follow from it are an independent verification stage with a
  `blocked` verdict and documentation-drift detection. Name the neighbours plainly and factually. Do not
  disparage them, and do not claim a comparison that has not been tested: the claim is about what this
  kit ships, not about which is better.
- Version `0.1.0` and not `1.0.0`, because the kit is one maintainer's working library, three skills are
  explicitly held pending real use, and the install story has an open portability question
  (`chore-0020`, `feat-0034`). `0.1.0` says that accurately.
- **Confirm the version number with the author before writing it anywhere.** It appears in the changelog
  heading and the tag, and a published tag is not cheaply retracted.
- For the topics, propose a list rather than setting one: `agent-skills`, `claude-code`, `agents-md`,
  `ai-agents`, `developer-tools`, `spec-driven-development`. The author applies them.
- Write the publish steps as a numbered list in the task's outcome, in the order they must run, with the
  exact commands. That list is the deliverable an agent can produce and a human can execute.

## Risks and rollback

Required: this task's output leads to an irreversible public action, even though it performs none.

The risk is that the prepared material is treated as already published, or that a later session reads
the changelog heading and assumes the tag exists. Word the heading so it describes a prepared release
until the tag is pushed, and state in the task outcome that no tag was created. Everything this task
writes reverts with one commit; the tag it prepares does not, which is why it does not create one.

## Acceptance criteria (mechanically verifiable)

    python .tasks/validate.py --strict

- [x] `README.md` has a section, three or four sentences, naming obra/superpowers and GitHub Spec Kit and stating what this kit is and is not.
- [x] That section makes no comparative quality claim, only claims about what this kit ships.
- [x] `CHANGELOG.md` has a `v0.1.0` heading above the existing entries, and **no existing line is edited**, verified by the diff touching only added lines.
- [x] The version number is confirmed with the author before it is written.
- [x] The task outcome carries the ordered publish steps with exact commands, and a proposed topic list.
- [x] No tag exists, no release exists, and no repository setting changed: `git tag --list` is empty and `gh release list` is empty.
- [x] All four repository checks still pass.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in the `AGENTS.md` conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.

---

## Outcome

**Nothing was published.** No tag was created, no release was cut, and no repository setting was
changed. `git tag --list` and `gh release list` were both empty when this task closed and are meant to
stay that way until a person runs the steps below. The [`CHANGELOG.md`](../../CHANGELOG.md) heading is
deliberately worded `prepared 2026-07-29, not yet tagged` so that a later session reading it cannot
mistake a plan for history.

What was written: a `How this relates to adjacent projects` section in
[`README.md`](../../README.md), placed after `Why this repository exists`, and a `Releases` section in
[`CHANGELOG.md`](../../CHANGELOG.md) above the task log, plus one dated task-log line. The version
number `0.1.0` was confirmed with the author on 2026-07-29 before it was written anywhere.

### Publish steps, in order

Run these from a clean checkout of `main`, after the prepared changes have landed there. Steps 1 to 3
are the gate; steps 4 and 5 are the irreversible part.

1. **Land this preparation on `main` and confirm the tree is clean.**

       git switch main
       git pull --ff-only
       git status --short

2. **Re-run every check on the exact commit that will be tagged.** Do not tag a commit whose checks were
   run on a different tree.

       python scripts/validate-skills.py
       python -m unittest discover -s tests -p "test_*.py"
       python .tasks/validate.py --strict
       python scripts/build-adapters.py --dry-run
       python scripts/install.py --dry-run --home ./.tmp/zen-home

3. **Confirm nothing is published yet.** Both commands must print nothing.

       git tag --list
       gh release list

4. **Create the annotated tag, then push it.** This is the first irreversible step. An annotated tag
   (`-a`) is used rather than a lightweight one so the tag carries a date and an author.

       git tag -a v0.1.0 -m "v0.1.0: first versioned cut of the portable skills library"
       git push origin v0.1.0

5. **Cut the GitHub release against that tag.** `--verify-tag` is not optional here: without it,
   `gh release create` will happily create a tag of its own if the push in step 4 did not land, which is
   how a release ends up pointing at a commit nobody checked.

       gh release create v0.1.0 --verify-tag --title "v0.1.0" --notes "First versioned cut of Zen Agent Skills: 19 portable skills, two swappable lenses, and the tooling to distribute them across Claude Code, OpenCode, Cursor, and VS Code or Copilot. See CHANGELOG.md for the full contents."

6. **Apply the repository topics** (proposed list below; the author decides the final set).

       gh repo edit hams-ollo/zen-agent-skills \
         --add-topic agent-skills \
         --add-topic claude-code \
         --add-topic agents-md \
         --add-topic ai-agents \
         --add-topic developer-tools \
         --add-topic spec-driven-development

7. **Retire the two claims the tag falsifies.** Both are correct today and stop being correct at step 4,
   so they are edits to make after publishing, not before.

   - [`CHANGELOG.md`](../../CHANGELOG.md): change `### v0.1.0 (prepared 2026-07-29, not yet tagged)` to
     `### v0.1.0 (2026-07-29)` and drop the paragraph beginning `**No tag and no GitHub release exist
     yet.**`. This is the only edit to that section that is not append-only, and it is correct precisely
     because the condition it described has ended.
   - [`SECURITY.md`](../../SECURITY.md), `Supported versions`: it currently reads "There are no releases
     or version branches yet, so fixes land on `main` and adopters pick them up by pulling", and ends
     "If that changes, this section will say so." Step 4 is that change. Say which version is current
     and whether fixes still land only on `main`.

   Then commit both, and re-run the link check.

8. **Verify the published state.**

       git tag --list
       gh release view v0.1.0
       gh repo view hams-ollo/zen-agent-skills --json repositoryTopics

### Proposed topics

Proposed, not applied. The author sets them in step 6.

`agent-skills`, `claude-code`, `agents-md`, `ai-agents`, `developer-tools`, `spec-driven-development`

### Findings

- **The `doc-sync` pass found one claim the release will falsify, and it is in a document this task does
  not touch.** [`SECURITY.md`](../../SECURITY.md) says "There are no releases or version branches yet"
  and promises "If that changes, this section will say so". It is accurate right now, because nothing
  was published, so it is not drift and was deliberately left unedited. It becomes wrong at step 4,
  which is why the retraction is a numbered publish step rather than a note. A release prepared without
  that step would have shipped a security policy contradicting the repository's own releases page.
- **The task's version rationale was partly wrong, and the changelog does not repeat it.** This file
  justifies `0.1.0` partly on "three skills are explicitly held pending real use".
  [`docs/CATALOG.md`](../../docs/CATALOG.md) holds two, `ci-scaffold` and `release-cut`, and both are
  *unbuilt* skills held until they have been used twice, not shipped skills awaiting exercise. Every
  skill under `.agents/skills/` is listed as shipped. The rationale written into `CHANGELOG.md`
  therefore rests on the two claims that check out: the one-maintainer bar, and the open install
  portability question (`chore-0020`, `feat-0034`).
- **The acceptance criteria say "all four repository checks" and there are five.**
  [`.github/workflows/checks.yml`](../../.github/workflows/checks.yml) runs `validate-skills.py`, the
  test suite, `.tasks/validate.py --strict`, `build-adapters.py --dry-run`, and
  `install.py --dry-run`, plus a real install/re-install/uninstall cycle and a relative-link check. All
  five preview checks and the link check were run for this task and pass. The stale count is
  cosmetic here, but it is the same "hardcoded list drifts" defect `chore-0019` fixed in the link
  checker.
- **The neighbours are named as repository slugs rather than hyperlinked.** `obra/superpowers` and
  `github/spec-kit` identify both projects unambiguously on GitHub, and a slug cannot rot into a wrong
  URL in the most-read section of a public README. Adding links later is a one-line edit.
