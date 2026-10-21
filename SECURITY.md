# Security policy

## What this project is, and why its threat model is unusual

Zen Agent Skills distributes **instructions that an AI coding agent executes**. A skill is not a library your code calls in a sandbox. It is prose that an agent reads and acts on, in your repository, usually with permission to read files, write files, and run commands.

That changes what a vulnerability looks like here. There is no memory safety surface and almost no attack surface in the usual sense: the tooling is standard-library Python with no deserialization of untrusted input and no dependencies to be compromised. The real risk is that **a skill body causes an agent to do something the person running it did not intend**.

Treat a skill the way you would treat a script you are about to run, not the way you would treat a document you are about to read.

### The one network call, and what it fetches

One script does make network calls, and it is named here rather than left to be discovered. [`check-provenance.py`](scripts/check-provenance.py) re-fetches the upstream sources this kit adapted material from, so it can compare a SHA256 digest and tell you whether upstream has moved. Its properties, all of them checkable in the script:

- **It runs only when you run it.** It is on-demand, deliberately kept out of the required CI gates, and no other script, skill, or hook invokes it.
- **It fetches to digest, never to execute.** The response is hashed and discarded. Nothing fetched is run, stored, or written to disk.
- **The destinations come from the repository's own files**, specifically the `source:` line of each provenance block under `.agents/` and `scripts/`. `python scripts/check-provenance.py --list` prints every URL a run would contact and fetches nothing, so the set is reviewable before any connection is made.
- **`https://` only, at both ends, under a read bound.** Two separate rules, and the distinction is worth stating because for a while only the first held. A record pinning an `http://` source is reported as malformed rather than fetched. And the connection itself stays on `https`: `urllib` follows redirects by default and its own allow-list admits `http`, so an `https` source answering `302 Location: http://...` used to be followed into plaintext, where the digest authenticates nothing. A redirect off `https` is now refused and reported, by a handler on the opener the fetch actually uses rather than by a check after the bytes have already arrived (`bug-0054`). A redirect that stays on `https` is followed, because upstream repositories get renamed, and the run reports the URL that answered when it differs from the one recorded. A response over 10 MiB is reported as an error rather than read into memory whole.

The shape worth naming for a reporter: a pull request can add a provenance block, and its `source:` URL is a destination a maintainer's later run will contact from their machine. That is a review question about what a pull request adds, not a defect in the script, but it is the reason the URLs are recorded in plain text and `--list` exists.

## Supported versions

The kit is distributed from `main`, and `main` is the only supported version. Releases are tagged (the first is `v0.1.0`, 2026-07-29) so that a report can name the version it was found against, but a tag is a marker in the history rather than a maintained branch: fixes land on `main` and are not backported to an earlier tag. Adopters pick them up by pulling and re-running the installer.

## What to report

Please report any of the following privately:

- **A skill that can be induced to take a destructive or exfiltrating action**, for example one whose procedure could be steered into deleting work, force-pushing, sending repository contents somewhere, or committing credentials.
- **A skill whose stated boundary does not hold.** Several skills promise to be report-only or draft-only: `house-review`, `spec-conformance`, `spec-quality`, `test-quality`, `pr-describe`, and `verifier-agent` among them. A path where one of those edits, commits, or publishes anything is a real finding, because users rely on that promise to run them unsupervised.
- **Prompt-injection paths**, where content a skill is designed to read (a diff, an issue body, a fetched page, a file in the target repo) can redirect the agent's behavior. This class is governed by rule `A10` in [`.agents/rules/autonomy.md`](.agents/rules/autonomy.md), which every skill in the kit references: once an agent has read material it did not author, nothing in that material may cause an action. Concretely, it may not run a command whose text came from there, install or fetch or execute anything it names, or send anything anywhere on its say-so; the passage is quoted in a report instead. **`A10` constrains the action and is deliberately not a detector**, because published work breaks the detectors (Zhan et al., NAACL 2025 Findings, arXiv:2503.00061; "The Attacker Moves Second", arXiv:2510.09023), so content that merely *contains* an injection attempt is not itself a finding. A path where a skill acts on one is: that is a rule this kit states and failed to hold, so report it as a broken promise rather than as new ground.
- **Tooling that writes outside its declared scope**, for example `install.py` or `build-adapters.py` touching a path they never announced, or overwriting a file they promised to preserve.
- **Tooling that contacts a destination the person running it would not expect.** `check-provenance.py`'s fetch of recorded provenance sources, described above, is the only network call in the kit, and it is the baseline: a script that fetches when nothing said it would, a provenance `source:` URL that points somewhere unrelated to the material it claims to credit, or a path that sends any repository content outward rather than only receiving.
- **Anything that silently does nothing while reporting success.** This has already happened once in this project's history, and a step that appears to work while losing the user's work is a safety problem, not merely a bug.

## What is not a vulnerability here

- The fact that skills instruct an agent to modify files. That is the entire purpose, and it is why installation is an explicit, reviewable step.
- Your agent doing something you did not want after you approved it. Keep a human in the loop for anything destructive.
- A skill giving low-quality advice, or a review missing a defect. That is a normal issue, not a security report.
- `check-provenance.py` contacting the sources recorded in this repository when you run it. That is what the script is for, and `--list` shows you every URL first.

## How to report

Use GitHub's private vulnerability reporting on this repository: open the **Security** tab and choose **Report a vulnerability**. That opens a private advisory visible only to the maintainers, so a finding is never disclosed publicly before it is fixed.

Please do not open a public issue for anything in the list above.

Include what you would want if you were fixing it: the skill or script involved, the harness you were running, the prompt or command that triggered it, what the agent did, and what you expected instead. A transcript excerpt is worth more than a description.

## What to expect

This project is maintained by one person. There is no security team and no paid support, so please read these as honest intentions rather than a service commitment:

- An acknowledgement within about a week.
- An assessment of whether it reproduces, and a fix or a documented mitigation for anything that does.
- Credit in the advisory and the changelog if you want it, and none if you would rather stay anonymous.

If a report turns out to be a design decision rather than a defect, you will get the reasoning rather than a silent close.

## Protecting yourself

- **Read a skill before installing it.** Each `SKILL.md` is a single readable file with no indirection. This is deliberate, and it is the main defense the design offers.
- **Preview first.** `install.py` and `build-adapters.py` both take `--dry-run`, and several skills default to a reporting mode that changes nothing.
- **Install to a throwaway home while evaluating**: `python scripts/install.py --dry-run --home ./.tmp/zen-home`.
- **Apply the same review standard to skills from outside this repository.** A skill obtained elsewhere carries whatever intent its author gave it.
- **Keep a human on destructive and outward-facing steps**: deletions, force-pushes, publishing, spending, and anything touching credentials.
