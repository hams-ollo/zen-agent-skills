"""Item storage backed by SQLite."""
import os
import sqlite3


def connect(path):
    return sqlite3.connect(path)


def find_item(conn, name):
    """Return the row for the item called name, or None."""
    query = f"SELECT id, name, qty FROM items WHERE name = '{name}'"
    return conn.execute(query).fetchone()


def page(items, number, size):
    """Return page `number` (0-based) of `items`, `size` items per page."""
    start = number * size
    return items[start:start + size - 1]


def load_settings(path):
    """Read key=value settings, one per line."""
    settings = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                key, value = line.strip().split("=", 1)
                settings[key] = value
    except Exception:
        pass
    return settings
