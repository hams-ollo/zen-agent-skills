---
id: chore-0055
title: The template marker is matched case-sensitively while the markdown suffixes beside it are not, so a file can classify as neither
type: chore
status: open
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

`classify_supporting_file()` in [`validate-skills.py`](../scripts/validate-skills.py) decides a
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

- [ ] `AGENTS.md.TMPL` and `AGENTS.md.tmpl` classify the same way as each other, or both fail loudly,
      per the recorded decision.
- [ ] The chosen rule is pinned by a test covering both the template marker and the markdown suffixes,
      failing against the current code in at least one direction.
- [ ] No destination-bound file becomes link-checked as a result, proven rather than asserted.
- [ ] The validator's coverage line on the real tree still reports the same counts it does today,
      since no file in the kit is affected.
- [ ] The closeout states whether `S-024`'s wording still holds unchanged, checked rather than assumed.
- [ ] Existing tests still pass, unchanged in intent.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
