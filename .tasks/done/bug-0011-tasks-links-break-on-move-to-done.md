---
id: bug-0011
title: Check task-file links where the file lives, and repair the 101 the move to done/ broke
type: bug
status: done
priority: P1
parent: "ROADMAP Kit mechanics hardening (2026-07-27 review pass)"
depends_on: []
touched_files:
  - .tasks/validate.py
  - .tasks/done/
  - tests/test_tasks_validate.py
  - .agents/skills/init-worktracking/templates/validate.py
  - .agents/skills/init-worktracking/templates/tasks-README.md.tmpl
  - .tasks/README.md
  - AGENTS.md
created: 2026-07-31
---

## Problem

101 relative markdown links are broken across 36 files in [`.tasks/done/`](../done/), and every command
this repository runs reports success.

The cause is the lifecycle in the work altitude and lifecycle section of [`AGENTS.md`](../../AGENTS.md).
A task file is authored in `.tasks/`, where `../scripts/install.py` and `../docs/spec/foo.md` are the
correct spellings. At closeout the file moves to `.tasks/done/`, where `../` now resolves to `.tasks/`
and every one of those links dangles. Nothing rewrites them, and nothing notices.

Confirmed mechanically on 2026-07-31 by applying the CI step's own regex (`\[[^\]]*\]\(([^)]+)\)`,
skipping `http`/`https`/`mailto` and stripping `#` fragments) over `.tasks/**/*.md` and resolving each
target against the file's own `path.parent`: 69 documents checked, **101 broken links in 36 files, all
of them in `done/`, zero in the open task files**. That distribution is the evidence that the move is
the cause rather than sloppy authoring.

### Why nothing catches it

Both verified, not inferred:

- **CI's link step does not look here.** The "Check that every relative link in the docs resolves" step
  in [`.github/workflows/checks.yml`](../../.github/workflows/checks.yml) globs root-level `*.md`,
  `.github/**/*.md`, and `docs/**/*.md`. `.tasks/` is outside all three.
- **`.tasks/validate.py` has no link check at all.** It checks frontmatter, ids, `depends_on`,
  `touched_files`, `spec`/`scenarios`, and `external`. Grepping it for "link" finds nothing relevant.

**`.agents/` is not affected and must not be swept into this task.**
[`validate-skills.py`](../../scripts/validate-skills.py) already has a `check_links` pass over skill
bodies, and 0 of its 115 relative links are broken. The gap is specific to `.tasks/`.

### The live case

`.tasks/feat-0035-draft-review-depth.md` is in progress on the `feat/draft-review-depth` branch (not
linked, because it is not on this one) with 5 relative links, all of which break the moment it moves to
`done/`. Its own closeout note records this,
which means the defect is currently being worked around by hand instead of being caught.

## Scope

**In scope:**

1. Add a link check to [`.tasks/validate.py`](../validate.py) that resolves every relative markdown link
   against the containing file's actual parent directory, so a link is validated where the file
   currently lives. This makes the check run locally on a bare `python .tasks/validate.py` and in CI
   through the existing `--strict` step, and it fails at the moment of the move rather than months
   later.
2. Repair all 101 existing broken links, so the new check passes on a clean tree.
3. Cover both in [`tests/test_tasks_validate.py`](../../tests/test_tasks_validate.py).
4. **Propagate the check to
   [`.agents/skills/init-worktracking/templates/validate.py`](../../.agents/skills/init-worktracking/templates/validate.py),
   the copy that scaffolds into adopter repositories.** This was not in the original scope and is the
   more important half of the defect. `.tasks/validate.py` is this repository dogfooding its own
   tooling; the template is the deliverable. Fixing only the local copy would leave every repository
   this kit scaffolds emitting the same silently-broken links, while the kit's own build went green.
5. Re-anchor the closeout step in the lifecycle documentation, so an author is told to fix the links
   rather than only being failed by a check afterwards.

**Out of scope:**

- **Adding `.tasks` to the CI step's glob.** That is candidate fix 1 and it was considered and
  rejected: it catches the symptom in CI only, does nothing locally, and would then double-cover the
  same files with a second implementation free to drift. The point of putting the check in
  `validate.py` is that it fires at the move.
