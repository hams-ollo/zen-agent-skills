---
id: bug-0013
title: The link checkers report every file:// link as broken, in all three copies
type: bug
status: done
priority: P1
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: []
touched_files:
  - .tasks/validate.py
  - .agents/skills/init-worktracking/templates/validate.py
  - .github/workflows/checks.yml
  - tests/test_tasks_validate.py
created: 2026-08-05
---

## Problem

The link checkers skip three URL schemes and resolve everything else as a repository-relative path:

    LINK_SKIP_PREFIXES = ("http://", "https://", "mailto:")

An absolute `file://` link is therefore treated as relative, joined onto the document's own
directory, and reported broken. Reproduced against [`validate.py`](../validate.py) on 2026-08-05:

    >>> broken_links(doc)   # doc contains two file:// links, one https, one mailto
    ['file:///d:/repo/src/models.py', 'file:///c:/other/README.md']

The `https://` and `mailto:` links in the same document were skipped correctly. There is nothing
wrong with either link: they name locations on a disk, which is not this checker's to resolve.

**Why this matters beyond a cosmetic false positive.** The checker ships to adopters. `.tasks/validate.py`
is scaffolded into every repository [`init-worktracking`](../../.agents/skills/init-worktracking/SKILL.md)
touches, via its template copy. An adopting repository whose documented house style uses absolute
`file:` links (a real convention, and the reason this was found) gets every such link reported broken
on the first run, with `--strict` promoting them to errors and failing the command. The validator is
unusable in exactly the repositories that already committed to the convention, and the only remedies
available to them are abandoning their house style or abandoning the validator.

Note this is not a rule the kit itself breaks: the swappable
[`house-style.md`](../../.agents/rules/house-style.md) module mandates *relative* links, which is why
the kit's own 33 documents pass. The defect is invisible from inside this repository and only fires
downstream, which is why it survived `bug-0011`'s link-checking work.

**Three copies, free to drift.** The same prefix tuple is duplicated:

| Copy | Line | Serves |
|---|---|---|
| [`.tasks/validate.py`](../validate.py) | 49 | this repository's backlog |
| [`.agents/skills/init-worktracking/templates/validate.py`](../../.agents/skills/init-worktracking/templates/validate.py) | 43 | every repository the skill scaffolds |
| [`.github/workflows/checks.yml`](../../.github/workflows/checks.yml) | 99 | the CI docs-link step |

Fixing one and not the others reproduces the defect for a different audience.

## Scope

**In scope:**

- Add `file://` to the skipped prefixes in all three copies, with a comment saying why it belongs
  there for a different reason than the other three: those are network schemes this checker has no
  business fetching, whereas this one is an absolute path outside the repository.
- Add a test to [`tests/test_tasks_validate.py`](../../tests/test_tasks_validate.py) proving a document
  containing only `file://` links passes.
- Keep the three copies in step, and note in each that the others exist.

**Out of scope:**

- Unifying the three copies into one shared module. That is a real and separate problem (`install.py`
  already carries a standing note about a third copy of its own frontmatter reader), and the template
  copy in particular *cannot* import from this repository, because it ships standalone into an
  adopter's tree. Solving duplication properly is a design task; do not attempt it inside a
  one-line-per-file bug fix.
- Validating that a `file://` target exists. It names a path on someone else's disk. Skipping is the
  correct behavior, not a shortcut.
- Changing [`house-style.md`](../../.agents/rules/house-style.md). The kit's own convention stays
  relative links; this fix is about not punishing adopters who chose otherwise.
- Any other prefix (`ftp://`, `vscode://`, custom schemes). Add them when one actually shows up.

## Implementation notes

A candidate patch already exists and was verified to work: four files, `+31/-3`, sitting in this
working copy's `stash@{0}` (message: `file:// link-skip fix for validators + CI + test`). It is
local-only and a stash is not durable, so treat it as a convenience rather than the source of truth.
The change it makes is small enough to restate:

- the two `validate.py` copies: `LINK_SKIP_PREFIXES = ("http://", "https://", "mailto:", "file://")`
- `checks.yml`: the same fourth element added to the inline `startswith((...))` tuple
- a new `test_a_file_scheme_link_is_skipped` in `RelativeLinkTests`

Match the prefix form to what a link actually carries. `file://` covers `file:///d:/x` and
`file://host/share`, which is every form the house style in question produces. A bare `file:`
without slashes is legal in the URI spec but is not what anyone writes in Markdown, so decide
deliberately whether to match it and say which you chose.

Mirror the existing comment style in these files: both copies explain *why* a rule exists rather
than what it does, and the surrounding comments in `validate.py` are unusually good about naming the
failure each rule prevents.

## Risks and rollback

The task touches more than one module (`.tasks/`, a shipped skill's template, and CI), so the rule
fires.

The risk is under-skipping in the opposite direction: a prefix match broad enough to swallow a
genuinely broken relative link that happens to begin with the same characters. `file://` is specific
enough that this is unlikely, but a bare `file:` would not be, which is the reason the form is called
out above as a deliberate decision.

Rollback is a single revert. Nothing persists state, and no other code reads these tuples.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" -v && python .tasks/validate.py --strict

- [x] A new test proves a document whose only links are `file://` passes with exit 0. `test_a_file_scheme_link_is_skipped`, and it was confirmed to **fail** against the pre-fix validator (`relative link does not resolve: file:///d:/some-repo/src/thing.py`) rather than assumed to prove something.
- [x] The test names the defect it protects against, per the test-quality convention used
      throughout `tests/`.
- [x] All three copies carry the prefix. **The grep half of this criterion was wrong and is recorded rather than quietly satisfied**: `mailto:` returns *five* non-test hits, not three. The other two are `scripts/validate-skills.py` and `scripts/build-adapters.py`, which carry a similar-looking tuple guarding a different rule, that a skill body's links may not escape the installed skill tree. An absolute link there is a portability defect `AGENTS.md` already forbids, so adding `file://` to those would weaken a real check rather than fix this one. Left unchanged deliberately, and a comment in both `validate.py` copies now says so, because the next person to run this grep will otherwise 'finish the job'.
- [x] The chosen matching form (`file://` versus bare `file:`) is stated in a comment. Two slashes, because that covers `file:///d:/x` and `file://host/share` (every form the house style produces) while a bare `file:` is short enough to swallow a genuinely broken relative link.
- [x] Existing tests still pass, and the CI docs-link step still reports 0 broken links over this
      repository's own documents. Suite 140 to 141.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents. **No finding.** The change is internal to three checkers; no reader-facing document describes which URL schemes they skip, and the kit's own house style still mandates relative links, which this does not alter. Original text:
      `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason. Updating `CHANGELOG.md` and the task file is not documenting the change: a feature only a maintainer can find out about has not shipped for anyone else.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
