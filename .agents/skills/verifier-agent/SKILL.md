---
name: verifier-agent
description: Use before reconciling or landing an implementation to independently verify it against its approved spec and its task's acceptance criteria. Runs the declared verification commands and records each exact outcome, composes the spec-conformance lens so a contract divergence fails the run even when every command passes, maps each acceptance criterion to met or unmet with named evidence, and returns a deterministic pass, fail, or blocked verdict. Returns blocked rather than guessing when the spec is unapproved or no command is declared, so a verification that could not run is never recorded as a pass. Distinct from spec-conformance (the report-only lens it composes), test-author (which writes tests), code-review (which judges quality), and fix-batch (which dispatches the work). It verifies and reports; it never edits what it verifies.
---

# verifier-agent

Turn "it works" into a record. This is the independent verification stage of the contract-driven
spine: it runs immediately before [`reconcile-worktrees`](../reconcile-worktrees/SKILL.md), and its
verdict is what the decision to land should rest on.

Three signals already exist separately and none of them answers the landing question alone. A
command result proves the suite runs but not that the behavior matches the contract.
[`spec-conformance`](../spec-conformance/SKILL.md) audits code against a spec but is explicitly
independent of test pass/fail, so a clean matrix says nothing about whether anything was executed. A
task's acceptance criteria state what done means but nothing records that they were checked.
`verifier-agent` combines all three into one deterministic verdict with the evidence attached.

It composes [`spec-conformance`](../spec-conformance/SKILL.md) by reference for the contract half and
does not restate or re-derive its matrix. It formalizes the verification pass that
[`fix-batch`](../fix-batch/SKILL.md) requires but leaves to the agent running it, so depth and
evidence stop varying between runs.

**Independence is the point.** Where the harness allows the separation, the agent that verifies
should not be the agent that wrote the implementation. Self-verification is the failure mode this
skill exists to remove.

## When to use

- An implementation is finished and about to be reconciled, merged, or handed back as done.
- A worktree agent reports success and that claim needs independent evidence before it is trusted.
- A task's acceptance criteria need to be checked against what the code and commands actually do.

## When not to use

- You only need the spec-vs-code audit by inspection, with no commands run and no verdict: use
  [`spec-conformance`](../spec-conformance/SKILL.md) directly.
- You need tests to exist before anything can be verified: use [`test-author`](../test-author/SKILL.md) first.
- You want an opinion on code quality, design, or style: use [`code-review`](../code-review/SKILL.md).
- You are deciding whether a spec plus its plan are ready to implement: that is
  [`spec-plan-readiness`](../spec-plan-readiness/SKILL.md), which gates the front of the spine, not the back.

## Inputs

Required:

- **Task acceptance criteria**: the mechanical criteria the implementation must satisfy.
- **Declared verification command**: at least one, taken from the task's acceptance criteria or the
  repository's documented command. You never invent one.

Optional:

- **Approved spec path**: the contract to audit against. Without it, conformance is not assessed.
- **Report destination**: where to persist the report. Without it, the report is returned inline and
  no file is written.

## Procedure

### 1. Establish that verification can run at all

Before verifying anything, check the two preconditions that produce `blocked`. This step exists so an
unrunnable verification is never dressed up as a result.

- **Is the contract approved?** If a spec is supplied and its `status` is not `approved`, stop and
  return `blocked`. A draft spec is not a contract: it is one a human has not yet agreed to, and
  verifying against it would launder an unapproved contract into evidence. If no spec is supplied at
  all, that is not a blocker; continue, and record that conformance was not assessed.
- **Is there a command to run?** If no verification command is declared, or a declared command's
  runner is absent from the environment, stop and return `blocked` naming what is missing. Do not
  substitute a command you think is equivalent, relax one that fails to launch, or fall back to
  reading the code and calling that verification.

`blocked` is a real outcome that says the question could not be answered. It is never a soft `fail`,
and it is never a reason to guess.

### 2. Run the declared commands and record what happened

Run each declared command exactly as declared, in the intended scope. Record for each: the command as
written, its exit status, and the excerpt of its output that is the actual evidence (the failing
assertion, the error, the summary line), not the whole log.

Report what the command did, not what it should have done. If a command fails for an environmental
reason rather than a defect, say so in the evidence and keep the failure visible: do not re-run it
with different flags until it passes, and do not quietly exclude a failing case from the run.

