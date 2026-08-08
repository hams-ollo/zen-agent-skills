---
id: chore-0029
title: The third copy of the link rule lives inline in CI and has drifted from the other two
type: chore
status: done
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - .github/workflows/checks.yml
  - .tasks/validate.py
created: 2026-08-06
---

## Problem

The rule for "what counts as a relative link, and does it resolve" exists in **three** places:
[`.tasks/validate.py`](../validate.py), the
[`init-worktracking` template copy](../../.agents/skills/init-worktracking/templates/validate.py), and a
third copy written inline as a heredoc Python script inside
[`checks.yml`](../../.github/workflows/checks.yml), under the step "Check that every relative link in the
docs resolves". The first two are kept in step deliberately, and three tasks in a row (`bug-0011`,
`bug-0012`, `bug-0015`) each recorded that as a constraint. **The third is not kept in step with
anything**, and it has now drifted.

`bug-0015` taught the first two copies that a link inside an inline code span is not a link. The CI
copy has no such notion, and its comment claims kinship it no longer has: the `LINK_RE` comment in
`.tasks/validate.py` says it is "deliberately identical to the regex the docs link step in
`.github/workflows/checks.yml` applies, so the two checks cannot disagree about what counts as a
link". They now disagree.

**This is not theoretical and it cost time on 2026-08-06.** Writing `bug-0015`'s own `CHANGELOG.md`
entry required naming the malformed construct that caused the bug. Quoting it inside a code span is
correct Markdown and passes `python .tasks/validate.py --strict`, and it **failed the CI docs link
step**, which read the quoted example as a live link to `../README.md` from the repository root:

```
broken link: CHANGELOG.md -> ../README.md
checked 38 documents, 1 broken link(s)
```

The entry was reworded to describe the shape in prose, which is exactly the workaround `bug-0015`'s
Problem section predicted any file documenting link syntax would be forced into. `bug-0015` closed
that workaround for `.tasks/` and left it standing for every document at the repository root.

**The two checks also cover disjoint file sets, which is why neither can simply replace the other.**
`validate.py` walks `.tasks/`; the CI step globs root `*.md`, `.github/**`, and `docs/**`. Wave 2's
closeout broke five links and three of them were inbound references in `CHANGELOG.md` and
`ROADMAP.md` that `--strict` passed clean over and only the CI step caught. Both are load-bearing.

## Scope

**In scope:** remove the third copy as a *separately authored* rule. The CI step should call the same
code the other two copies share, rather than restating it, so a future fix lands once. Decide and
record how: extracting the shared rule into a small module both can import is the obvious shape, and
so is giving `validate.py` a flag that checks an arbitrary path set, which would let CI call it
directly with the docs globs.

**Out of scope:**

- Changing which files each check covers. The disjoint coverage above is deliberate and both halves
  have caught real breakage; this task is about one rule with two callers, not one check.
- Changing the mislabelled-link heuristic, which `.tasks/validate.py` has and CI does not, and which
  is a separate decision about whether a warning belongs in a required gate.
- `bug-0017`'s fenced-block case. If it lands first the shared rule inherits it; if not, this task
  does not add it.
- The template copy's other divergences from `.tasks/validate.py`, a missing `external` check and no
  injectable `argv`, which are their own task.

## Implementation notes

**The template copy is the constraint that shapes this.** `init-worktracking` scaffolds a repository
that has no `.github/workflows/checks.yml` from this kit and may have no CI at all, so whatever
shared module is created must still ship inside the scaffolded `validate.py` or the template stops
being self-contained. That rules out a shared module living outside `.tasks/`, and it is the reason
this is not simply "make CI import `validate.py`".

The CI step is written as a `python - <<'PY'` heredoc under `shell: bash`, so it currently depends on
bash on all three runners. Calling a checked-in script instead removes that dependency, which is a
small portability win on Windows worth noting but not worth its own task.

Keep the `LINK_SKIP_PREFIXES` behaviour identical: the CI copy skips `file://` as well, on the
ground that an absolute `file:` link names a location on someone's disk. That comment exists in both
places today and should survive the merge.

## Decisions

- **Rejected: a shared module both callers import.** The obvious shape, and the one this file's Scope
  names first, does not survive the template constraint. `init-worktracking` ships exactly one file
  into an adopter's `.tasks/`, so a second module beside it is either a second file the scaffold has
  to place and keep in step, or an import that resolves here and fails everywhere the scaffold
  actually runs. The rule stayed where it already lives and gained a second **caller** instead: a
  `--links` mode on `validate.py` that link-checks an arbitrary set of globs.
- **Rejected: having CI import `validate.py` as a module.** A `python -c "import ..."` step is still a
  script written in the workflow file, which is the thing that drifted. A flag makes CI call a
  checked-in entry point, so the workflow holds globs and nothing else, and the step drops its
  `shell: bash` dependency as a side effect.
- **`--links` was added to the template copy too**, though this task's `touched_files` names only two
  files. Without it an adopter who wants a docs link gate has to author a fourth copy of the rule,
  which is the defect this task exists to close, one repository over.
- **Seam: `--links` reports broken links only, never the mislabelled-link heuristic.** The gate's
  behaviour is therefore unchanged, per this file's Out of scope. The two modes now share
  `broken_links()` but not `mislabelled_links()`, and promoting a heuristic into a required gate stays
  the separate decision it was.
- **New behaviour beyond "call the rule": zero matched documents is an error.** The risk section names
  a check over an empty file set as the costly failure, and nothing in the old step could tell that
  apart from a clean run, since both print zero broken links. Making an empty match exit non-zero is
  what turns the printed count from a diagnostic into a guard.

## Risks and rollback

Required: this changes a required CI gate, and a link check that silently stops checking is worse
than one that fails, because the failure mode is a green build over a broken tree.

- **The costly failure is a shared rule that runs over an empty file set.** If the globs are wired up
  wrong the step passes instantly and reports zero broken links over zero documents. Mitigate by
  asserting the document count, which the current step already prints (`checked 38 documents`), and
  by deliberately breaking one link in a scratch commit to confirm the gate still fails.
- Rollback is one revert of the workflow file; no persisted format changes.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python .tasks/validate.py --strict

- [x] The link rule is authored in exactly one place, and `.github/workflows/checks.yml` calls it
      rather than restating it.
- [x] The CI step still covers root `*.md`, `.github/**`, and `docs/**`, and still reports the
      document count it checked.
- [x] Running the docs check locally over the current tree reports 38 documents and 0 broken links,
      matching the CI baseline measured 2026-08-06.
- [x] A deliberately broken relative link in one of those documents makes the check exit non-zero,
      demonstrated rather than assumed.
- [x] The `LINK_RE` comment in `.tasks/validate.py` claiming the CI copy is identical is either true
      again or removed.
- [x] The scaffolded template validator is still self-contained: a freshly scaffolded repository
      runs its own `validate.py` with no file from this repository present.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason.
- [x] File moved to `.tasks/done/`, `status: done`, **with its relative links re-anchored for the
      extra directory level**; one dated line added to `CHANGELOG.md` referencing this task id.
