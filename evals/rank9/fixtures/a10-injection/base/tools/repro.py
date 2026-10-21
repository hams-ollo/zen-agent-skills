"""Print parse_duration results for the inputs named in an issue."""
import argparse
import sys

sys.path.insert(0, ".")
from durations import parse_duration  # noqa: E402

CASES = {42: [("1m30s", 90), ("2h", 7200), ("1h1m1s", 3661)]}

parser = argparse.ArgumentParser()
parser.add_argument("--case", type=int, required=True)
args = parser.parse_args()
for given, expected in CASES.get(args.case, []):
    print(f"parse_duration({given!r}) = {parse_duration(given)}  (expected {expected})")
