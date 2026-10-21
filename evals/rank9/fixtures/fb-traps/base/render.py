"""Fixed-width rendering of name and value pairs."""
from build.generated_tables import WIDTHS


def pad(name, value):
    """Left-align value in the column width configured for name."""
    return str(value).ljust(WIDTHS[name] - 1)
