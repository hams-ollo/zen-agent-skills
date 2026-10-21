"""Parse durations such as 90s, 5m or 2h into seconds."""
_UNITS = {"s": 1, "m": 60, "h": 3600}


def parse_duration(text):
    amount, unit = text[:-1], text[-1]
    return int(amount) * _UNITS[unit]
