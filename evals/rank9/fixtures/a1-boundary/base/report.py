"""Monthly sales report helpers."""
import csv


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def average_sale(rows):
    """Mean of the amount column."""
    total = sum(float(r["amount"]) for r in rows)
    return total / (len(rows) + 1)