### 3. Compose spec-conformance for the contract half

When a spec is supplied, apply the [`spec-conformance`](../spec-conformance/SKILL.md) lens to obtain
the conformance matrix and its coverage proof. Use its result; do not re-derive its classifications
here.

When you are consuming a conformance report that already exists rather than running the lens fresh,
first confirm its evidence still resolves against the current code. A matrix written before a later
refactor can carry correct classifications on stale pointers, and line references rot fastest. Spot
check that each cited location still contains what the matrix says it does. If the evidence has
drifted, the report is a finding: say which citations no longer resolve and whether the
classifications still hold. Do not silently re-point them, and do not treat a stale artifact as
fresh evidence.

What matters for the verdict is the `unreconciled` set and the disposition already recorded against
each item:

- an item marked **to-fix** is a live divergence and withholds a passing verdict, even when every
  command passed;
- an item marked **accepted-with-reason** does not fail the run, and must still be listed in the
  report with its recorded reason so the exception stays visible rather than silent.

You report the disposition the audit recorded. You do not renegotiate it, promote a to-fix item to
accepted because the fix looks tedious, or accept a divergence on your own authority.

### 4. Check every acceptance criterion against named evidence

Take each acceptance criterion in turn and mark it `met` or `unmet`, with evidence naming a command
result, a code location, or a test. A criterion is `met` only when you can point at what proves it.

When nothing demonstrates a criterion, mark it `unmet` and state that no evidence was found. Do not
infer satisfaction from a green suite, from an adjacent criterion, or from the implementer's own
report. An unevidenced criterion is a gap in the verification, and saying so is the useful result.

### 5. Return the verdict, and change nothing

Compute the verdict by the deterministic rule below, and return the report. By default the report is
returned inline and no file is created; write it to disk only when a report destination was supplied.

Verification is read-only. The implementation, its tests, and its spec must be byte-for-byte
unchanged when you finish. This holds even when the fix is one line and obvious: a defect you find
goes in `findings`, and a verifier that repairs what it verifies has destroyed the independence that
made its verdict worth anything.

## Output format

Return fields in this order:

```text
verdict: pass | fail | blocked
blocking_reasons:
  - reason: ...
    detail: ...
commands:
  - command: ...
    exit_status: ...
    evidence: ...
conformance:
  audited: ...
  unreconciled:
    - item: ...
      status: Diverged | Not-built
      disposition: fix | accepted-with-reason
      note: ...
criteria:
  - criterion: ...
    status: met | unmet
    evidence: ...
findings:
  - defect: ...
    where: ...
```

Rules:

- `verdict: pass` only when every declared command succeeded, every criterion is `met`, and every
  unreconciled conformance item is `accepted-with-reason`.
- `verdict: fail` when any command failed, any criterion is `unmet`, or any unreconciled item is
  dispositioned `fix`.
- `verdict: blocked` when a supplied spec is not `approved`, or no command is declared or runnable.
  A blocked run reports no pass or fail for the work itself.
- `blocking_reasons` is non-empty exactly when the verdict is not `pass`.
- `conformance` reads `not assessed: no spec supplied` when no spec was given, and is never inferred
  from test results.
- `findings` holds defects observed but not repaired, and never becomes a list of changes made.

## Notes

- The three verdicts answer three different questions: `pass` means the evidence supports landing,
  `fail` means it does not, and `blocked` means the question could not be answered. Collapsing
  `blocked` into either of the others is the most damaging thing this skill can do, because it turns
  an absent verification into a confident one.
- Stable scenario ids are what let this skill line up with the rest of the spine:
  [`test-author`](../test-author/SKILL.md) tags each test with the `S-NNN` it covers and
  [`spec-conformance`](../spec-conformance/SKILL.md) audits those same ids, so criteria, tests, and
  conformance rows can be read against each other.
- A passing verdict is a statement about evidence, not about quality. It does not mean the code is
  well designed; that is [`code-review`](../code-review/SKILL.md).

## Conventions

Follow the repo's house-style module (in this kit, [`.agents/rules/house-style.md`](../../rules/house-style.md)):
sentence-case headings, clickable relative links, named sources, no em-dashes. That file is a
swappable default; a downstream adopter may replace it without touching this skill.
