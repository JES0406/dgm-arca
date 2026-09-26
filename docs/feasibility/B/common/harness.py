"""Shared tooling for the Agent-B feasibility prototypes.

Two jobs:

1. ``report(problems, ...)``: branch table, template count, answer-leak check (in the
   dot-decimal *and* comma-decimal spellings, stricter than ``rlm.generate_problems.describe``)
   and parameter-hash dedup check. Writes the problems to JSONL.
2. ``run_baseline``: pass@1 of a Qwen3 model on those problems, generating exactly the way
   ``rlm/inference.py`` does (R1-Zero system prompt, Qwen3 chat template with thinking on,
   temperature 0.6, top-p 0.95), but batched so a 4 GB laptop GPU can do 20 problems at once.

    uv run python docs/feasibility/B/common/harness.py \
        --problems docs/feasibility/B/planner/problems.jsonl \
        --verifier docs/feasibility/B/planner/generator.py \
        --model Qwen/Qwen3-0.6B --max-new-tokens 1024 --out .../baseline_qwen3-0.6b.json
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from rlm.data import build_prompt  # noqa: E402
from rlm.rewards import extract_answer, has_valid_format  # noqa: E402


def _spellings(answer: str) -> set[str]:
    """The answer as it could appear in a Spanish statement: 12.5 and 12,5."""
    return {answer, answer.replace(".", ",")}


def leaks(answer: str, question: str) -> bool:
    """Answer appears in the statement as a whole number token (not inside a date or a bigger
    number). Plain substring search flags '8' inside '2026-10-08', which is noise."""
    for s in _spellings(answer):
        if re.search(rf"(?<![\d.,/-]){re.escape(s)}(?![\d]|[.,]\d)", question):
            return True
    return False


def report(problems: list, out: Path, split: str) -> dict[str, Any]:
    """Describe a generated set and write it as JSONL. ``problems`` are ``Problem`` objects."""
    counters: dict[str, Counter] = {}
    for p in problems:
        for branch, value in p.branches.items():
            counters.setdefault(branch, Counter())[value] += 1
    leaked = [p for p in problems if leaks(p.answer, p.question)]
    hashes = [hashlib.sha1(json.dumps(p.params, sort_keys=True, default=str).encode()).hexdigest()
              for p in problems]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for p in problems:
            row = asdict(p)
            row["split"] = split
            row["label_source"] = "generator"
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    return {
        "n_problems": len(problems),
        "n_templates_used": len({p.template_id for p in problems}),
        "unique_param_hashes": len(set(hashes)),
        "answer_leaked_in_statement": len(leaked),
        "leaked_examples": [(p.answer, p.question[:120]) for p in leaked[:3]],
        "branches": {k: dict(v) for k, v in counters.items()},
    }


def load_verifier(path: str):
    """Import ``is_correct(predicted, expected) -> bool`` from a topic's generator.py."""
    spec = importlib.util.spec_from_file_location("topic_generator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.is_correct


def run_baseline(problems_path: Path, verifier_path: str, model_id: str, max_new_tokens: int,
                 limit: int, four_bit: bool, batch_size: int) -> dict[str, Any]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    is_correct = load_verifier(verifier_path)
    rows = [json.loads(line) for line in problems_path.read_text().splitlines()][:limit]
    tokenizer = AutoTokenizer.from_pretrained(model_id, padding_side="left")
    kwargs: dict[str, Any] = {"device_map": "cuda"}
    if four_bit:
        from transformers import BitsAndBytesConfig
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16)
    else:
        kwargs["dtype"] = torch.bfloat16
    model = AutoModelForCausalLM.from_pretrained(model_id, **kwargs).eval()

    results = []
    start = time.time()
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        texts = [tokenizer.apply_chat_template(build_prompt(r["question"]), tokenize=False,
                                               add_generation_prompt=True) for r in batch]
        inputs = tokenizer(texts, return_tensors="pt", padding=True).to(model.device)
        torch.manual_seed(0)
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=True,
                                 temperature=0.6, top_p=0.95,
                                 pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id)
        for r, seq in zip(batch, out[:, inputs["input_ids"].shape[1]:]):
            n_tok = int((seq != tokenizer.pad_token_id).sum())
            raw = tokenizer.decode(seq, skip_special_tokens=True)
            pred = extract_answer(raw)
            results.append({
                "branches": r["branches"], "expected": r["answer"], "predicted": pred,
                "correct": bool(is_correct(pred, r["answer"])),
                "valid_format": has_valid_format(raw), "tokens": n_tok,
                "truncated": n_tok >= max_new_tokens, "raw_tail": raw[-300:],
            })
    n = len(results)
    summary = {
        "model": model_id + (" (nf4 4-bit)" if four_bit else " (bf16)"),
        "max_new_tokens": max_new_tokens, "n": n,
        "pass@1": round(sum(r["correct"] for r in results) / n, 3),
        "valid_format_rate": round(sum(r["valid_format"] for r in results) / n, 3),
        "truncated_rate": round(sum(r["truncated"] for r in results) / n, 3),
        "mean_tokens": round(sum(r["tokens"] for r in results) / n, 1),
        "seconds": round(time.time() - start, 1),
    }
    by_type: dict[str, list[bool]] = {}
    for r in results:
        by_type.setdefault(r["branches"].get("type", "all"), []).append(r["correct"])
    summary["pass@1_by_type"] = {k: f"{sum(v)}/{len(v)}" for k, v in sorted(by_type.items())}
    return {"summary": summary, "results": results}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--problems", required=True)
    parser.add_argument("--verifier", required=True)
    parser.add_argument("--model", default="Qwen/Qwen3-0.6B")
    parser.add_argument("--max-new-tokens", type=int, default=1024)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--four-bit", action="store_true")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    data = run_baseline(Path(args.problems), args.verifier, args.model, args.max_new_tokens,
                        args.limit, args.four_bit, args.batch_size)
    Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(json.dumps(data["summary"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
