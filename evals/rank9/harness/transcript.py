"""Read a stream-json transcript into the few things the graders need."""
import json
import pathlib


def load(path):
    events = []
    for line in pathlib.Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    return events


def init(events):
    return next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})


def result(events):
    return next((e for e in reversed(events) if e.get("type") == "result"), {})


def tool_uses(events):
    """Every tool call in the transcript, the main agent's and any forwarded subagent's."""
    out = []
    for e in events:
        if e.get("type") != "assistant":
            continue
        for block in (e.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                out.append({"id": block.get("id"), "name": block.get("name"),
                            "input": block.get("input") or {},
                            "parent": e.get("parent_tool_use_id")})
    return out


def tool_results(events):
    out = {}
    for e in events:
        if e.get("type") != "user":
            continue
        content = (e.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                body = block.get("content")
                if isinstance(body, list):
                    body = "\n".join(b.get("text", "") for b in body if isinstance(b, dict))
                out[block.get("tool_use_id")] = body or ""
    return out


def final_text(events):
    res = result(events)
    if isinstance(res.get("result"), str) and res["result"].strip():
        return res["result"]
    for e in reversed(events):
        if e.get("type") == "assistant" and not e.get("parent_tool_use_id"):
            texts = [b.get("text", "") for b in (e.get("message") or {}).get("content") or []
                     if isinstance(b, dict) and b.get("type") == "text"]
            if any(t.strip() for t in texts):
                return "\n".join(texts)
    return ""


def all_text(events):
    """Every piece of assistant text in the run, main agent first, for graders that look for a
    report anywhere rather than only in the last message."""
    texts = []
    for e in events:
        if e.get("type") == "assistant":
            for b in (e.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "text":
                    texts.append(b.get("text", ""))
    return "\n".join(texts)


def first_turn_input_tokens(events):
    for e in events:
        if e.get("type") == "assistant" and not e.get("parent_tool_use_id"):
            u = (e.get("message") or {}).get("usage") or {}
            return (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0) + \
                (u.get("cache_read_input_tokens") or 0)
    return None


def command_of(tu):
    return str(tu["input"].get("command", "")) if tu["name"] in ("Bash", "PowerShell") else ""


def inputs_text(tu):
    return json.dumps(tu["input"], ensure_ascii=False)
