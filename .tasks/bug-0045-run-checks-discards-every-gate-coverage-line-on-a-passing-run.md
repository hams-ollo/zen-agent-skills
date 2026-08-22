---
id: bug-0045
title: The acceptance command prints one status word per gate and discards every coverage count, so a clean run and a run over nothing produce identical output
type: bug
status: open
priority: P2
parent: "ROADMAP Epic E #2: make this repository cloud-executable"
depends_on: []
spec: "docs/spec/cloud-executable.md"
scenarios: ["S-001", "S-002"]
touched_files:
  - scripts/run-checks.py
  - tests/test_run_checks.py
created: 2026-08-22
---

## Problem

Every gate in this repository emits a coverage count, and each one was put there deliberately, by a
task that had just been burned by its absence. `run-checks.py` throws all of them away on a passing
run.

The mechanism is three lines in `run_all()`:

```python
        suffix = "" if cleanup_ok else "  (cleanup did not complete)"
        out.write(f"{status:11} {gate.name}{suffix}\n")
        # A passing gate whose cleanup failed still needs its output shown, or the
        # leftover files are announced in one word and explained nowhere.
        if status != "ok" or not cleanup_ok:
            notes.append((gate.name, status, output))
```

`output` is captured for every gate and appended only when the gate did not pass. A passing gate is
reported as one word and a name.

The counts it discards were each written against a recorded incident, and the comments say so in
the gates' own words:

- `validate-skills.py`: the supporting-file counts are printed because "a coverage number nobody
  can compare across runs is the gap this rule closes rather than a report of it: '0 supporting
  files checked' reads identically whether the rule is working or the walk is broken, until the
  count of what it declined to read sits beside it."
- `tests/test_tasks_validate.py`, on the `--links` document count: "The count is load-bearing, not
  decoration: it is the only thing in the output that distinguishes a clean run from a run over an
  empty file set, and both print zero broken links."
- `.tasks/validate.py` prints `Checked N task files`; `install.py` prints the placed count and the
  per-profile description budget.

AGENTS.md declares `python scripts/run-checks.py` the acceptance command, so this is the shape in
which those counts are read, or would be. In the baseline run for this review, the whole output was
seven status words, a tally, and the platform line. Not one of the counts above appeared.

**What that hides, measured rather than argued.** Six of the seven gates exit 0 having examined
nothing. Probed directly against the real functions, each pointed at an empty directory:

```text
validate-skills.py over an empty skills dir   -> exit 0 | No skills found under <tmp>/skills.
install.py over an empty skills dir           -> exit 0 | No skills found under <tmp>/skills.
build-adapters.py over an empty skills dir    -> exit 0 | No skills found under <tmp>/skills.
.tasks/validate.py over an empty .tasks dir   -> exit 0 | Checked 0 task files: 0 error(s), 0 warning(s).
python -m unittest discover over an empty dir -> exit 0 | Ran 0 tests in 0.000s / OK
```

End to end, over a copy of this repository with `.agents/skills/`, `tests/`, and the `.tasks/`
task files emptied:

```text
ok          lint skills
ok          test suite
ok          backlog
ok          adapters dry run
ok          install dry run
ok          install cycle
failed      doc links
```

Six `ok` over a repository holding zero skills, zero tests, and zero task files. The seventh
noticed, and only incidentally: `doc links` failed because the documents still linked to what had
been deleted, not because it counted its inputs. That gate is the one that gets it right on
purpose, and the only one:
`test_patterns_that_match_no_document_fail_rather_than_pass_silently` in
`tests/test_tasks_validate.py` pins exactly this rule for `--links` and for nothing else.

The three gates that print `No skills found` are not being dishonest; they say what happened. The
defect is at the seam. The gate says it, and the aggregator that is now the only sanctioned way to
run it throws the sentence away.

This matters most for the reader the command was written for. `run-checks.py`'s own docstring says
an unattended agent "cannot push and wait for someone to read the result", so its report is the
whole record of what happened. A report that cannot distinguish seven gates passing from seven
gates declining to look is the same silent under-report class this repository has closed eight
times in its checkers, one level up, in the tool that reports on them.

