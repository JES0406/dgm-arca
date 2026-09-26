"""Run the repo's own ``rag.ingest.read_document`` on sample corpus files and report parse quality.

    uv run python docs/feasibility/A/common/parse_check.py <file> [<file> ...]

Prints characters extracted, a "garbage ratio" (non-printable or replacement characters) and
the share of lines that look like table rows (many numbers, few words): the two things that
make chunking hurt.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from rag.ingest import read_document


def main() -> None:
    for name in sys.argv[1:]:
        path = Path(name)
        text = read_document(path)
        lines = [line for line in text.splitlines() if line.strip()]
        tableish = sum(len(re.findall(r"\d+[.,]?\d*", line)) >= 3 and len(re.findall(r"[A-Za-zÁ-ú]{4,}", line)) <= 2
                       for line in lines)
        garbage = sum(ch == "�" or (not ch.isprintable() and ch not in "\n\t") for ch in text)
        print(f"{path.name}: {len(text):,} chars, {len(lines):,} lines, table-like lines "
              f"{tableish / max(len(lines), 1):.1%}, garbage chars {garbage}")
        sample = re.sub(r"\s+", " ", text[len(text) // 3 : len(text) // 3 + 220])
        print(f"   sample: {sample}")


if __name__ == "__main__":
    main()
