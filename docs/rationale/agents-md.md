# AGENTS.md: rationale and history

The reasons and incidents behind rules in [`AGENTS.md`](../../AGENTS.md), moved here verbatim on
2026-10-20 by the kit refresh ([audit](../reviews/2026-10-kit-refresh-audit.md), finding 6.2).
`CLAUDE.md` now imports `AGENTS.md`, so every Claude Code session in this repository loads it at
launch, and about 30 percent of its words were history rather than rule. Each rule in `AGENTS.md`
still stands where it was; this file keeps the evidence for it. Nothing below was reworded; only
relative links were re-pointed so they resolve from here.

## Why some scripts are not distribution scripts

Recorded 2026-08-28 by `chore-0076`, which needed a local store and a local server for [`docs/spec/agent-observatory.md`](../../docs/spec/agent-observatory.md); the sentence above had read as though every script were a distribution script, and five documents said so in five different scopes.

## Why the closeout list has its re-anchor, `doc-sync`, and conformance steps

The re-anchoring clause is in that list because the move silently invalidates every link in the file: a task authored in `.tasks/` correctly links to `../scripts/x.py`, and from `.tasks/done/` that same text means `.tasks/scripts/x.py`. `bug-0011` found 101 links across 36 completed tasks broken exactly this way, with `validate.py --strict` and the CI docs link step both passing, because neither looked here. `validate.py` now checks every link against the directory the file is actually in, so the move fails loudly.

The `doc-sync` step is in that list because its absence has cost real work. `feat-0031` shipped a user-facing feature that was dogfooded, given a conformance matrix and a verification record, and left every reader-facing document with zero mention of it. Updating `CHANGELOG.md` and the task file is bookkeeping, not documentation: a feature only a maintainer can find out about has not shipped for anyone else.

`cloud-executable` is the incident: approved 2026-08-07, with `feat-0045` and `feat-0046` both closed against it, it reached 2026-08-19 as the only approved spec of eleven with no matrix at all, having passed every stated obligation at both closeouts because no stated obligation mentioned the contract.

## How the lens-shape rule came to be enforced

The enforcement is new because the list was wrong, and how wrong is worth keeping. Until
`chore-0069` this rule named three lenses and was right about one: `spec-quality` carried the shape,
`test-quality` did not, and `review-quality.md` was never in this section's scope at all, since this
section opens by saying what a skill *directory* contains and that file is a rules module under
`.agents/rules/`, governed by the layout table above and the lens rules below. Two skills the rule
never named were shaped exactly as it prescribed, `spec-conformance` and `spec-plan-readiness`, and
the second of those calls itself a gate rather than a lens, so nothing classifies it either way.
Measured again on 2026-08-31: three skills declare themselves lenses (`spec-conformance`,
`spec-quality`, `test-quality`), and one of the three is reported.

That one report is `test-quality`, and it is left standing rather than cleared. Its headings are a
rubric (`Goal`, `Core rules`, `Review checklist`, `Commit gate`, `Reporting`), so the shape rule's
letter is broken there and its stated harm is not: it carries no procedure for an agent to run.
Which way that settles, reshaping the skill or rewording its declaration, is a change to the skill
rather than to this file, and renaming its headings to clear the warning would be satisfying the
validator instead of the rule.

## How the universal-lens rule came to be enforced

The enforcement is new and the reason is worth keeping. This rule existed here in prose and nothing
checked it, so its two halves had drifted a long way apart without either being visible: on
2026-08-29 `house-style.md` was referenced by all twenty-two skills, which is discipline rather than
a guarantee, and `autonomy.md` by five, for the twenty-one days since `A10`, the kit's only rule
about material an agent did not author, was added to it. Every gate passed throughout, because the
only lens rule in the validator asked whether **at least one** skill pointed at a module and one
always did (`feat-0064`).

## What the gates cannot see, by incident

**The other insufficiency is the one more runs do not close.** The paragraph above is about coverage
across the CI matrix, which a second platform closes. This one does not: every gate here decides a
mechanical property, and the defects below all sat outside what any of them sees. `bug-0045` emptied
`.agents/skills/`, `tests/`, and the `.tasks/` task files and reran this command; six of seven gates
reported `ok` over a repository holding nothing. `bug-0044` found seven links that resolve here and
dangle in every `cursor` and `vscode` tree the adapter builder ships, having "survived every gate".
`bug-0037` found three of sixty-five citations in a conformance matrix pointing at something other
than what they claimed, and why nothing could report it: the tests match on content and the link
check resolves paths, so neither sees a line anchor. The gates are healthy and catch what they were
built to catch; the claim is about what they cannot see, so read a green run as evidence about the
mechanical layer and nothing else. Buy the rest by hand, cheapest first: **construct the empty or
degenerate input and see what the tool actually says**, as `bug-0045` did by emptying the tree and
`bug-0046` did by renaming one `.md` to `.MD`, which carried two of eight provenance records out of
the run at exit 0. A check that cannot fail is unchecked, whatever it printed.

## Why the one hook registration is committed

The reason is mechanical rather than a preference. A user-level `~/.claude/settings.json` does not reach a cloud session, and a cloud session is the exact case this hook exists for: it clones the repository, gets none of the user-scope skills this kit installs, and would otherwise work without them and never say so. Verified against Anthropic's Claude Code documentation on 2026-08-07, which states the same thing from the other side by telling readers to commit settings files to change a cloud session's settings. A printed registration cannot be pasted by a machine that nobody is watching.

## Why the hook interpreter is a fallback (`bug-0050`)

The fallback replaced a one-sided `python3`, and the correction is worth recording because the reasoning was sound and the conclusion was wrong (`bug-0050`). `python3` was chosen as the portable default for the cloud sessions this exception exists for, with the Windows hazard known and stated: there `python3` is the Microsoft Store alias, a stub that advertises an install and exits without running anything. Both halves were true. What was wrong was the sentence joining them, that a static JSON file cannot probe and so cannot be right on both platforms at once. **It does not need to probe.** The cost of believing it was counted rather than estimated: the observatory's health report found this hook had exited non-zero on every session start in this checkout from 2026-08-07 to 2026-08-29, fourteen distinct failures, silent throughout, because a reminder must exit cleanly whatever happens. The one hook this repository commits, for the one argument that justified committing it, had never run.

## Why commits carry no co-author trailer

The reason is mechanical rather than stylistic. The `main protection` ruleset sets
`require_extra_approval_for_unattributed_changes`, so a commit trailer naming an identity with no
GitHub account marks the change unattributed and demands an extra approving review. The only human
here is also the author of every pull request, and **GitHub does not let a pull request author approve
their own pull request**, so the requirement cannot be satisfied as configured. On 2026-08-21 that
deadlocked the `developer` to `main` sync, 68 commits of which 44 carried the trailer, and it took an
admin bypass to land. The bypass stays available to the repository owner and the rule stays enforced
for everyone else; dropping the trailer is what keeps the rule from firing on work that is not
actually unattributed.

## Why the provenance convention exists

A meaningful share of this kit was adapted from somewhere else, and prose credit alone decays into folklore. `ROADMAP.md` once credited `doc-sync` to an upstream `document` workflow that was never vendored here, and the only surviving trace of the real contract was one line inside a gitignored folder that no longer exists. The attribution went wrong in under two weeks, and nothing could check it.

## Why the provenance check does not sync

Upstream's own `sync-maintainability-review.mjs` rewrites its vendored region in place, which is correct for verbatim vendoring and wrong here, because every fold-in in this kit was house-styled and retargeted and an overwrite would destroy the adaptation.
