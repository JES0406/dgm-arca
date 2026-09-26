"""Print the headline numbers and branch table of one or more generator reports (JSON)."""

from __future__ import annotations

import json
import sys

for path in sys.argv[1:]:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    head = {k: v for k, v in data.items() if k not in ("branches", "leaked_examples")}
    print(path.rsplit("/", 1)[-1], head)
    for branch, counts in data["branches"].items():
        print(f"  {branch}: {counts}")
