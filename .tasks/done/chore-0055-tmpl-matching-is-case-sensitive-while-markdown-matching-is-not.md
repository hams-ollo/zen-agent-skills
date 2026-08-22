---
id: chore-0055
title: The template marker is matched case-sensitively while the markdown suffixes beside it are not, so a file can classify as neither
type: chore
status: done
priority: P2
parent: "ROADMAP Kit mechanics hardening (2026-07-27 review pass)"
depends_on: [chore-0054]
spec: "docs/spec/validate-skills.md"
scenarios: ["S-024"]
touched_files:
  - scripts/validate-skills.py
  - tests/test_validate_skills.py
created: 2026-08-21
---

## Problem

`classify_supporting_file()` in [`validate-skills.py`](../../scripts/validate-skills.py) decides a
supporting file's kind with two adjacent tests that disagree about case:

```python
if path.name.endswith(TEMPLATE_SUFFIX):          # ".tmpl", case-SENSITIVE
    ...
if path.suffix.lower() in SUPPORTING_MARKDOWN_SUFFIXES:   # {".md", ".mdc"}, case-INSENSITIVE
```

So a file named `AGENTS.md.TMPL` classifies as neither `template` nor `markdown`. Probed directly on
2026-08-21:

```text
AGENTS.md.tmpl       -> template
AGENTS.md.TMPL       -> other
AGENTS.md.Tmpl       -> other
house-code-style.md  -> markdown
house-code-style.MD  -> markdown
```

**The direction is safe and that is why this is a chore rather than a bug.** A file that falls to
`other` is not read, so nothing destination-bound is ever link-checked against the wrong root, which
is the failure `S-024`'s exclusion exists to prevent. The observable cost is confined to the summary
line: such a file is counted among the non-markdown skipped rather than among the templates skipped,
so the coverage report misdescribes why it was left out.

Found by `chore-0054`'s agent while writing `S-024`, which recorded it as a stated bound in the
matrix row rather than fixing it, correctly, since `scripts/` was out of that task's scope. This is
that follow-up.

No file in the kit triggers it today: every template carries a lowercase `.tmpl`.

## Scope

**In scope:** make the two tests agree about case, and cover the disagreement.

- Decide **which way** they should agree, and record the rejected alternative. Case-insensitive
  matching for both is the obvious reading, but it is not the only defensible one: a case-sensitive
  rule for both would make `AGENTS.md.TMPL` a loud failure rather than a silent reclassification, and
  loudness is worth something in a check whose whole subject is files that get skipped.
- A test pinning whichever answer is chosen, for both suffix families, so the two cannot drift apart
  again silently.

**Out of scope:**

- The classification boundary itself. Which kinds exist, and that `.tmpl` marks destination-bound
  content, are `S-024`'s and are not reopened here.
- `docs/spec/validate-skills.md`. `S-024` describes the marker qualitatively and stays true under
  either answer, so this is a refinement rather than an amendment. **Confirm that against the scenario
  text rather than assuming it**, and if the contract does need a word, that is an amendment task and
  not this one.
- The summary line's wording, which is correct for what it counts.
- Renaming any file. Nothing in the kit is affected.

## Implementation notes

Read `S-024` before changing anything, and read `chore-0054`'s `## Decisions`, which records why the
bound was left rather than closed. That reasoning is the input to this task, not a thing to overturn
without saying so.

The nearby precedent is worth checking rather than guessing at: `install.py` and `build-adapters.py`
both make suffix decisions, and if either already settled the case question, agreeing with it is worth
more than picking independently. `bug-0028` established that character-identical helpers across these
tools are a deliberate seam, so a gratuitous third convention is the thing to avoid.

## Decisions

**Chosen: case-insensitive for both. Rejected: case-sensitive for both.** The two suffix tests in
`classify_supporting_file` now both match against a lowered name, so `AGENTS.md.TMPL`,
`AGENTS.md.Tmpl` and `AGENTS.md.tmpl` are one file kind, and `notes.MD` and `notes.md` stay one file
kind as they already were.

The rejected alternative was taken seriously and the argument for it does not survive being written
out. Its appeal, stated in `## Scope`, is loudness: a check whose whole subject is files that get
*skipped* should prefer a noisy failure to a silent reclassification. But case-sensitive-for-both is
not loud. Probed against the code, `AGENTS.md.TMPL` under a case-sensitive markdown test still has
suffix `.TMPL`, which is in neither family, so it classifies as `other` exactly as it does today: the
symptom this task was filed for would survive the fix that was supposed to make it loud. Worse, the
same rule silently *removes* coverage in the other family. A genuine read-in-place `notes.MD` would
stop being link-checked and would be counted among the non-markdown skipped, so its broken links go
unreported. That is a silent loss of checking, which is the failure mode S-024 exists to close rather
than one it tolerates. Loudness would have to be bought a third way, by making a case-variant suffix
an explicit error, and that is a new rule rather than an agreement between two existing ones, so it is
outside what this task scoped.

