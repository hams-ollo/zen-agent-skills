"""Turn titles into URL slugs."""
import re


def slugify(text):
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.lstrip("-")
