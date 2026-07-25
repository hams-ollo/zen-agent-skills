---
title: validate-skills verification
spec: docs/spec/validate-skills.md
task: .tasks/done/chore-0003-test-validate-skills.md
verified: 2026-07-24
verdict: pass
---

# validate-skills verification report

Independent verification of [`scripts/validate-skills.py`](../../scripts/validate-skills.py) against
its approved spec [`validate-skills.md`](validate-skills.md) and the acceptance criteria of
[`chore-0003`](../../.tasks/done/chore-0003-test-validate-skills.md). Produced as the first in-kit
dogfood of the `verifier-agent` skill. No file under verification was modified.

```text
verdict: pass

blocking_reasons: []

commands:
  - command: python -m unittest discover -s tests -p "test_*.py"
    exit_status: 0
    evidence: "Ran 11 tests in 0.018s / OK"
  - command: python scripts/validate-skills.py
    exit_status: 0
    evidence: "Checked 18 skill(s): 0 error(s), 0 warning(s)."

conformance:
  audited: S-001 through S-008 and all three Proposed Surface elements, per
    docs/spec/validate-skills.conformance.md
  unreconciled:
    - item: S-008 (description states what and when)
      status: Diverged
      disposition: accepted-with-reason
      note: The implementation length-proxies the "what and when" bar (len(desc) < 40) rather
        than checking it. Recorded as a deliberate, documented approximation; a full
        natural-language check is out of scope for a standard-library structural linter.

criteria:
  - criterion: tests/test_validate_skills.py exists and the acceptance command exits 0
    status: met
    evidence: command 1 exited 0 with 11 tests; tests/test_validate_skills.py present
  - criterion: Tests cover S-001 through S-007 with exact (errors, warnings, exit_code)
      assertions, not "does not crash" checks, using temp fixture directories
    status: met
    evidence: scenario tags S-001 through S-007 all present in tests/test_validate_skills.py;
      11 assertEqual calls and 0 assertTrue/assertIsNotNone weak oracles; tempfile used for
      fixture directories, no committed file mutated
  - criterion: main accepts an optional skills_dir, and the default invocation still prints
      the summary line and exits 0
    status: met
    evidence: scripts/validate-skills.py:57 `def main(skills_dir: Path = SKILLS_DIR) -> int`;
      command 2 printed "Checked 18 skill(s): 0 error(s), 0 warning(s)." and exited 0
  - criterion: validate-skills.py output is unchanged for the default invocation
    status: met
    evidence: observed output matches the format fixed by the spec's Proposed Surface,
      "Checked N skill(s): E error(s), W warning(s).", emitted at
      scripts/validate-skills.py:99-100

findings:
  - defect: Stale evidence citations in docs/spec/validate-skills.conformance.md. Every line
      reference pointing inside main() is off by +8 lines, because chore-0003 inserted the
      skills_dir parameter, the missing-directory guard, and the _rel helper above that code.
      The classifications remain correct; only the pointers drifted.
    where: docs/spec/validate-skills.conformance.md, matrix rows S-001, S-003, S-004, S-005,
      S-006, S-007, S-008 and all three Proposed Surface rows. The parse_frontmatter citations
      (S-002) are unaffected, since that function did not move.
```

## Notes on this verification

The finding above is the reason the conformance audit and the command run are separate inputs. Both
declared commands pass and every acceptance criterion is evidenced, so the implementation is sound
and the verdict is `pass`. But the artifact that carries the contract evidence has drifted out of
alignment with the code it cites, and neither the test suite nor a re-run of the original audit would
have surfaced that: the tests assert behavior, and a fresh audit would simply have written new line
numbers without noticing the old ones had rotted.

Per the skill's contract the drift is reported, not repaired. Correcting the citations is a separate
change to a separate file, and a verifier that edits its own evidence is no longer independent.

Line-number evidence is inherently fragile. A more durable citation form (`file:symbol`, which
`spec-conformance` already permits) would not have drifted here, which is worth considering the next
time a conformance matrix is produced.
