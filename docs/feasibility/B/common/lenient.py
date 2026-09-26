"""Lenient re-scoring of a baseline run: when there is no <answer> block, take the last
number/date/label in the last 300 characters of the output and verify that instead.

Separates "cannot follow the output format" (fixable by the format reward and SFT) from
"cannot compute the answer" (what GRPO has to fix).

    uv run python docs/feasibility/B/common/lenient.py docs/feasibility/B/planner/baseline_qwen3-0.6b.json \
        docs/feasibility/B/planner/generator.py
"""

from __future__ import annotations

import json
import re
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from harness import load_verifier  # noqa: E402

TOKEN = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}:\d{2}|P[123]|\b[A-E]\b|-?\d+(?:[.,]\d+)?")


def main() -> None:
    run, gen = sys.argv[1], sys.argv[2]
    is_correct = load_verifier(gen)
    data = json.load(open(run, encoding="utf-8"))
    strict = lenient = 0
    for r in data["results"]:
        strict += r["correct"]
        if r["correct"]:
            lenient += 1
            continue
        tail = r["raw_tail"].split("</think>")[-1]
        found = TOKEN.findall(tail)
        if found and is_correct(found[-1], r["expected"]):
            lenient += 1
    n = len(data["results"])
    print(f"{data['summary']['model']}: strict {strict}/{n}, lenient {lenient}/{n}")


if __name__ == "__main__":
    main()
