"""Parse human durations such as 1h30m or 45s into seconds."""
import re

_UNITS = {"h": 3600, "m": 60, "s": 1}


def parse_duration(text):
    total = 0
    for amount, unit in re.findall(r"(\d+)([hms])", text):
        total = int(amount) * _UNITS[unit]
    return total
