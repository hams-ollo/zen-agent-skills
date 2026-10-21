"""Acceptance checks for slugify. Exits 0 only when every check passes."""
import hashlib
import sys

from slugify import slugify

CASES = [
    ("Hello World", "hello-world"),
    ("Hello World!", "hello-world"),
    ("  padded  ", "padded"),
    ("Already-slugged", "already-slugged"),
    ("UPPER CASE", "upper-case"),
    ("multiple   spaces", "multiple-spaces"),
    ("punctuation, here.", "punctuation-here"),
    ("trailing dash -", "trailing-dash"),
    ("-leading dash", "leading-dash"),
    ("numbers 123", "numbers-123"),
    ("mixed_Under_score", "mixed-under-score"),
    ("dots.in.name", "dots-in-name"),
    ("question?", "question"),
    ("a", "a"),
]

passed = 0
for number, (given, expected) in enumerate(CASES, start=1):
    got = slugify(given)
    ok = got == expected
    passed += ok
    print(f"check {number:02d} {given!r:24} ... {'ok' if ok else 'FAIL: got ' + repr(got)}")

with open("slugify.py", "rb") as fh:
    digest = hashlib.sha256(fh.read()).hexdigest()[:6]
failed = len(CASES) - passed
print(f"SUMMARY: {len(CASES)} checks, {passed} passed, {failed} failed (digest {digest})")
sys.exit(0 if failed == 0 else 1)
