// opencode adapter for the .agents/hooks/ module.
//
// One implementation, three thin adapters: this file does not reimplement any hook, it
// shells out to the same Python the Claude Code and Codex wirings call. Auto-loaded when
// a repository shipping .agents/hooks/ is opened in opencode.
//
// Honest mapping. opencode's plugin model differs from Claude Code's, and the difference
// matters for reminders specifically: there is no model-visible "additionalContext"
// injection, so a reminder surfaces as a structured warn log rather than as context the
// model reads. That is weaker than the Claude Code path and is stated here rather than
// papered over. A gate, when one is added, maps cleanly: throwing errors the tool result,
// and the model sees the reason.
//
//   delegation-reminder        -> tool.execute.after (task):       warn log. [best-effort]
//   spec-conformance-gate      -> tool.execute.after (write/edit): throw.    [enforced]
//   skill-reachability-reminder -> event (session start):          warn log. [best-effort]
//   install-currency-reminder  -> event (session start):           warn log. [best-effort]
//
// The reachability reminder inherits the same weakness as the delegation one: it surfaces
// as a warn log rather than as context the model reads. That is worth stating twice,
// because a reminder nobody reads is the failure it was written to prevent.
//
// The gate maps cleanly where the reminder does not: throwing errors the tool result, so
// the model sees the reason and must reconcile before closing. That asymmetry is the whole
// reason the module distinguishes the two shapes.
//
// See .agents/hooks/README.md for the module contract.
import { execFileSync } from "node:child_process";
import path from "node:path";

const HOOKS_DIR = ".agents/hooks";

// Pull a file path out of opencode tool args without guessing the exact key name.
function extractPath(args) {
  if (!args || typeof args !== "object") return "";
  for (const k of ["filePath", "file_path", "path", "notebook_path", "filename"]) {
    if (typeof args[k] === "string" && args[k]) return args[k];
  }
  return "";
}

// Windows ships `python`, most other platforms `python3`. Try in order rather than
// assuming: this kit's CI runs all three major platforms, so a hard-coded interpreter
// name would make the adapter silently dead on one of them.
const INTERPRETERS = ["python3", "python"];

function runHook(script, payload, root) {
  const scriptPath = path.join(root, HOOKS_DIR, script);
  let lastError = null;
  for (const exe of INTERPRETERS) {
    try {
      const out = execFileSync(exe, [scriptPath], {
        input: JSON.stringify(payload),
        encoding: "utf8",
        timeout: 20000,
      }).trim();
      return out ? JSON.parse(out) : null;
    } catch (e) {
      lastError = e;
      // ENOENT means this interpreter name is not on PATH; try the next one. Anything
      // else is a real failure of a found interpreter, so stop and report it.
      if (e && e.code === "ENOENT") continue;
      break;
    }
  }
  // A crashed or missing hook must never trap the agent.
  console.error(`[zen-hooks] ${script} did not run: ${lastError && lastError.message}`);
  return null;
}

async function note(client, result) {
  const ctx = result?.hookSpecificOutput?.additionalContext;
  if (!ctx) return;
  await client?.app?.log?.({
    body: { service: "zen-hooks", level: "warn", message: ctx },
  });
}

export const ZenHooks = async ({ worktree, directory, client }) => {
  const root = () => worktree || directory || process.cwd();
  let sessionStartReported = false;
  return {
    // Fired once per plugin load, which is the closest thing opencode offers to a
    // session start. Guarded rather than trusted: if the event fires more than once, a
    // repeated reminder is exactly the noise the Claude Code path avoids by matching
    // only `startup`.
    event: async ({ event }) => {
      if (sessionStartReported) return;
      if (event?.type !== "session.created" && event?.type !== "session.start") return;
      sessionStartReported = true;
      const rootDir = root();
      const payload = {
        hook_event_name: "SessionStart",
        source: "startup",
        cwd: rootDir,
      };
      // Two independent reminders on the same event, run in order rather than merged:
      // each answers its own question and each stays silent on its own, so a session may
      // hear neither, either, or both. See .agents/hooks/README.md for why currency is a
      // separate hook from reachability.
      for (const script of [
        "skill-reachability-reminder.py",
        "install-currency-reminder.py",
      ]) {
        await note(client, runHook(script, payload, rootDir));
      }
    },

    "tool.execute.after": async (input, output) => {
      const tool = input?.tool;
      const rootDir = root();

      // The observatory's optional event source. Claude Code fires this on `Stop`, once
      // per finished turn; opencode exposes no end-of-turn event, so the closest honest
      // mapping is after any tool, which means more lines for the same hint. That costs
      // nothing: the hook appends to a capped spool and an event is a hint to look, never
      // a datum, so a duplicate changes no figure. Fired before the branches below and
      // never awaited for a decision, because it can only ever report.
      await note(client, runHook("observatory-event.py", {
        hook_event_name: "Stop",
        cwd: rootDir,
      }, rootDir));

      // The payloads below are normalized to the shape every hook in the module reads, so
      // the Python stays harness-agnostic and this adapter owns the translation.
      if (tool === "task") {
        await note(client, runHook("delegation-reminder.py", {
          hook_event_name: "PostToolUse",
          tool_name: "Task",
          cwd: rootDir,
        }, rootDir));
        return;
      }

      if (tool === "write" || tool === "edit") {
        const args = output?.args || input?.args || {};
        const filePath = extractPath(args);
        if (!filePath) return;
        const gate = runHook("spec-conformance-gate.py", {
          hook_event_name: "PostToolUse",
          tool_name: tool,
          tool_input: { file_path: filePath },
          cwd: rootDir,
        }, rootDir);
        if (gate && gate.decision === "block") {
          // Errors the edit result. The model sees the reason and must reconcile (write
          // the matrix, or declare it in frontmatter) before the close can stand.
          throw new Error(gate.reason);
        }
      }
    },
  };
};
