"""Shared helpers for the feasibility generators: dataset stats, leakage and dedup checks.

Every topic generator subclasses ``rlm.generate_problems.ProblemGenerator`` and calls
``run_cli`` so that all topics report the same numbers: branch table, template count,
answer-as-substring leakage, parameter-hash dedup across splits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from rlm.generate_problems import Problem, ProblemGenerator


def param_hash(params: dict[str, Any]) -> str:
    return hashlib.sha1(json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()[:12]


def leaks(answer: str, question: str) -> bool:
    """Answer appears in the statement as a whole number token (not inside 4,0 or 12.5), also 12,34."""
    variants = {answer, answer.replace(".", ",")}
    return any(v and re.search(rf"(?<![\d.,]){re.escape(v)}(?![\d]|[.,]\d)", question) for v in variants)


def describe_split(problems: list[Problem]) -> dict[str, Any]:
    counters: dict[str, Counter] = {}
    for p in problems:
        for branch, value in p.branches.items():
            counters.setdefault(branch, Counter())[value] += 1
    answers = Counter(p.answer for p in problems)
    return {
        "n_problems": len(problems),
        "n_templates": len({p.template_id for p in problems}),
        "distinct_answers": len(answers),
        "most_common_answer": answers.most_common(1)[0] if answers else None,
        "answer_leaked_in_statement": sum(leaks(p.answer, p.question) for p in problems),
        "mean_question_chars": round(sum(len(p.question) for p in problems) / max(len(problems), 1)),
        "branches": {k: dict(sorted(v.items())) for k, v in counters.items()},
    }


def branch_table_md(stats: dict[str, dict[str, Any]]) -> str:
    """Markdown table: one row per (branch, value), one column per split."""
    splits = list(stats)
    keys: dict[tuple[str, str], None] = {}
    for s in splits:
        for b, vals in stats[s]["branches"].items():
            for v in vals:
                keys[(b, v)] = None
    lines = ["| branch | value | " + " | ".join(splits) + " |", "|---|---|" + "---|" * len(splits)]
    for b, v in keys:
        cells = [str(stats[s]["branches"].get(b, {}).get(v, 0)) for s in splits]
        lines.append(f"| {b} | {v} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def run_cli(generator: ProblemGenerator, default_out: Path, rules_text: str = "") -> None:
    """Generate train/test/ood, write JSONL, print stats and cross-split overlap."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=40, help="problems per split")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, default=default_out)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    stats: dict[str, dict[str, Any]] = {}
    hashes: dict[str, set[str]] = {}
    for split in ("train", "test", "ood"):
        problems = generator.generate(args.n, split, args.seed)
        hashes[split] = {param_hash(p.params) for p in problems}
        stats[split] = describe_split(problems)
        with (args.out / f"{split}.jsonl").open("w", encoding="utf-8") as fh:
            for p in problems:
                row = asdict(p)
                if rules_text:
                    row["question"] = f"{rules_text}\n\n{row['question']}"
                row["split"] = split
                row["label_source"] = "generator"
                row["param_hash"] = param_hash(p.params)
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    overlap = {
        "train&test": len(hashes["train"] & hashes["test"]),
        "train&ood": len(hashes["train"] & hashes["ood"]),
        "test&ood": len(hashes["test"] & hashes["ood"]),
    }
    summary = {s: {k: v for k, v in st.items() if k != "branches"} for s, st in stats.items()}
    print(json.dumps({"summary": summary, "param_hash_overlap": overlap}, indent=1, ensure_ascii=False))
    print()
    print(branch_table_md(stats))
    first = json.loads((args.out / "test.jsonl").open(encoding="utf-8").readline())
    print("\nEjemplo (test):\n" + first["question"][-900:] + f"\nRespuesta: {first['answer']}")
