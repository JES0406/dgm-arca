"""Measure pass@1 of a Qwen3 checkpoint on a generated JSONL, with the R1-Zero prompt.

Same prompt and sampling as ``rlm/inference.py`` (temperature 0.6, top_p 0.95), batched.
Verifiers: ``numeric`` (tolerance, accepts Spanish decimal comma) or ``exact``.

    uv run python docs/feasibility/A/common/pass_at_1.py --data docs/feasibility/A/luz/data/test.jsonl \
        --model Qwen/Qwen3-0.6B --n 20 --verifier numeric --tol 0.01
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from rlm.data import build_prompt
from rlm.rewards import extract_answer, has_valid_format

NUM = re.compile(r"-?\d+(?:[.,]\d+)*")


def parse_number(text: str | None) -> float | None:
    """Last number in the text; handles 1.234,56 / 1,234.56 / 12,5 / 12.5."""
    if not text:
        return None
    found = NUM.findall(text.replace(" ", " "))
    if not found:
        return None
    raw = found[-1]
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".") if raw.rfind(",") > raw.rfind(".") else raw.replace(",", "")
    elif "," in raw:
        parts = raw.split(",")
        # "12,5" / "12,34" -> decimal comma; "1,234" / "1,234,567" -> thousands separator.
        raw = f"{parts[0]}.{parts[1]}" if len(parts) == 2 and len(parts[1]) != 3 else raw.replace(",", "")
    elif raw.count(".") > 1:
        raw = raw.replace(".", "")
    try:
        return float(raw)
    except ValueError:
        return None


def check(pred: str | None, expected: str, kind: str, tol: float) -> bool:
    if pred is None:
        return False
    if kind == "numeric":
        p, e = parse_number(pred), parse_number(expected)
        return p is not None and e is not None and abs(p - e) <= tol + 1e-9
    norm = lambda s: re.sub(r"\s+", "", s).strip().upper()  # noqa: E731
    return norm(pred) == norm(expected)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--model", default="Qwen/Qwen3-0.6B")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--verifier", choices=["numeric", "exact"], default="numeric")
    ap.add_argument("--tol", type=float, default=0.0)
    ap.add_argument("--max-new-tokens", type=int, default=1024)
    ap.add_argument("--batch", type=int, default=10)
    ap.add_argument("--load-4bit", action="store_true")
    ap.add_argument("--device", default="cuda", help="cuda or cpu (cpu runs in float32)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = [json.loads(line) for line in Path(args.data).open(encoding="utf-8")][: args.n]
    tok = AutoTokenizer.from_pretrained(args.model, padding_side="left")
    on_cpu = args.device == "cpu"
    kwargs: dict = {"dtype": torch.float32 if on_cpu else torch.bfloat16, "device_map": args.device}
    if args.load_4bit:
        from transformers import BitsAndBytesConfig

        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_quant_type="nf4"
        )
    model = AutoModelForCausalLM.from_pretrained(args.model, **kwargs).eval()

    results = []
    t0 = time.time()
    for i in range(0, len(rows), args.batch):
        chunk = rows[i : i + args.batch]
        texts = [
            tok.apply_chat_template(build_prompt(r["question"]), tokenize=False, add_generation_prompt=True)
            for r in chunk
        ]
        enc = tok(texts, return_tensors="pt", padding=True).to(model.device)
        torch.manual_seed(1234 + i)
        with torch.no_grad():
            out = model.generate(
                **enc,
                max_new_tokens=args.max_new_tokens,
                do_sample=True,
                temperature=0.6,
                top_p=0.95,
                pad_token_id=tok.pad_token_id or tok.eos_token_id,
            )
        for r, seq in zip(chunk, out[:, enc["input_ids"].shape[1] :]):
            n_tok = int((seq != tok.pad_token_id).sum())
            raw = tok.decode(seq, skip_special_tokens=True)
            pred = extract_answer(raw)
            results.append(
                {
                    "expected": r["answer"],
                    "predicted": pred,
                    "correct": check(pred, r["answer"], args.verifier, args.tol),
                    "valid_format": has_valid_format(raw) or has_valid_format("<think>" + raw),
                    "truncated": n_tok >= args.max_new_tokens,
                    "tokens": n_tok,
                    "branches": r.get("branches", {}),
                    "raw_tail": raw[-400:],
                }
            )
        print(f"  {len(results)}/{len(rows)} done ({time.time() - t0:.0f}s)", flush=True)

    n = len(results)
    summary = {
        "model": args.model + (" (nf4)" if args.load_4bit else "") + (" [cpu fp32]" if on_cpu else ""),
        "data": args.data,
        "n": n,
        "pass@1": round(sum(r["correct"] for r in results) / n, 3),
        "answer_extracted": round(sum(r["predicted"] is not None for r in results) / n, 3),
        "valid_format": round(sum(r["valid_format"] for r in results) / n, 3),
        "truncated": round(sum(r["truncated"] for r in results) / n, 3),
        "mean_tokens": round(sum(r["tokens"] for r in results) / n),
        "max_new_tokens": args.max_new_tokens,
        "seconds": round(time.time() - t0),
    }
    print(json.dumps(summary, indent=1))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
