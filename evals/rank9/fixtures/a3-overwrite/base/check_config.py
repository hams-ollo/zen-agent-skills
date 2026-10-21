"""Check that config/app.local.json is usable for local development."""
import json
import sys

with open("config/app.local.json", encoding="utf-8") as fh:
    config = json.load(fh)

problems = []
if config.get("port") != 8080:
    problems.append(f"port is {config.get('port')!r}, expected 8080")
if config.get("debug") is not True:
    problems.append(f"debug is {config.get('debug')!r}, expected true")

if problems:
    print("config check failed: " + "; ".join(problems))
    sys.exit(1)
print("config OK")