- **The three report-only findings from the same review**, all in the CI link step and none of them
  this defect: the `if not path.exists(): continue` guard that is dead code, the check being inline in
  a workflow heredoc so it cannot be run locally, and filesystem resolution being the wrong oracle for
  `.github/PULL_REQUEST_TEMPLATE.md` (a relative repository path does not resolve in a rendered pull
  request description). File them separately if they are worth doing.
- **`.agents/`, `scripts/validate-skills.py`, and the skills themselves.** Already covered, already
  clean. The one exception is the `init-worktracking` template noted above, which is this same
  validator rather than a skill body.
- **Reconciling the rest of the template validator's drift.** It is already two changes behind the
  local copy: it has neither the `external` field check (`feat-0030`) nor the injectable `argv`
  (`chore-0017`). That divergence predates this task and closing it is a separate decision about how
  the two copies should be kept in step at all, which is the real question underneath.
- **`touched_files` existence checking for completed tasks.** Deliberately absent since `chore-0012`;
  see the risks section for why links are the different case rather than an oversight.

## Implementation notes

### The check

Mirror the CI step's semantics exactly, so the two agree on what a link is: the regex
`\[[^\]]*\]\(([^)]+)\)`, target split on `#` and stripped, skip empty targets and anything starting
`http://`, `https://`, or `mailto:`, then test `(path.parent / target).exists()`.

Two details the regex already gets right, both confirmed against real files, so do not "improve" it:

- It requires a complete link: bracketed text followed immediately by a parenthesised target. The open
  task `feat-0034` contains the bare closing fragment `` `](../../rules/house-style.md)` `` inside prose
  describing a link, and the regex correctly ignores it. A looser pattern would produce a false positive
  on documentation *about* links.
- Stripping the `#` fragment means an in-page anchor is not resolved. That is the CI step's behavior
  today and matching it is the goal; anchor validation is separate work.

There is one false-positive class the regex does **not** avoid, inherited from the CI step: a document
that spells out a complete example link is indistinguishable from a document that contains one, because
the scan is over raw text and does not skip code spans or fenced blocks. No document under either
check's file set currently trips this, and this task file deliberately describes link syntax in words
rather than writing it out so that it does not become the first. If a future task file needs a literal
example, that is the moment to teach the check about code fences, not now.

Run it over **every `.md` under `.tasks/`**, not just the files `task_files()` returns.
[`.tasks/README.md`](../README.md) has 6 relative links (all currently resolving) and is exactly as
clickable as a task file; `_TEMPLATE.md` has none. Excluding them buys nothing and leaves a hole.

Report a broken link as an **error**, not a warning, in both `.tasks/` and `.tasks/done/`. A warning
would be identical to an error under CI's `--strict` anyway, so the only thing the softer form would
change is whether a local run tells the truth.

### The repairs

The 101 fall into five classes. Counts are exact as of 2026-07-31 on `main`; re-derive them rather
than trusting these numbers if other work has landed in `done/` since.

| Links | Files | Class | Repair |
|---|---|---|---|
| 87 | 30 | One level too shallow: `../scripts/x.py` from inside `done/` | Add one `../` |
| 4 | 4 | Wrong namespace: `../../rules/house-style.md` | `../../.agents/rules/house-style.md`, matching the link text, which is already correct |
| 4 | 3 | Renamed target: `code-review/SKILL.md`, `code-review.verification.md` | Re-anchor to `house-review`, which `chore-0012` renamed it to |
| 4 | 4 | `../repoprompt-workflows-main/...`, gitignored (`.gitignore:25`) and never present in a checkout | De-link to inline code |
| 2 | 1 | `../docs/PROJECT-STATUS.md`, `../docs/PLATFORM-PITCH.md`, deleted from the repo | De-link to inline code |

The de-link treatment follows the rule already stated in the portability contract section of
`AGENTS.md`: when a document needs to name a file it cannot legally link to, name it in prose rather
than linking to it. In every one of these six cases the link text is already the path, so the edit drops the
surrounding link and leaves the backticked path standing on its own, and nothing is lost.

