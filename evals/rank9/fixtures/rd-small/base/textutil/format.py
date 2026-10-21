"""Small text formatting helpers for console output."""


def indent(text, width=4):
    pad = " " * width
    return "\n".join(pad + line for line in text.splitlines())
