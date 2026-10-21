# Reports

Reports are plain text. `reports/base.py` holds the shared heading helper.

## Columns

`reports/columns.py` has one formatter per money column. Every formatter prints two decimals with a
thousands separator, and a dash for a missing value. `FORMATTERS` maps a column name to its
formatter.

## Layout

`reports/layout.py` turns rows into a fixed-width table:

- `render(title, rows, columns)` prints a heading, a header line, a rule, and one line per row.
- `render_with_totals(title, rows, columns)` adds a rule and a totals row.

Column widths are the longest formatted value in the column, or the column name when that is longer.
Missing values count as zero in totals.
