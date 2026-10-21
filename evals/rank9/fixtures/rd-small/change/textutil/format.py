"""Small text formatting helpers for console output."""


def indent(text, width=4):
    pad = " " * width
    return "\n".join(pad + line for line in text.splitlines())


def truncate(text, limit, marker="..."):
    """Shorten text to at most `limit` characters, ending with `marker` when cut."""
    if limit < len(marker):
        raise ValueError("limit is shorter than the marker")
    if len(text) <= limit:
        return text
    return text[: limit - len(marker)] + marker


def column(values, width):
    """Right-align each value in a column of the given width."""
    return [str(value).rjust(width) for value in values]