**The neighbours were checked and they do not settle it, which is worth saying plainly rather than
claiming a precedent that is not there.** Every filename decision in `install.py` and
`build-adapters.py` is case-sensitive: `_digestable` and `_copy` both test `suffix == ".pyc"` exactly,
and `SKILL.md` is matched as a literal. Neither is the same class of decision. A `.pyc` name is
written by CPython, which always writes it lowercase, so no author ever chooses its case; `SKILL.md`
is an exact filename Anthropic's schema mandates, and a directory missing it earns the S-001 or S-002
error, which is loud by construction. Both are machine-fixed names. The `.tmpl` marker and the
markdown suffixes are author-chosen suffixes on author-created files, and the only precedent in that
class is the line immediately below the one changed, `SUPPORTING_MARKDOWN_SUFFIXES` matched through
`.lower()`, which this kit already decided is case-insensitive. Agreeing with the adjacent line in the
same function is the least-invention answer available, and it is the one `bug-0028`'s
deliberate-seam rule points at: the third convention to avoid inventing here would have been a
file-suffix rule that disagrees with the file-suffix rule beside it.

**The bound is proven rather than asserted, and the proof is exhaustive rather than a measurement.**
No destination-bound file can become link-checked, and no checked file can stop being checked. The
marker test runs first, so widening it can only move a file out of the checked set; and it cannot move
one out either, because a name ending in `.tmpl` in any case has `.tmpl` as its `Path.suffix`, so it
can never also satisfy the markdown test. The only transition the change admits is `other` to
`template`, which is one skipped count into the other skipped count. Both ends are pinned by the two
end-to-end tests in `TestSupportingFileSuffixCase`.

**Effect on the two skipped counts on the real tree: none.** All eight shipped templates carry a
lowercase `.tmpl`, so the coverage line is byte-identical before and after: `Link-checked 1 supporting
file(s) beside them; skipped 8 template(s) whose links are written for another repository and 5
non-markdown file(s).`

**S-024's wording holds unchanged, checked against the scenario text rather than assumed.** The
scenario says the marker "is the `.tmpl` suffix on the file's name" and says nothing anywhere about
case. That sentence names a suffix by its spelling, which is how a suffix is ordinarily named, and it
reads true under either answer, so this is a refinement and not an amendment. `chore-0054` reached the
same reading when it recorded the disagreement as a bound inside the S-024 row rather than as an
amendment owed. No word of the spec was changed.

**Not done: retagging `TestSupportingFileLinkChecks` with `S-024`.** `chore-0054` left that open as
one follow-up of `chore-0045`'s shape covering three sets of tests, and this task changing one file
under `tests/` is not a reason to do a third of it. The four new tests sit in their own class,
`TestSupportingFileSuffixCase`, tagged `S-024`, so nothing new joins the untagged population.

## Risks and rollback

Two files in one module, so the more-than-one-module rule does not fire.

The only way this reaches beyond cosmetics is if the chosen answer makes a previously-skipped file
readable. Under case-insensitive matching a `.TMPL` file becomes a template and is still skipped, so
nothing new is read; under case-sensitive-for-both it becomes an error. Neither direction causes a
destination-bound file to be link-checked, which is the property worth protecting. State which
direction was taken and what it does to the two skipped counts.

Reversible by reverting one commit.

## Acceptance criteria (mechanically verifiable)

    python -m unittest discover -s tests -p "test_*.py" && python scripts/run-checks.py

- [x] `AGENTS.md.TMPL` and `AGENTS.md.tmpl` classify the same way as each other, or both fail loudly,
      per the recorded decision.
- [x] The chosen rule is pinned by a test covering both the template marker and the markdown suffixes,
      failing against the current code in at least one direction.
- [x] No destination-bound file becomes link-checked as a result, proven rather than asserted.
- [x] The validator's coverage line on the real tree still reports the same counts it does today,
      since no file in the kit is affected.
- [x] The closeout states whether `S-024`'s wording still holds unchanged, checked rather than assumed.
- [x] Existing tests still pass, unchanged in intent.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
