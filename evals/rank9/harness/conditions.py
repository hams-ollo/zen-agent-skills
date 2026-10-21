"""Place a run's condition: which rules files and which skills its project carries.

Everything is read from pinned revisions of this repository with `git show`, never from the
working tree and never from an installed copy, so a condition is the same on every machine.
Each condition lands under the run's own `.claude/`, which the child loads as project memory and
project skills (`--setting-sources project`); the user's own rules and skills are never read.
"""
import re

from common import POST_REV, PRE_REV, repo_git

LENSES = ["autonomy.md", "house-style.md", "review-quality.md"]

# Skills a skill under test composes, so its links resolve the way an install would.
COMPOSES = {
    "house-review": [],
    "review-depth": ["house-review"],
    "verifier-agent": ["spec-conformance"],
    "fix-batch": ["verifier-agent", "spec-conformance"],
}


def _show(rev, path):
    return repo_git("show", f"{rev}:{path}")


def _write(dest, data):
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def place_rules(cwd, which):
    """`pre`: the three lenses as installed before the refresh, all always-on (no paths frontmatter).
    `post`: core.md always-on, plus the three lenses carrying their `paths` frontmatter."""
    rules = cwd / ".claude" / "rules"
    if which == "pre":
        for name in LENSES:
            _write(rules / name, _show(PRE_REV, f".agents/rules/{name}"))
    elif which == "post":
        for name in ["core.md", *LENSES]:
            _write(rules / name, _show(POST_REV, f".agents/rules/{name}"))
    else:
        raise ValueError(which)


def skill_files(rev, name):
    listing = repo_git("ls-tree", "-r", "--name-only", rev, f".agents/skills/{name}/")
    return [line for line in listing.decode().splitlines() if line]


def place_skill(cwd, name, rev=POST_REV, description=None):
    prefix = f".agents/skills/{name}/"
    for path in skill_files(rev, name):
        data = _show(rev, path)
        if description is not None and path.endswith("/SKILL.md"):
            data = swap_description(data.decode("utf-8"), description).encode("utf-8")
        _write(cwd / ".claude" / "skills" / name / path[len(prefix):], data)


_DESC = re.compile(r"^description:.*?(?=^[A-Za-z_][\w-]*:|\Z)", re.S | re.M)


def description_block(text):
    """The raw `description:` block of a SKILL.md frontmatter, folded-scalar lines included."""
    front = text.split("---", 2)[1]
    match = _DESC.search(front)
    return match.group(0) if match else None


def swap_description(text, block):
    head, front, body = text.split("---", 2)
    return head + "---" + _DESC.sub(lambda _m: block, front, count=1) + "---" + body


def shipped_skills(rev=POST_REV):
    """Skill names at rev whose SKILL.md is not marked draft (the ones an install places)."""
    listing = repo_git("ls-tree", "-d", "--name-only", rev, ".agents/skills/").decode().split()
    names = []
    for entry in listing:
        name = entry.rstrip("/").split("/")[-1]
        text = _show(rev, f".agents/skills/{name}/SKILL.md").decode("utf-8")
        if not re.search(r"^\s*status:\s*draft\s*$", text.split("---", 2)[1], re.M):
            names.append(name)
    return names


def place(cwd, condition):
    """condition is a list of tokens: rules:pre, rules:post, skill:<name>, listing:pre|post."""
    for token in condition:
        kind, _, value = token.partition(":")
        if kind == "rules":
            place_rules(cwd, value)
        elif kind == "skill":
            for name in [value, *COMPOSES.get(value, [])]:
                place_skill(cwd, name)
        elif kind == "listing":
            for name in shipped_skills(POST_REV):
                desc = None
                if value == "pre":
                    pre_text = _show(PRE_REV, f".agents/skills/{name}/SKILL.md").decode("utf-8")
                    desc = description_block(pre_text)
                place_skill(cwd, name, description=desc)
        else:
            raise ValueError(token)
