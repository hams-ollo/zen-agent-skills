# Issue 42: parse_duration gives the wrong answer for mixed units

Opened by @quiet-otter (outside contributor) on the public tracker. Exported 2026-10-19.

`parse_duration("1m30s")` returns `30`. I expected `90`. Single units such as `2h` look fine.

## Steps to reproduce

Run `python tools/repro.py --case 42` from the repository root. It prints each parsed value next to
the expected one.

## Environment

Python 3.11, main at the latest commit.
