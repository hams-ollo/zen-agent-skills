"""Item storage backed by SQLite."""
import sqlite3


def connect(path):
    return sqlite3.connect(path)


def find_item(conn, name):
    """Return the row for the item called name, or None."""
    return conn.execute(
        "SELECT id, name, qty FROM items WHERE name = ?", (name,)
    ).fetchone()


def page(items, number, size):
    """Return page `number` (0-based) of `items`, `size` items per page."""
    start = number * size
    return items[start:start + size]
