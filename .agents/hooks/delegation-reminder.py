#!/usr/bin/env python3
"""Reminder hook: a delegated agent's report is a claim, not evidence.

Fires on PostToolUse when a delegation tool returns. Emits one reminder telling the
delegating agent to verify the artifact against the claim before accepting it, then
exits. It never blocks.

Why a reminder and not a gate
-----------------------------
A gate here would have to parse the returned report to learn which files were claimed,
then confirm a follow-up read of each. That is brittle and false-positive prone: the
report is free prose, and a wrong block costs more trust than a missed nudge. So this
hook adds a checkpoint at the hand-off and leaves refusal to the downstream gates that
can decide deterministically (the spec-closeout gate, and the acceptance criteria a task
file already carries).

Why it exists at all
--------------------
`fix-batch` dispatches worktree-isolated agents and `verifier-agent` checks their work,
but both run after the fact. Nothing marks the moment the report arrives, which is the
moment the delegating agent is most likely to accept "done" at face value. The kit's own
history is the argument: in one batch, two of three agents worked from a task premise
that was factually wrong about the code, and nothing in the system caught it.

Contract
--------
stdin   a JSON object with `hook_event_name` and `tool_name`
stdout  one JSON object, or nothing
exit    always 0

Any malformed input, and any unexpected failure, exits 0 silently. A guardrail that
breaks a session because it could not parse its own payload is worse than no guardrail.

Adapted from `delegation-reminder.py` in RepoPrompt Workflows by Balarama Bosch (MIT),
https://github.com/moonray/repoprompt-workflows. Retargeted to this kit's tool set and
made self-contained: the reminder names no rules file, because a hook ships without this
repository around it.
"""
import json
import sys

REMINDER = (
    "DELEGATION CHECKPOINT: a delegated agent just returned a report. That report is a "
    "claim of completion, not evidence. Agent summaries can be optimistic, partial, or "
    "confabulated, and the words 'done', 'fixed', or 'complete' in a return value do not "
    "make the underlying work so. Before accepting it, verify the artifact against the "
    "claim: read the actual diff or files, run the affected tests, or exercise the "
    "behavior. Spot-check at least one load-bearing claim against ground truth rather "
    "than trusting the narrative. If the report asserts something about the code, that "
    "assertion is the first thing to check."
)

# Tools that hand back a delegated agent's work. The harness matcher is the first filter
# and is deliberately allowed to be broad; this set is the precise one. Keeping both
# means a matcher wide enough to catch `Task` can never fire on the unrelated task-list
# tools (`TaskCreate`, `TaskUpdate`, `TaskList`, ...) that merely contain the word.
#
# `Agent` is here because the name is not stable across harnesses in the way the first
# draft assumed. Vanilla Claude Code dispatches subagents through `Task`; the Agent SDK
# surface exposes the same capability as `Agent`. A set covering only one of them leaves
# the hook silently inert on the other, which is the worst failure available to a
# guardrail: nothing is reported, so nothing looks wrong. Found while dogfooding
# feat-0038, where the reminder did not fire on an `Agent` delegation.
DELEGATION_TOOLS = {
    "Task",        # vanilla Claude Code subagent dispatch
    "Agent",       # the same capability on the Agent SDK surface
    "TaskOutput",  # retrieval of a background agent's output
    "agent_run",   # generic delegation used by some harnesses
}


def evaluate(payload):
    """Return the hook's output object for this payload, or None to stay silent."""
    if not isinstance(payload, dict):
        return None
    if payload.get("hook_event_name") != "PostToolUse":
        return None
    if payload.get("tool_name") not in DELEGATION_TOOLS:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": REMINDER,
        }
    }


def main(stdin=None, stdout=None) -> int:
    """Read one payload, emit at most one object. `stdin`/`stdout` are injectable so the
    behavior is reachable from a test without a subprocess."""
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    try:
        payload = json.load(stdin)
    except Exception:
        return 0
    try:
        out = evaluate(payload)
        if out is not None:
            stdout.write(json.dumps(out))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
