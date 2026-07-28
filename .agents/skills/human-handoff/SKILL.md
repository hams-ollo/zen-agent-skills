---
name: human-handoff
description: >-
  Packages the current state of a project into a handoff for a person: a business partner,
  a client, or a team member. Produces a document or a short message, in plain language,
  tuned to the reader, with internals and costs redacted when the reader is a client. Use
  this whenever the user wants to bring a person up to speed, ask a collaborator to decide
  something, prep for a meeting, or draft an update. Trigger on phrases like: "write an
  update for my partner", "draft a message to <name> about where we are", "summary for the
  client", "onboard the new dev", "prep for the meeting with the other engineering team",
  "what should I tell <name> about the open questions", "put together a handoff doc for
  whoever picks this up", or any request to explain project status to a person rather than
  an agent. If the handoff target is a fresh agent session or a spawned subagent that will
  execute work, use agent-handoff instead.
---

# Human handoff

Package where a project stands so a person can absorb it, decide on it, or pick it up. The reader is a human with limited time and no access to the repository, so the job is translation and judgment, not a code dump. Get the audience right first, because it changes tone, depth, and what you leave out. If the handoff target is a fresh session or subagent that will execute work rather than a person, use [`agent-handoff`](../agent-handoff/SKILL.md) instead.

## Pick the audience first

The same underlying state renders three different ways. Decide which reader you are writing for before you draft, and if the user has not said, ask in one line.

- **Partner** (a co-founder or business partner, someone with shared stakes): give an honest, grounded picture including realistic estimates of time, cost, and token or API burn when the work involves agents. This reader wants the real number, not an optimistic one. Frame open questions diplomatically, but do not soften the substance. Never invent effort or cost figures; if you cannot ground an estimate, say what it depends on instead.
- **Client** (someone paying for a deliverable): report status, deliverables, and next steps. Redact the internals: no file paths, no architecture details, no your-side costs, no mention of other clients or projects, no token spend. The client cares what they are getting and when, not how the sausage is made.
- **Team member** (a technical collaborator picking up or reviewing work): give the architecture, the open decisions, and how to get oriented. This reader can handle detail and file references. This is the one case where pointing at repo files is appropriate.

## Pick the form

Two output shapes cover almost everything the user asks for:

- **Handoff document**: a standalone Markdown file when the reader needs something durable to work from (onboarding, an open-questions doc, a status packet). Save it into the repo's docs location.
- **Message**: a short, ready-to-send note when the user just needs to tell someone something (a Slack or email update, a nudge, a question). Keep it to the point.

If the user has not said which, infer from the verb: "draft a message" or "tell <name>" means a message; "put together a handoff" or "onboarding doc" means a document.

## Before writing: gather the real state

Ground the handoff in reality, not recollection. Read the repo's `AGENTS.md` or `CLAUDE.md` for context, check `git status` and recent changes, and look at the actual docs or task files that describe current state. A handoff built on a stale mental model is worse than none, because the reader acts on it.

## What every human handoff covers

Underneath the audience tuning, all three readers need the same four things. Render each in the register the audience calls for.

1. **Where things stand.** The honest current state in a few sentences. For a client, this is deliverable status; for a partner or teammate, it is the real state including what is unfinished.
2. **What changed or what is done.** What moved since the reader last looked, or since the project started if this is an introduction.
3. **What is open or needs a decision.** The questions or blockers. Phrase decisions as decisions, with enough context for the reader to actually choose, and a recommendation where you have one. For a partner asking to unblock work, this is usually the heart of the handoff.
4. **What is next and who owns it.** The forward path and the ownership, so nothing falls into the gap between people.

## Tone

Write plainly and honestly. No hype, no padding, no em-dashes (the user will notice and it undercuts the message). Match the reader's register: a partner update can be direct and candid, a client update stays professional and scoped, a teammate handoff can be technical. When drafting a message to a named person, read it back as that person would and cut anything that sounds like spin.

## Conventions

Follow the repo's `AGENTS.md` and its house-style module (in this kit, [`.agents/rules/house-style.md`](../../rules/house-style.md)) for any document you write to disk: Mermaid over ASCII, sentence-case headings, clickable file links, no em-dashes. For client-facing output, strip internal links and paths entirely rather than making them clickable.

## Redaction check before delivering

Before handing back client-facing output, reread it once for leaks: file paths, internal tool names, cost-to-you figures, other-client references, unreleased plans. This single pass is the most common failure point for a client handoff and the cheapest to fix.
