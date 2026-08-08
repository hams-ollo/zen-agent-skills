---
id: chore-0032
title: The --links empty-match guard fires per run, so one dead glob checks nothing and passes
type: chore
status: open
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [chore-0029]
touched_files:
  - .tasks/validate.py
  - .agents/skills/init-worktracking/templates/validate.py
  - tests/test_tasks_validate.py
  - .github/workflows/checks.yml
created: 2026-08-06
---

## Problem

`chore-0029` gave `--links` a guard against the failure its own risk section named as costliest: a
link check that passes instantly having checked nothing. The guard exits non-zero when the patterns
match no documents. **It fires only when every pattern matches nothing.**

CI calls it with three patterns. If one stops matching, the step passes on the strength of the
others, and the only signal is a document count nobody is comparing against anything:

```
python .tasks/validate.py --links "*.md" "docs/**/*.md" "totally-gone/**/*.md"
checked 37 documents, 0 broken link(s)     exit 0

python .tasks/validate.py --links "*.md" ".github/**/*.md"
checked 9 documents, 0 broken link(s)      exit 0
```

Measured 2026-08-06 during `chore-0029`'s verification. **Rename `docs/` and CI passes having checked
9 of 38 documents.** `docs/` holds 29 of the 38, so the great majority of the coverage disappears
while the step reports success.

**The workflow comment overstated this and has been corrected** to state the real bound, so nothing
in the tree currently claims a property the code does not have. The gap itself is still open, which
is what this task closes.

**This is the fourth instance of one failure shape in two waves**, which is the reason it is worth a
task rather than a shrug. A blank line deleted a provenance record (`bug-0016`); an unreadable file
deletes all of a file's records (`bug-0019`); a stray backtick could have disabled the link check
below it (`bug-0015`, guarded); and a dead glob drops 29 documents. Every one of them exits 0.

## Scope

**In scope:** make the guard per pattern, so a pattern matching nothing fails the run and names
itself, in [`.tasks/validate.py`](validate.py) and the
[template copy](../.agents/skills/init-worktracking/templates/validate.py); tests pinning the
one-of-three case; and whatever the workflow comment should say once the bound changes.

**Out of scope:**

- Which globs CI passes. That set is `chore-0029`'s and is deliberate.
- The disjoint coverage between `--strict` and `--links`, which is deliberate and load-bearing.
- Asserting an absolute document count in CI, which would fail on every legitimate addition and is
  the reason `chore-0018` and `chore-0019` moved to globs in the first place.
- `broken_links()` and `mislabelled_links()`, which are unaffected.

## Implementation notes

**A pattern legitimately matching nothing is the case to think about before writing the check.** In
this repository all three CI globs always match, but an adopter's scaffolded repository may have no
`.github/` at all, and the template ships this same code. A per-pattern failure that cannot be
relaxed would make the scaffold's own check unusable in a repo without CI. Either let a caller mark a
pattern optional, or have the scaffold pass only patterns it knows match, and say which in the
template's comment.

**Name the dead pattern in the message.** "No document matched" without saying which pattern died
sends the reader to check three globs by hand, and the whole value here is that the failure is
self-explaining.

**Keep the two copies in step**, the constraint `bug-0011`, `bug-0012`, `bug-0015`, `bug-0017`, and
`chore-0029` each honoured in turn. The executable code and module-level regexes stay identical; the
template's prose stays retargeted so it never names this repository.

## Risks and rollback

Required: this changes a required CI gate and what a shipped scaffold emits.

- **The failure that costs most is a gate that now fails for a legitimate reason**, for example an
  adopter with no `.github/` directory, because a gate that cries wolf gets deleted. Decide the
  optional-pattern story before implementing, not after, and cover the scaffold case in a test.
- Rollback is one revert of the guard plus the workflow comment; no persisted format changes.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python .tasks/validate.py --strict

- [ ] A test proving one pattern matching nothing, among several that match, exits non-zero. It must
      fail against the current implementation.
- [ ] The message names the pattern that matched nothing.
- [ ] A test proving the all-patterns-dead case still fails, so the existing guard is not lost.
- [ ] A test covering the scaffold case: a repository with no `.github/` runs the template's own
      check without a spurious failure, or the optional-pattern mechanism is exercised.
- [ ] `python .tasks/validate.py --links "*.md" ".github/**/*.md" "docs/**/*.md"` still reports 38
      documents and 0 broken links against this tree.
- [ ] The workflow comment describes the bound the code now has.
- [ ] The two validator copies remain identical in the executable code and module-level regexes.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason.
- [ ] File moved to `.tasks/done/`, `status: done`, **with its relative links re-anchored for the
      extra directory level**; one dated line added to `CHANGELOG.md` referencing this task id.
