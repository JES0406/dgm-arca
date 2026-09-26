"""Is there anything for a pipeline-choosing policy to learn? Four numbers on generated captchas.

- raw:        OCR on the untouched image (empty pipeline). If ~100 %, the task is trivial.
- best_fixed: the single pipeline of the grid with the best accuracy over all images
              (the "why not a lookup table?" baseline).
- random:     mean accuracy of a pipeline drawn uniformly from the grid (untrained policy proxy).
- oracle:     fraction of images solved by at least one pipeline in the grid (ceiling of a
              per-image policy restricted to the grid). If ~0 %, the reward is always 0.
Headroom for learning = oracle - best_fixed.

    uv run --with rapidocr-onnxruntime --with opencv-python-headless \
        python docs/feasibility/A/captcha/headroom.py --split test --n 100
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).parent))

from pipeline import verify  # noqa: E402

DENOISE = [[], [{"op": "median", "k": 3}], [{"op": "median", "k": 5}], [{"op": "gaussian", "k": 3}]]
LINES = [[], [{"op": "remove_lines", "length": 25}]]
BINAR = [[], [{"op": "otsu"}], [{"op": "adaptive", "block": 21, "c": 10}]]
MORPH = [[], [{"op": "open", "k": 2}], [{"op": "close", "k": 2}]]
SCALE = [[], [{"op": "upscale", "f": 2}]]
GRID = [a + b + c + d + e for a, b, c, d, e in itertools.product(DENOISE, LINES, BINAR, MORPH, SCALE)]


def solve_image(r: dict) -> list[int]:
    """Indices of the grid pipelines that make this captcha readable."""
    img = cv2.imread(r["image"], cv2.IMREAD_GRAYSCALE)
    return [j for j, pipe in enumerate(GRID)
            if verify(img, json.dumps(pipe), r["answer"], r["params"]["kind"]).ok]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--data", type=Path, default=Path(__file__).parent / "data")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    rows = [json.loads(line) for line in (args.data / f"{args.split}.jsonl").open()][: args.n]
    t0 = time.time()
    with Pool(args.workers) as pool:
        hits_per_image = pool.map(solve_image, rows, chunksize=1)
    solved_by = defaultdict(set)  # pipeline index -> image indices
    per_image = []
    for i, (r, hits) in enumerate(zip(rows, hits_per_image)):
        for j in hits:
            solved_by[j].add(i)
        per_image.append({"answer": r["answer"], "kind": r["params"]["kind"], "n_solving": len(hits),
                          "raw_ok": 0 in hits, "solving": hits, "recipe": {k: r["params"][k] for k in
                                                          ("rotation", "warp", "lines", "noise", "blur", "bg")}})
    n, g = len(rows), len(GRID)
    best_j = max(range(g), key=lambda j: len(solved_by[j]))
    summary = {
        "split": args.split, "n_images": n, "grid_size": g,
        "raw": round(len(solved_by[0]) / n, 3),
        "best_fixed": round(len(solved_by[best_j]) / n, 3), "best_fixed_pipeline": GRID[best_j],
        "random": round(sum(len(s) for s in solved_by.values()) / (n * g), 3),
        "oracle": round(sum(p["n_solving"] > 0 for p in per_image) / n, 3),
        "seconds": round(time.time() - t0),
    }
    summary["headroom_oracle_minus_best_fixed"] = round(summary["oracle"] - summary["best_fixed"], 3)
    # Accuracy of the raw OCR by distortion factor: which knob breaks the captcha?
    by_factor = {}
    for k in ("rotation", "warp", "lines", "noise", "blur", "bg"):
        acc = defaultdict(list)
        for p in per_image:
            acc[str(p["recipe"][k])].append(p["n_solving"] > 0)
        by_factor[k] = {v: f"{sum(x)}/{len(x)}" for v, x in sorted(acc.items())}
    summary["oracle_by_factor"] = by_factor
    by_kind = defaultdict(list)
    for p in per_image:
        by_kind[p["kind"]].append((p["raw_ok"], p["n_solving"] > 0))
    summary["by_kind"] = {k: {"n": len(v), "raw": sum(a for a, _ in v), "oracle": sum(b for _, b in v)}
                          for k, v in by_kind.items()}
    print(json.dumps(summary, indent=1))
    if args.out:
        args.out.write_text(json.dumps({"summary": summary, "per_image": per_image}, indent=1))


if __name__ == "__main__":
    main()
