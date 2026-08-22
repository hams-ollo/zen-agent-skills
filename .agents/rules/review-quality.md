# Zen review quality lens (edit freely)

This file is a **swappable module**, the house-review counterpart to
[`house-style.md`](house-style.md). It holds the rubric, severities, and protocol that the
`house-review` skill applies. It is separated from the skill so an adopter can retune the review bar
(or replace it with a team's own standard) without touching skill logic. Future quality-focused
skills (for example `test-author`, `security-audit`) can compose this same lens, or a sibling lens
next to it.

The pattern follows moonray's composable quality lens (`github.com/moonray/repoprompt-workflows`):
a lens is a reusable review "shot" a workflow composes, and findings are validated before they are
reported, then reconciled with the author. The evidence gate and the stable finding signature below
are taken from the Deep Review workflow in Balarama Bosch's same repository (MIT), as two mechanisms
rather than as the workflow around them.

## Severity scheme

Every finding gets exactly one severity:

- **blocker**: must be fixed before merge. A real bug, a security hole, data loss, a broken build
  or contract. If shipped, something is wrong.
- **major**: should be fixed. Not merge-blocking on its own, but a meaningful correctness,
  maintainability, or test gap that will bite later.
- **minor**: worth fixing. A smaller readability, structure, or consistency issue.
- **nit**: optional polish. Style or taste, take it or leave it. Label these clearly so they are
  never mistaken for must-fix.

## Rubric categories

Apply a category only where the diff actually warrants it. A one-line change gets a short review,
not a forced pass through all eight. In rough priority order:

1. **Correctness & bugs**: logic errors, edge cases, off-by-one, null/None handling, incorrect
   conditionals, race conditions, resource lifecycle, wrong assumptions about inputs.
2. **Security**: injection (SQL, shell, template), secrets in code or logs, missing authz/authn,
   unsafe deserialization, path traversal, unvalidated external input.
3. **Error handling & resilience**: swallowed or over-broad exceptions, missing validation,
   unchecked failure paths, leaked resources (files, connections, locks), silent data loss.
4. **Tests & coverage**: is the change covered? Missing tests for new logic, untested edge cases,
   tests that assert nothing, or a test changed to pass rather than to prove.
5. **Readability & maintainability**: naming, structure, dead code, duplicated logic, needless
   complexity, comments that explain "what" instead of "why".
6. **Performance**: obvious inefficiencies (N+1 queries, needless repeated work, accidental
   quadratic behavior). Only when it plausibly matters; do not speculate on micro-optimizations.
7. **API & interface design**: breaking changes to a public signature or contract, backward
   compatibility, error semantics, defaults, and whether the shape will age well.
8. **Docs & comments**: stale docs the change should have updated, missing rationale for
   non-obvious code, misleading comments.

## Evidence shape

A finding is a claim about code, so it carries the code. Every finding, at every severity, records
its evidence in one of the two forms below, and a candidate carrying neither is not reportable.

**Presence evidence**, for a defect in something that is there:

| Field | Content |
|---|---|
| `path` | Repository-relative path, forward slashes, no leading `./`. |
| `lines` | The single line, or the line range, the finding is about. |
| `symbol` | The enclosing function, class, or heading, where the file has one. Omitted where it does not. |
| `quote` | A verbatim excerpt of the cited lines, long enough to be unique within the file. |

**Absence evidence**, for a defect in something that is *not* there: a missing test, an unhandled
branch, an error path nothing covers. There is no offending code to quote, and the category that
suffers most from pretending otherwise is tests and coverage, which is made almost entirely of
absences. Requiring a quote of code that by definition does not exist would suppress that whole
category, so an absence finding quotes an **anchor** instead: the nearest code that would have to
change, or the sibling that shows what the missing thing would look like.

| Field | Content |
|---|---|
| `path`, `lines`, `symbol` | The anchor's location, not the missing thing's: the function whose branches are incomplete, or the test file where the missing test belongs. |
| `quote` | A verbatim excerpt of the anchor. |
| `absent` | One line naming what is not there. |
| `searched` | The search that established the absence, written so a reader can rerun it: the exact pattern, the scope, and what it returned. |

`searched` is what keeps an absence claim falsifiable. "There is no test for this" is an assertion.
"`git grep -n parse_frontmatter tests/` returns only `test_validate_skills.py:41`, which asserts on
the return value and never on the block-scalar branch" is evidence, and a reader who disagrees knows
exactly what to run.

## The evidence gate

Protocol rule 2 below says validate every finding before reporting it. The gate is that rule made
mechanical: **before a candidate becomes a reported finding, resolve its quote against the file
itself.**

Resolve against the revision under review, not against whatever happens to be in the working tree:
`git show <rev>:<path>` for a change review of a committed range, and the file on disk when the
changeset is the working tree or an explicit path scope. Checking a finding about a historical
commit against today's file drops correct findings and keeps stale ones.

Compare exactly, with two normalizations and no others: line endings (CRLF and LF are the same text)
and trailing whitespace. Indentation, spelling, and case are content, not formatting.

Then take exactly one branch:

| Result of resolving the quote | Disposition |
|---|---|
| Found at the cited lines | Report as written. |
| Found in the file at a different line | **Re-anchor and report.** Correct `lines` to where the text actually is, keep the finding, and say it was re-anchored. |
| Found more than once | Extend the quote until it is unique, then resolve again. If it cannot be made unique, cite the occurrence inside the changeset. |
| Not found anywhere in the file, or the path does not resolve | **Drop the finding.** |
| Absence evidence | Rerun `searched`. If it now returns something that covers the claim, drop the finding. If the anchor quote fails to resolve, drop it. Otherwise report. |

**Drift is a pointer problem, not a finding problem.** A quote found eight lines below where it was
cited means a refactor moved the code, not that the defect is imaginary, so re-anchoring is the
correct outcome and dropping would discard a real finding for a bookkeeping reason. This is not a
hypothetical: `verifier-agent`'s dogfood in this repository found a conformance matrix whose
classifications were correct and whose citations had every one of them drifted eight lines after a
refactor, and a human caught it rather than the process.

**A finding that fails the gate is dropped, not softened.** It is not reported at a lower severity,
not hedged, and not marked "possible". The gate is worth having only because a reader can then trust
every citation in the output, and one unresolvable finding carried through with a hedge spends that.

**Report the count of drops, not their content.** One line is enough: "2 candidate findings dropped
by the evidence gate." A reviewer whose candidates routinely fail to resolve is a reviewer to
distrust, and that is invisible if drops leave no trace at all. The dropped findings themselves stay
out, because restating them is exactly the unverifiable claim the gate just removed.

## Stable finding signature

Every reported finding carries a signature, so the same defect found twice is recognizably one
defect rather than two. Four fields joined by `|`:

    <severity>|<path>|<category>|<summary-slug>

- **severity**: the severity name, lowercase.
- **path**: the evidence `path`, repository-relative with forward slashes. For absence evidence, the
  anchor's path.
- **category**: the rubric category as a slug, one of `correctness`, `security`, `error-handling`,
  `tests`, `readability`, `performance`, `api`, `docs`. Slugs rather than the numbers 1 to 8,
  because `review-depth` already spends `R1` to `R7` on its selection rules and two unrelated
  numbering schemes in one review output is a trap worth not setting.
- **summary-slug**: the finding's one-line issue, lowercased, with every run of characters outside
  `a-z0-9` collapsed to a single `-`, trimmed, and cut to its first eight tokens.

Example: `major|scripts/install.py|tests|no-test-covers-the-symlink-fallback`.

**The line number is deliberately not in it.** A signature that moved when the code moved would
report one drifting defect as a new defect on every run, which is the same failure the re-anchor
rule fixes from the other end. A finding re-anchored from line 40 to line 48 keeps its signature,
and that is the property that makes signatures countable at all.

Signatures are emitted here, not consumed. Counting repeats across runs, and deciding when a
repeatedly reported finding is futile, are separate work and deliberately not defined by this lens.

## Review protocol

1. **Ground every finding in the actual diff.** Read the real changed lines and enough surrounding
   context to judge them. Do not review from the summary or the file names.
2. **Validate each finding before reporting it (govern/revalidate).** For every candidate finding,
   confirm it against the real code: does the problematic path actually exist, is the input really
   unchecked, is the test really missing? Drop anything you cannot substantiate. A confident
   false positive costs the author more trust than a missed nit costs you.
3. **Run the evidence gate over every candidate.** Give each one the evidence shape above, then
   resolve it as the gate directs: re-anchor a quote that moved, drop a quote that resolves nowhere,
   and rerun the stated search for an absence. Report how many candidates the gate dropped. Rule 2
   is the judgment; this is the check that the judgment was actually made.
4. **Order by severity**, blocker first. Within a severity, group by file.
5. **Make each finding actionable**: severity, `file:line`, the issue in one or two sentences, why
   it matters, its evidence quote, its signature, and a concrete suggested fix. Prefer a specific
   change over "consider improving".
6. **Report only.** State the findings and the suggested fixes. Do not edit or commit anything;
   reconciliation is the author's call. Changes are handled by the human, `/simplify`, or
   `fix-batch`.
7. **Say when it is clean.** If nothing substantive survives validation, say so plainly rather
   than manufacturing findings to look thorough.

## Scope

These are defaults, not laws. A skill may state a local exception, and a downstream adopter may
retune the severities, add or drop rubric categories, change the signature's field order, or replace
this lens entirely. One default is worth keeping whatever else changes: an adopter who relaxes the
gate into "report it with a note" gets back the failure mode it was written for, a review full of
confident citations that point at nothing. The point of
pulling it into its own file is that the override is a one-file edit, and no adopter inherits a
review bar they did not choose.

## Provenance

This lens draws on two upstream files rather than one, so it records two blocks. The composable
quality-lens pattern comes from the `review-quality` skill in Balarama Bosch's RepoPrompt Workflows
(MIT); the evidence gate and the stable finding signature come from the Deep Review workflow in the
same repository, taken as two mechanisms rather than as the workflow around them. Neither digest is
of this file, which differs from both by design. Re-check them by running
`scripts/check-provenance.py` in the Zen Agent Skills repository.

```provenance
source: https://raw.githubusercontent.com/moonray/repoprompt-workflows/main/.agents/skills/review-quality/SKILL.md
author: Balarama Bosch
license: MIT
retrieved: 2026-08-06
sha256: 5cf5a6e599f13e13b9b4ad8e93115d76c39310ff8d48b92c016a7a39c77be19b
note: source of the composable quality-lens pattern. Backfilled baseline (feat-0043); the snapshot adapted from is gone, so this pins upstream as of the retrieved date.
```

```provenance
source: https://raw.githubusercontent.com/moonray/repoprompt-workflows/main/.agents/workflows/Deep-Review.md
author: Balarama Bosch
license: MIT
retrieved: 2026-08-06
sha256: 77437e6e78fd10bde508be37aed1d4339c4572b9d58a9f0bb745a6f95f637795
note: source of the evidence gate and the stable finding signature. Backfilled baseline (feat-0043); the snapshot adapted from is gone, so this pins upstream as of the retrieved date.
```