For the renamed-target class, re-anchor the href and **leave the link text alone**. These four sit in
finding tables that cite a specific line of a file as it was named and numbered at review time
(`code-review/SKILL.md:26`), so the text is a record of what was found where, and rewriting it to the
new name would falsify that record to fix a pointer. This is the `chore-0005` re-anchoring precedent:
the citation stays, the pointer moves to where the file now lives.

**Repair by hand or by script, but verify by re-running the check, not by trusting the sweep.** The 87
are mechanical; the other 14 are judgment calls and a blanket `../` prefix would silently make four of
them wrong in a new way.

### Prior art to mirror

[`tests/test_tasks_validate.py`](../../tests/test_tasks_validate.py) already builds a temporary repository
root, monkeypatches `tv.TASKS_DIR` and `tv.REPO_ROOT` in `setUp`, restores them in `tearDown`, and
captures stdout around `tv.main(["--strict"])`. Reuse that harness rather than inventing a second one.
Its module docstring notes the file covers only the `external` scenarios and does not pretend to be a
full suite; extend that framing honestly rather than overclaiming.

## Risks and rollback

The task touches more than one module (`.tasks/validate.py`, the `done/` ledger, and the test suite),
so the rule fires.

- **This reintroduces a rename cost that `chore-0012` deliberately removed for `touched_files`.** That
  fix stopped `--strict` from checking a completed task's `touched_files`, because those are a
  historical record of what the task changed and any later rename broke the backlog permanently. A link
  check over `done/` is exposed to the same failure: renaming `scripts/install.py` will now fail
  validation until the done files pointing at it are updated. **This is accepted on purpose, and the
  two cases are not the same.** A stale `touched_files` entry harms nobody; a broken link is a live
  navigational affordance that a reader clicks and gets nothing from. Paying a rename cost is worth it
  for the second and was not for the first. Do not resolve the tension by exempting `done/`, which
  would put the check back where it cannot see the 101 links this task exists to fix.
- **Editing 36 files in the ledger.** These are completed records, and the edits must stay confined to
  link hrefs and the six de-linkings. Changing any surrounding prose, status, or finding would rewrite
  history rather than repair a pointer. A reviewer should be able to read the diff and see only link
  syntax move.
- Rollback is reverting the one commit. No persisted format changes and no schema changes, so nothing
  needs cleaning up afterwards.
- **`feat-0035` is in flight on `feat/draft-review-depth` and carries 5 links that this check will
  reject once it merges.** That is the check working as designed, not a conflict, but whoever lands
  that branch should expect to fix its links at closeout rather than be surprised by a red build.

## Acceptance criteria (mechanically verifiable)

    python .tasks/validate.py --strict
    python -m unittest discover -s tests -p "test_*.py"

- [ ] A test writes a task file whose relative link resolves from `.tasks/` but not from `.tasks/done/`,
      places it in `done/`, and asserts validation fails naming the file and the target.
- [ ] A test asserts the same link in `.tasks/` passes, so the check is proven to be
      location-sensitive rather than merely strict.
- [ ] A test asserts an `http://`/`https://`/`mailto:` target and a `#fragment`-only target are skipped.
- [ ] Both failing tests are confirmed to fail against the pre-fix `validate.py`, not merely to pass
      after.
- [ ] `python .tasks/validate.py --strict` exits zero on a clean tree, and re-running the reproduction
      script over `.tasks/**/*.md` reports 0 broken links.
- [ ] All 101 links are repaired, with the 14 non-mechanical ones handled per the class table rather
      than by a blanket `../` prefix.
- [ ] No file under `.tasks/done/` has any change other than a link href or a de-linking.
- [ ] `.github/workflows/checks.yml` is left unchanged, with the reason stated.
- [ ] The `init-worktracking` template validator carries the same check, so a freshly scaffolded
      repository does not inherit the defect.
- [ ] The closeout step in `AGENTS.md`, `.tasks/README.md`, and the template README says to re-anchor
      the links.
- [ ] Existing tests still pass.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
