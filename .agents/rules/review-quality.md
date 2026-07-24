# Zen review quality lens (edit freely)

This file is a **swappable module**, the code-review counterpart to
[`house-style.md`](house-style.md). It holds the rubric, severities, and protocol that the
[`code-review`](../skills/code-review/SKILL.md) skill applies. It is separated from the skill so
an adopter can retune the review bar (or replace it with a team's own standard) without touching
skill logic. Future quality-focused skills (for example `test-author`, `security-audit`) can
compose this same lens, or a sibling lens next to it.

The pattern follows moonray's composable quality lens (`github.com/moonray/repoprompt-workflows`):
a lens is a reusable review "shot" a workflow composes, and findings are validated before they are
reported, then reconciled with the author.

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

## Review protocol

1. **Ground every finding in the actual diff.** Read the real changed lines and enough surrounding
   context to judge them. Do not review from the summary or the file names.
2. **Validate each finding before reporting it (govern/revalidate).** For every candidate finding,
   confirm it against the real code: does the problematic path actually exist, is the input really
   unchecked, is the test really missing? Drop anything you cannot substantiate. A confident
   false positive costs the author more trust than a missed nit costs you.
3. **Order by severity**, blocker first. Within a severity, group by file.
4. **Make each finding actionable**: severity, `file:line`, the issue in one or two sentences, why
   it matters, and a concrete suggested fix. Prefer a specific change over "consider improving".
5. **Report only.** State the findings and the suggested fixes. Do not edit or commit anything;
   reconciliation is the author's call. Changes are handled by the human, `/simplify`, or
   `fix-batch`.
6. **Say when it is clean.** If nothing substantive survives validation, say so plainly rather
   than manufacturing findings to look thorough.

## Scope

These are defaults, not laws. A skill may state a local exception, and a downstream adopter may
retune the severities, add or drop rubric categories, or replace this lens entirely. The point of
pulling it into its own file is that the override is a one-file edit, and no adopter inherits a
review bar they did not choose.
