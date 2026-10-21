"""Shared pieces for plain-text reports."""


def heading(title):
    return f"{title}\n{'=' * len(title)}"