## Scope

**In scope:** make a passing run carry each gate's own account of what it covered.

- Surface a coverage line per gate rather than the whole captured output. The full output of seven
  passing gates is long and would bury the tally; the last non-empty line of most of these gates is
  already the summary line, which is the cheap version and worth trying first.
- Whatever the shape, it must satisfy one property: a run over an empty tree must not be
  byte-identical to a run over the full one. Assert that property in a test rather than asserting
  the current strings, so the test survives a wording change in any gate.

**Out of scope:**

- Changing any gate's exit code so that zero inputs fail. That is six edits across five files and a
  policy decision about what each gate's minimum input is, and it belongs in its own task. The
  survey above is recorded here so whoever writes it does not have to redo it. Note that the
  `--links` half of that policy is already filed as
  [chore-0032](chore-0032-links-guard-fires-per-run-not-per-pattern.md).
- Adding an eighth gate. `run-checks.py`'s summary arithmetic is pinned by
  `tests/test_run_checks.py` and a count change is a separate deliberate edit.
- Parsing a gate's output for anything but display. The aggregator must not start deciding a
  verdict from text; the exit code stays the verdict.

The two scenarios this task declares are the nearest the contract has, and neither requires a
coverage line. `S-001` requires only that each gate "is named in the output with its own outcome",
and `S-002` requires a failing gate to be "named with its output", which is where the passing
case's silence comes from. Amending `docs/spec/cloud-executable.md` to state what a passing gate
must carry is a separate chore, in the shape of
[chore-0047](done/chore-0047-validate-skills-contract-lacks-the-lens-composition-rule.md). File it
at closeout.

## Implementation notes

`run_gate()` already returns the joined output for every gate, passing or not, so nothing new has
to be captured. The change is what `run_all()` does with it.

Resist per-gate special cases. A table mapping gate names to the regex that finds their coverage
line is a second source of truth that drifts the first time a gate rewords its summary, which is
the failure `chore-0029` recorded for a copied link rule. Prefer a rule that needs no per-gate
knowledge, such as the last non-blank line of the gate's output, and accept that it is imperfect
for a gate whose output ends elsewhere.

Two gates run more than one command. The `install cycle` gate runs `install.py` twice and then a
cleanup, so "the last line" there is the second install's line; decide whether that is the right
one to show and say why in the closeout rather than leaving it to be inferred.

## Risks and rollback

Required: this changes the format of the one report an unattended agent produces, and the format is
pinned by `tests/test_run_checks.py`, so an agent or a script reading the old shape is affected by
the change rather than by a bug in it.

The realistic failure is a report so long that the tally at the bottom stops being read, which
would be a worse outcome than the current terseness. Bound it by keeping the addition to one line
per gate and by checking the total length of a real passing run before committing.

Reversible by reverting one commit. Nothing is persisted and no other tool reads this output.

## Acceptance criteria (mechanically verifiable)

    python scripts/run-checks.py

- [ ] A test asserts that a passing run's output differs when a gate reports different coverage,
      using two injected gates whose outputs differ only in their count line.
- [ ] A test asserts the per-gate coverage line appears for a gate whose status is `ok`, which is
      the case the current code excludes.
- [ ] The failure and could-not-run branches still show the gate's full output, unchanged.
- [ ] A real `python scripts/run-checks.py` run is recorded verbatim in the closeout, so the new
      shape is on the record rather than described.
- [ ] Existing tests still pass, updated only where they pin the old format, and each such update
      named in the closeout.

## Definition of done

- [ ] Acceptance command(s) pass locally.
- [ ] Conventions in AGENTS.md's conventions section followed.
- [ ] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a reason.
- [ ] The `cloud-executable` conformance matrix updated over `S-004` and `S-005`, or the deferral recorded with what is owed.
- [ ] File moved to `.tasks/done/`, `status: done`; one dated line added to `CHANGELOG.md` referencing this task id.
