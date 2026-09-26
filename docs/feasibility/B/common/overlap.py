"""Parameter-hash overlap between generated splits (the train/test leakage check).

    uv run python docs/feasibility/B/common/overlap.py train.jsonl test.jsonl ood.jsonl
"""

from __future__ import annotations

import hashlib
import json
import sys
from itertools import combinations


def hashes(path: str) -> set[str]:
    with open(path, encoding="utf-8") as handle:
        return {hashlib.sha1(json.dumps(json.loads(line)["params"], sort_keys=True,
                                        default=str).encode()).hexdigest() for line in handle}


def main() -> None:
    sets = {path.rsplit("/", 1)[-1]: hashes(path) for path in sys.argv[1:]}
    for (a, ha), (b, hb) in combinations(sets.items(), 2):
        print(f"{a} ({len(ha)}) ∩ {b} ({len(hb)}) = {len(ha & hb)}")


if __name__ == "__main__":
    main()
