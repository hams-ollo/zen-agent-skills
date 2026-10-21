---
id: bug-0065
title: The observatory's copy-command builds its text with String.replace, so a dollar-sign escape in a recorded working directory silently yields a wrong path
type: bug
status: done
priority: P2
parent: "ROADMAP Epic E #7b: reporting"
spec: "docs/spec/agent-observatory.md"
scenarios: ["S-019"]
touched_files:
  - scripts/observatory/ui/index.html
  - tests/test_observatory_serve.py
depends_on: []
created: 2026-09-01
---

## Problem

`actionControl` in [`index.html`](../../scripts/observatory/ui/index.html) builds a `copy-command`
action's text like this:

```js
  var text = action.template.replace("{" + action.field + "}", value);
```

`value` is the **replacement** argument, so ECMA-262's `GetSubstitution` interprets a dollar-sign
escape inside it rather than inserting it literally. `value` is `row[action.field]`, and the
`copy-cwd` action's `field` is `cwd`, a working directory the corpus recorded and this repository did
not write. Both characters in the shortest such escape are legal in a path on every platform this kit
targets.

Measured 2026-09-01, with the escape written into a path and the backslashes elided by the shell:

```text
template : {cwd}
value    : D:work$&stuff
result   : D:work{cwd}stuff
expected : D:work$&stuff
```

The impact is bounded and is worth stating rather than inflating. The observatory is maintainer
tooling that `install.py` never places. The output reaches the page as a text node rather than as
markup, so this is not the `bug-0055` class and nothing is executed. The other two actions are safe
today: `copy-resume` takes a session UUID, and `open-pr` takes the `navigate` branch and never reaches
this line.

What it does is hand the viewer a silently wrong path, from the one control whose entire job is
handing them a correct one. There is no signal: the button reports `Copied`, and the text on the
clipboard is wrong in a way the viewer only discovers when the path fails to resolve somewhere else.

**Not covered, and structurally so.** The suite reads this file as text by design. A test asserts
`node_modules` is never introduced, and `followable_url`'s docstring gives that as the reason the
scheme check lives in Python rather than on the page:

```text
$ grep -n "no JavaScript runtime" scripts/observatory/serve.py
459:    suite deliberately has no JavaScript runtime (a test asserts `node_modules` is never
```

So no test here can execute this line, and this defect sits in the blind spot the conventions section
of [`AGENTS.md`](../../AGENTS.md) names: a mechanical gate that cannot see a class of defect reports
nothing about it.

Found by the 2026-09-01 review, recorded as finding 3 in
[`docs/reviews/2026-09-01-optimization-and-gap-review.md`](../../docs/reviews/2026-09-01-optimization-and-gap-review.md).

## Scope

**In scope:** replacing the substitution so a recorded value is inserted literally, and a test that
pins the construction within the suite's no-runtime bound.

**Out of scope:**

- Introducing a JavaScript runtime, a test harness, or `node_modules` to test this behaviorally. The
  absence is a contract property (`S-022` forbids fetching a subresource, and the no-runtime rule is
  asserted by an existing test), and trading it away to test one line is the wrong trade.
- The `navigate` branch and `followable_url`. Those are correct and were re-checked in the same pass.
- Widening `ACTIONS` or `ACTION_KINDS`. `S-019` is an enumeration claim and this task must not touch
  the enumeration.
- Escaping or sanitising the value for display. It is already a text node; the defect is the
  substitution, not the sink.

## Implementation notes

Two correct forms, either acceptable:

```js
  var text = action.template.split("{" + action.field + "}").join(value);
```

or a function replacer, which is exempt from `GetSubstitution`:

```js
  var text = action.template.replace("{" + action.field + "}", function () { return value; });
```

Prefer the first: it is the shorter statement of the intent, which is a literal token substitution
with no pattern language involved, and it needs no comment explaining why a function is being passed.

Whichever is chosen, leave a short comment naming the reason, in the voice the surrounding comments
use. This line looks obviously correct, which is exactly why it survived two prior reviews of this
file, and the next author to tidy it back to `replace` should be told what they are undoing.

**The test has to respect the no-runtime bound and say so.** It asserts on the construction, reading
`index.html` as text the way the neighbouring tests already do: that the token substitution in
`actionControl` is not `String.prototype.replace` with a data value as the replacement argument. Write
the bound into the test's own docstring, so a later reader does not mistake a source assertion for a
behavioral one and trust it further than it goes. The neighbouring assertions in
`tests/test_observatory_serve.py` that read `UI_INDEX` are the pattern to mirror.

## Decisions

- **A JavaScript runtime was considered and rejected.** Testing this behaviorally needs one, and the
  suite's freedom from one is a contract property with its own passing test. A source-level assertion
  that states its own bound is the honest trade; a runtime added for one line is not.

## Acceptance criteria (mechanically verifiable)

    python -m unittest tests.test_observatory_serve -v

- [x] `actionControl` no longer passes a corpus-derived value as the replacement argument of
      `String.prototype.replace`.
- [x] A new test reads `index.html` and fails against the current construction, passes against the
      fixed one, and states in its own docstring that it asserts construction rather than behavior and
      why.
- [x] The comment beside the fixed line names the reason, so the change is not tidied back.
- [x] `ACTIONS` and `ACTION_KINDS` in `serve.py` are unchanged, and the existing `S-019` enumeration
      tests pass unmodified.
- [x] `python scripts/run-checks.py` exits 0.

## Definition of done

- [x] Acceptance command(s) pass locally.
- [x] Conventions in AGENTS.md's conventions section followed.
- [x] `doc-sync` run over the reader-facing documents and its findings applied or dismissed with a
      reason.
- [x] `docs/spec/agent-observatory.conformance.md` brought up to date for `S-019`, or the deferral
      recorded with what is owed.
- [x] File moved to `.tasks/done/`, `status: done`, with its relative links re-anchored for the extra
      directory level; one dated line added to `CHANGELOG.md` referencing this task id.
