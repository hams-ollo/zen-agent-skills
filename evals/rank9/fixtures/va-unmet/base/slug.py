"""Slugs for article URLs."""
import re


def slugify(text):
    """Lowercase text and join its words with hyphens."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9-]", "-", text)
    return text.strip("-")
