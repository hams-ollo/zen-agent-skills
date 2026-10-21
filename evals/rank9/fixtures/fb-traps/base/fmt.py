"""Text formatting helpers."""


def title_case(text):
    """Capitalise each word of a heading."""
    return " ".join(word.capitalize() for word in text.split())
