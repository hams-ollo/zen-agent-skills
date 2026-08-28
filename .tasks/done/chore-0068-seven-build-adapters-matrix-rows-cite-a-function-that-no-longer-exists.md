---
id: chore-0068
title: Seven build-adapters matrix rows cite emit_shared_assets, a function that no longer exists, and nothing reports it
type: chore
status: done
priority: P2
parent: "ROADMAP Epic A: broadly shareable (the public kit)"
depends_on: [chore-0062]
spec: "docs/spec/build-adapters.md"
scenarios: []
touched_files:
  - docs/spec/build-adapters.conformance.md
created: 2026-08-27
---

## Problem

Found by [`chore-0062`](chore-0062-the-build-adapters-contract-says-nothing-about-what-a-lens-may-link.md)
while amending the same contract, and correctly declined there because repairing a citation without
re-auditing the row asserts a freshness that pass had not established.

Seven rows in [`build-adapters.conformance.md`](../../docs/spec/build-adapters.conformance.md) cite
`emit_shared_assets()` as their evidence. That function was split into `emit_rules_module()` and
`emit_skill_assets()` and the cells were never repointed.

```text
grep -n "emit_shared_assets" scripts/build-adapters.py   ->  nothing
grep -n "^def emit_" scripts/build-adapters.py           ->  emit_rules_module, emit_skill_assets,
                                                             emit_cursor, emit_vscode, emit_plugin,
                                                             emit_plugin_manifests
```

**One row is stale twice over.** The `S-009` row's note reads "called per skill from `main()`", which
describes the call site as it was before `bug-0025`. `emit_rules_module()` is now called once per
distinct layout, not once per skill, so the note misdescribes the mechanism as well as naming the wrong
function.

This is the same class as `bug-0037`, which moved conformance citations off line numbers because a
pointer that encodes position drifts when anything above it moves. A pointer that encodes a **symbol**
drifts when the symbol is renamed, and nothing here notices either.

**Nothing reports it, and that is the second half of the problem.** No gate and no test resolves a
conformance matrix's cited evidence against the file it cites. That absence is
[`chore-0049`](chore-0049-a-checker-for-conformance-matrix-citations.md), and this task is one of the
two live instances that argue for it. The other arrived the same day, when `chore-0064` reworded a
summary line and silently invalidated quotes in two other matrices.

## Scope

**In scope:** re-audit the seven rows, and repoint their evidence.

- **Re-audit, do not find-and-replace.** Each row asserts a classification as well as a citation. The
  split may have moved behaviour between the two new functions, so confirm the row's verdict still holds
  before correcting where it points. A mechanical substitution would produce seven citations that resolve
  and seven verdicts nobody checked, which is a worse state than today because it looks audited.
- Correct the `S-009` note's "called per skill from `main()`" to the post-`bug-0025` call site.
- Record the re-audit's scope in the matrix the way `chore-0062` did: which rows were re-derived on this
  date and which were not, so a partial audit is never readable as a whole one.
- Update `re_audited` in the frontmatter only for what this pass actually re-derived.

**Out of scope:**

- `scripts/build-adapters.py` and `tests/test_build_adapters.py`. **If the re-audit finds a row whose
  verdict no longer holds, that is a finding to report and a separate task**, not a code change here.
- The other rows in the same matrix, unless the re-audit reaches them. Say which were not touched.
- Building the checker that would catch this class, which is `chore-0049`. This task supplies it evidence
  and does not pre-empt it.
- The contract itself. `chore-0062` amended it on 2026-08-27 and it is current.

## Implementation notes

Read `bug-0025`'s record before touching the `S-009` row, since it is what moved the call site, and the
note's error is about the mechanism rather than the name.

`chore-0062` left this deliberately and its `## Decisions` states why. Read that first: it also records
which rows that pass *did* re-derive, which is exactly the set this task must not claim credit for.

## Risks and rollback

One document, so this section is short.

The risk is the one the Scope names: a substitution dressed as an audit. The guard is to state, per row,
what was re-derived and against what, rather than reporting a count of citations fixed.

Reversible by reverting one commit. No contract changes, so no re-approval is affected.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [x] `grep -n "emit_shared_assets" docs/spec/build-adapters.conformance.md` returns nothing.
- [x] Every repointed row names the function that now holds its evidence, and the closeout states, per
      row, that its verdict was re-derived rather than assumed.
- [x] The `S-009` note describes the post-`bug-0025` call site.
- [x] The matrix states which rows this pass re-audited and which it did not, and `re_audited` reflects
      only the former.
- [x] The line-number citation grep over `docs/spec/*.conformance.md` still returns nothing.
- [x] No file under `scripts/` or `tests/` is modified.
- [x] Existing tests still pass, unchanged in intent.

## Decisions

- **Rejected: keeping the removed function's name in the matrix's own narrative.** Four occurrences
  survived the row edits, all describing the split rather than citing it. Satisfying the acceptance
  grep only inside the evidence cells would have left a dead symbol in the prose of the one document
  whose citations `chore-0049` is meant to check, so it is now written nowhere in the file, not even
  to describe its own removal. `bug-0025`'s record carries it, and the matrix says so.
- **Rejected: repointing the seven citations in the form they already had.** Four of them were
  renderings rather than quotes and did not resolve literally: `or dest.exists(): continue`,
  `dest.resolve() == src.resolve(): continue`, `if dry: return`, and
  `LAYOUTS["plugin"] = Layout("rules", "skills")` for a dict entry written `"plugin": Layout(...)`.
  Carrying the style forward would have shipped seven freshly re-audited rows whose evidence still
  read like source and was not. Every backticked expression in the seven rows now resolves verbatim
  against `build-adapters.py`, checked mechanically.
- **Premise extended: the task says one row is stale twice over, and two are.** The `S-009` note is
  the one it names, and that is correct. `S-012` is stale in a second way the function rename hid:
  its Then has two halves, "no file exists that the run would have written" and "the reported counts
  describe what would have been produced", and the row's evidence named only the first. The second
  half was false on this row's original audit date and was what `bug-0025` measured and fixed, so the
  row was carrying a `Conformed` that half of its scenario did not support until 2026-08-08. The
  verdict is correct today; the evidence now covers both halves.
- **Seam left open deliberately: three rows this pass did not audit carry the same rendering-style
  citations**, `SHARED/skills/<name>/<target>` in `S-007`, `any(start <= m.start() < end ...)` in
  `S-018`, and `for fname, obj in ...` in `S-015`. All three are signposted elisions rather than false
  quotes, and all three sit in rows outside this task's scope, so they were left alone. They are
  flagged because a literal-match checker of the kind `chore-0049` proposes would report all three,
  and it needs a rule for an elision marker before it is pointed at this file.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [x] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
