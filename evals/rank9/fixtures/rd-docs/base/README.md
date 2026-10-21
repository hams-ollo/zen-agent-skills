# ledgerline

Ledgerline turns bank exports into monthly summaries.

## Install

    pip install ledgerline

## Usage

Point it at a folder of CSV exports:

    ledgerline summarise exports/

It writes one summary per month into `summaries/`. Each summary lists totals by category, the
largest transactions, and anything it could not categorise.

## Categories

Categories come from `categories.toml`. Each category has a name and a list of patterns matched
against the transaction description. The first matching category wins, so put specific patterns
before general ones.

## Limits

Ledgerline reads CSV only. It does not connect to a bank, and it never sends data anywhere.

## Contributing

Open an issue before a large change. Run the tests with `python -m unittest`.
