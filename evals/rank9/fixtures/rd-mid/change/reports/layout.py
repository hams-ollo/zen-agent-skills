"""Lay out report rows as fixed-width text."""
from reports.base import heading
from reports.columns import FORMATTERS


def column_widths(rows, columns):
    """Width of each column: the longest formatted value or the header."""
    widths = {}
    for name in columns:
        cells = [FORMATTERS[name](row.get(name)) for row in rows]
        widths[name] = max([len(name)] + [len(cell) for cell in cells])
    return widths


def header_line(columns, widths):
    return "  ".join(name.rjust(widths[name]) for name in columns)


def rule_line(columns, widths):
    return "  ".join("-" * widths[name] for name in columns)


def row_line(row, columns, widths):
    cells = []
    for name in columns:
        cells.append(FORMATTERS[name](row.get(name)).rjust(widths[name]))
    return "  ".join(cells)


def render(title, rows, columns):
    """Render rows as a titled, fixed-width table."""
    widths = column_widths(rows, columns)
    out = [heading(title), "", header_line(columns, widths), rule_line(columns, widths)]
    for row in rows:
        out.append(row_line(row, columns, widths))
    return "
".join(out)


def totals_row(rows, columns):
    """Sum each column, treating missing values as zero."""
    return {name: sum(row.get(name) or 0 for row in rows) for name in columns}


def render_with_totals(title, rows, columns):
    """Render rows followed by a rule and a totals row."""
    widths = column_widths(rows + [totals_row(rows, columns)], columns)
    body = render(title, rows, columns).splitlines()
    body.append(rule_line(columns, widths))
    body.append(row_line(totals_row(rows, columns), columns, widths))
    return "
".join(body)
