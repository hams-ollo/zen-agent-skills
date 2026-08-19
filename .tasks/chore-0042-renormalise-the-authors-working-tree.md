---
id: chore-0042
title: Make the LF policy hold end to end, by pinning the kit's own text writers and renormalising the author's checkout
type: chore
status: open
priority: P2
parent: "ROADMAP Kit coherence hardening (2026-08-18 review pass)"
depends_on: []
touched_files:
  - scripts/build-adapters.py
  - scripts/install.py
created: 2026-08-18
---

## Problem

Split from [`chore-0041`](done/chore-0041-working-tree-crlf-against-the-eol-lf-policy.md), which
closed on the policy and documentation half. That run measured two things that change what is left.

**The repository is not the problem, one checkout is.** A fresh worktree reports `0` files at
`w/crlf`; the author's long-lived checkout reports `30`. A clone is clean, so there is nothing here
for CI to guard and nothing an adopter inherits.

**And `core.autocrlf=true` is not a stray repository setting.** `git config --show-origin` puts it at
**system** scope, `C:/Program Files/Git/etc/gitconfig`, the Git for Windows installer default, with
no repository value and no global value. `chore-0041`'s problem statement said repository scope,
read from bare `git config --get`, which reports the effective value and not its origin. So there is
nothing to unset, and `eol=lf` already overrides it on checkout.

What is genuinely left is smaller and in two parts.

**One machine needs a renormalise**, which is a single command producing no content change.

**And the kit's own two text writers can reintroduce the drift.** `_write` in
[`build-adapters.py`](../scripts/build-adapters.py) and the manifest write in
[`install.py`](../scripts/install.py) both call `Path.write_text(content, encoding="utf-8")` with no
`newline` argument, which emits CRLF on Windows. Neither output is tracked here, so nothing is broken
today, and that is exactly why it is worth pinning before something reads them: `install.py --check`
and `check-provenance.py` both compare digests of bytes read off disk, and a writer that varies its
line endings by platform is the shape that makes such a comparison answer differently on Windows
than on Linux. `CONTRIBUTING.md` already carries the `newline=""` rule as of `chore-0041`; the two
sites the rule names do not follow it.

## Scope

**In scope:**

- Pass `newline=""` at both `Path.write_text` sites so the kit's writers emit exactly the newlines in
  the string they were given.
- Renormalise the author's working tree with `git add --renormalize .`, as its own commit with no
  content change beside it, and confirm the index does not move.

**Out of scope:**

- A CI guard on the `w/crlf` count. A fresh clone is already `0`, so the gate would pass on every
  runner while proving nothing about the one machine that has the drift. `chore-0041` ruled this out
  and the measurement above is why.
- Changing `core.autocrlf` anywhere, at any scope. It is a system-level installer default that
  `eol=lf` already overrides, and asking contributors to change it would be asking them to fix a
  setting that is not causing the problem.
- `.gitattributes` and `CONTRIBUTING.md`, both settled by `chore-0041`.
- Hunting the tool that rewrote the thirty files. `chore-0041` established it is not in `scripts/`,
  so it is an editor or an agent harness, and no change in this repository can prevent it.

## Implementation notes

Do the renormalise **alone**, in its own commit, with a working tree that is otherwise clean.
Mixed with anything else it becomes unreviewable, since the whole point is that it changes no
content. Verify with `git diff --cached --ignore-all-space` returning empty before committing, and
with `git ls-files --eol | grep -c 'w/crlf'` returning `0` after.

The `newline=""` change is two lines and needs no test of its own: no tracked file is written by
either site, so a test would have to assert against generated output that is already regenerated on
every run. State that reasoning in the closeout rather than adding a test that pins a byte nobody
reads.

## Decisions

- **Rejected: a test for the two `newline=""` sites.** Confirmed rather than inherited: neither
  output is tracked. `scripts/.install-manifest.json` is in `.gitignore`, and nothing under
  `.cursor/`, `.github/prompts/`, `.claude-plugin/`, or `skills/` that `_write` emits is in
  `git ls-files`. A test would pin bytes that are regenerated on every run and read by nothing
  under version control. Verified empirically instead: emitting all three targets produced 96 text
  files, none containing CRLF, and the manifest written by the install cycle is LF-only.
- **Seam left open: the renormalise half is not done and is not forgotten.** It belongs to the
  author's long-lived checkout, which measured `30` files at `w/crlf`. A fresh worktree measures
  `0` before and after `python scripts/run-checks.py`, so running `git add --renormalize .` here
  would change nothing and prove nothing, while mixing line-ending churn into a two-line change.
  Acceptance criteria two through four stay unticked until that command runs on the machine that
  has the drift.
- **Seam left open: `build-adapters.py` copies `__pycache__` into its output.** Noticed while
  measuring the emitted bytes, unrelated to line endings, and left alone as out of scope. The
  `rglob` in `emit_skill_assets` walks the skill directory verbatim, so a checkout that has run the
  tests carries `.agents/skills/init-worktracking/templates/__pycache__/validate.cpython-311.pyc`
  into the emitted adapter tree. Gitignored here, but an adopter would receive compiled bytecode
  they did not ask for.

## Risks and rollback

Touches two scripts in different modules, so the more-than-one-module rule fires, though both edits
are one keyword argument.

The renormalise is the part that looks alarming and is not: it rewrites the working tree copies of
up to thirty files and, because `text=auto` already normalises on the way into the index, produces
no index change at all. If `git diff --cached --ignore-all-space` is not empty, stop, because that
means something other than line endings is in the staged set.

Reversible by reverting one commit. The renormalise is reversible by checking the files out again.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [ ] Both `Path.write_text` sites pass `newline=""`, verified by grep over `scripts/`.
- [ ] `git ls-files --eol | grep -c 'w/crlf'` returns `0` in the author's checkout.
- [ ] The renormalise commit shows no content change: `git diff --ignore-all-space` against its
      parent is empty.
- [ ] The count is still `0` after `python scripts/run-checks.py` has run.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
