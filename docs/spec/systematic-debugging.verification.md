---
title: systematic-debugging verification
spec: docs/spec/systematic-debugging.md
task: feat-0061
verdict: pass
verified: 2026-08-29
---

# systematic-debugging verification record

Independent verification of `feat-0061`, the build of
[`systematic-debugging`](../../.agents/skills/systematic-debugging/SKILL.md) against
[`systematic-debugging.md`](systematic-debugging.md).

**A ledger, not a current-state document.** It records what was observed on 2026-08-29 and is never
rewritten to match a later tree, per the rule in [`README.md`](README.md).

**Run by an agent that did not write the implementation**, which is the point rather than a
formality: rule A7 of the autonomy rules module says self-verification is the failure mode the
separation exists to remove, and this run is the argument for it. Every one of the author's own
fifteen mutations had been killed, and the verifier's first five all survived.

## Verdict

```text
verdict: pass
blocking_reasons: none

command: python scripts/run-checks.py
result (verbatim tail):
    8 passed, 0 failed, 0 could not run.
    Ran on Windows, Python 3.11.10. CI runs 3 operating systems x 2 Python versions, so this is
    one of six cells: passing here is necessary but not sufficient.
```

The command and its result are separate fields on purpose. Prose closes no gap between them.

All eight gates reported `ok`: skill lint over 22 skills, the test suite, backlog validation over
191 task files, the adapter and install dry runs, the real install cycle, the documentation link
check, and the conformance-matrix citation check.

## Acceptance criteria

Every criterion in `feat-0061` was met, each with named evidence. The two worth restating here are
the ones the verifier re-derived rather than read:

| Criterion | Met | Evidence the verifier produced itself |
|---|---|---|
| A provenance block records the fold-in with a re-fetchable raw URL and a sha256 of the retrieved bytes | yes | re-fetched independently with `urllib` and digested with `hashlib`: 9,465 bytes, `808fc5717aa88ad65efff312b11c186294d3e6ee301afb584e2f86599b137787`, an exact match to the recorded digest |
| `install.py --dry-run` proves the skill is placed by no profile, including `all` | yes | ran the installer over all three profiles; each prints `2 skill(s) marked a draft are excluded from every profile, including 'all': agent-observatory, systematic-debugging.` and exits 0 |

The verifier also read the upstream file and confirmed both recorded departures are real: upstream
carries an iron-law gate and a fourth phase that implements the fix, and this skill has neither.

## What the verification found, and what happened to it

Five findings, three major and two minor. **All five were reproduced here against the real tree
before being accepted**, on copies of the skill in a scratchpad with the tracked file never edited,
because a delegated report is a claim and not evidence. All five reproduced exactly as described, and
a sixth turned up while reproducing them.

| Finding | Severity | Disposition |
|---|---|---|
| The suite cannot detect a permission added beside an assertion, and `S-014` is the scenario most exposed. An escape hatch permitting in-place instrumentation with a restore before exit passed all 31 tests | major | fixed: `test_s014_no_sentence_permits_or_undoes_an_edit_to_the_tracked_files` |
| The matrix claimed a fourth verdict fails; a fourth instructed in Procedure step 6 left the `## Verdicts` table untouched and passed | major | fixed in both places: the matrix sentence now scopes its claim, and `test_no_fourth_verdict_is_instructed_anywhere_in_the_body` decides the stronger one |
| The spec index still said this matrix did not exist, and its stated arithmetic was stale | major | fixed in [`README.md`](README.md), and it went further than the finding: see below |
| The `S-012` matrix row quoted the contract's wording where its Evidence column cites the skill | minor | fixed: repointed to the skill's own words. Same class as `bug-0037` |
| Nothing asserted the one-variable-per-trial rule, a contract Constraint. Deleting the paragraph passed all 31 tests | minor | fixed: `test_the_one_variable_per_trial_rule_is_present_with_its_reason` |
| Found while reproducing the above: deleting Procedure step 1 entirely also passed all 31 tests | minor | fixed: `test_the_symptom_is_restated_as_an_observable_before_anything_is_run` |

The suite went from 31 tests to 35. All twenty mutations, the author's fifteen and the verifier's
five, now fail it.

**The finding behind the findings** is one shape rather than five defects. Every mutation the author
designed was a deletion or a replacement of asserted text, and a presence assertion cannot see an
**addition that contradicts it**. Four of the six survivors were additions or untouched regions; the
other two were paragraphs no assertion was scoped to. An author testing their own prose reaches for
the failures they were already thinking about.

**The per-sentence exclusion is worth reading.** The obvious fix for the escape hatch is to forbid
words like "restore" in that section, and it is wrong: the section legitimately uses "cleaning up
afterwards" in the sentence that rejects it, so a bare-word check would have been broken by the very
prose explaining the rule. This kit has three recorded occasions of exactly that. The assertion pairs
a permission or an undo with a mention of the tracked files **inside one sentence**, which the
rejecting prose never produces.

## One correction that went past the finding

The stale-index finding asked for the arithmetic to be updated. Recomputing it instead falsified a
figure the finding had accepted: the standing claim that `install`'s matrix "covers 15 of its 18
scenarios" does not survive a check, since that matrix cites 17 of the 18 scenario ids. So the
derived count of classified scenarios is **not stated** in `README.md` rather than restated at a new
wrong value, and the reason is written where the number was. `chore-0075` is the open task that would
compute these figures instead of maintaining them by hand, and this is the second figure it would
have caught.

## What this verification does not establish

Nothing here observed an agent following the procedure. Every assertion in the suite is structural,
over prose, and a skill body is instructions to a model: a test can decide an instruction is present
and cannot decide a model obeyed it. `feat-0062` is the task that closes that gap, by running the
skill on a real defect, and until it has run, the contract's central claim, that the procedure
produces the cause rather than decorating one arrived at some other way, is untested.
