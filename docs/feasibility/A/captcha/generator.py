"""Feasibility prototype: self-generated text and math captchas for a robustness lab.

Only captchas we render ourselves; nothing here touches a third-party site.
``sample_params`` draws the text and the distortion recipe, ``render`` draws the image,
``solve`` gives the ground truth (the text, or the value of the arithmetic expression).
In phase 1 the model sees the image and answers with a preprocessing pipeline
(``pipeline.py``); the verifier runs the pipeline + OCR and compares with ``solve``.

    uv run --with rapidocr-onnxruntime --with opencv-python-headless \
        python docs/feasibility/A/captcha/generator.py --n 40
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Ambiguous glyphs (0/O, 1/l/I, 5/S, 2/Z, 8/B) are excluded from the charset (clean labels).
CHARSET = "ACDEFHJKLMNPQRTUVWXY34679"
FONTS_TRAIN = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]
FONTS_OOD = ["/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf"]
W, H = 200, 70


def sample_params(rng: random.Random, split: str) -> dict[str, Any]:
    kind = rng.choices(["text", "math"], weights=[3, 1])[0]
    if kind == "text":
        text = "".join(rng.choice(CHARSET) for _ in range(rng.randint(4, 6)))
    else:
        a, b = rng.randint(1, 19), rng.randint(1, 9)
        op = rng.choice("+-x")
        text = f"{a}{op}{b}="
    ood = split == "ood"
    return {
        "kind": kind, "text": text,
        "font": rng.choice(FONTS_OOD if ood else FONTS_TRAIN), "size": rng.randint(30, 38),
        "rotation": rng.choice([0, 5, 12, 20]),               # max per-char rotation, degrees
        "warp": rng.choice([0.0, 2.0, 4.0]) + (3.0 if ood else 0.0),  # sine warp amplitude, px
        "lines": rng.choice([0, 0, 1, 3, 5]),
        "noise": rng.choice([0.0, 0.0, 0.03, 0.08]),          # salt-and-pepper density
        "blur": rng.choice([0.0, 0.0, 0.8, 1.4]),
        "bg": rng.choice(["flat", "flat", "gradient", "speckle"]),
        "seed": rng.randrange(10**9),
    }


def solve(params: dict[str, Any]) -> str:
    if params["kind"] == "text":
        return params["text"]
    return str(eval_math(params["text"]))


def eval_math(text: str) -> int | None:
    """Value of 'a<op>b=' with op in + - x; None if the string is not of that shape (e.g. OCR noise)."""
    import re

    m = re.fullmatch(r"(\d{1,2})([+\-xX*])(\d{1,2})=?", text.replace(" ", ""))
    if not m:
        return None
    a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
    return a + b if op == "+" else a - b if op == "-" else a * b


def render(params: dict[str, Any]) -> Image.Image:
    rng = random.Random(params["seed"])
    img = Image.new("L", (W, H), 235)
    if params["bg"] == "gradient":
        arr = np.tile(np.linspace(170, 250, W, dtype=np.uint8), (H, 1))
        img = Image.fromarray(arr)
    elif params["bg"] == "speckle":
        arr = np.clip(np.random.default_rng(params["seed"]).normal(215, 25, (H, W)), 0, 255).astype(np.uint8)
        img = Image.fromarray(arr)
    font = ImageFont.truetype(params["font"], params["size"])
    x = 10
    for ch in params["text"]:
        tile = Image.new("L", (params["size"] + 12, params["size"] + 16), 0)
        ImageDraw.Draw(tile).text((6, 2), ch, fill=255, font=font)
        tile = tile.rotate(rng.uniform(-params["rotation"], params["rotation"]), resample=Image.BICUBIC, expand=False)
        ink = rng.randint(10, 70)
        img.paste(Image.new("L", tile.size, ink), (x, rng.randint(4, 14)), tile)
        x += int(params["size"] * 0.62) + rng.randint(-2, 3)
    if params["warp"]:
        arr = np.array(img)
        out = np.empty_like(arr)
        phase = rng.uniform(0, 2 * math.pi)
        for col in range(W):
            out[:, col] = np.roll(arr[:, col], int(params["warp"] * math.sin(2 * math.pi * col / 60 + phase)))
        img = Image.fromarray(out)
    draw = ImageDraw.Draw(img)
    for _ in range(params["lines"]):
        draw.line([(rng.randint(0, 40), rng.randint(0, H)), (rng.randint(W - 40, W), rng.randint(0, H))],
                  fill=rng.randint(20, 90), width=rng.choice([1, 2]))
    if params["noise"]:
        arr = np.array(img)
        mask = np.random.default_rng(params["seed"] + 1).random(arr.shape)
        arr[mask < params["noise"] / 2] = 0
        arr[mask > 1 - params["noise"] / 2] = 255
        img = Image.fromarray(arr)
    if params["blur"]:
        img = img.filter(ImageFilter.GaussianBlur(params["blur"]))
    return img


def generate(n: int, split: str, seed: int, out: Path) -> list[dict[str, Any]]:
    rng = random.Random(f"{seed}-{split}")
    seen, rows = set(), []
    (out / split).mkdir(parents=True, exist_ok=True)
    while len(rows) < n:
        p = sample_params(rng, split)
        key = hashlib.sha1(json.dumps(p, sort_keys=True).encode()).hexdigest()[:12]
        if key in seen:
            continue
        seen.add(key)
        path = out / split / f"{key}.png"
        render(p).save(path)
        rows.append({"image": str(path), "answer": solve(p), "params": p, "param_hash": key, "split": split,
                     "question": "Propón el pipeline de preprocesado que hace legible este captcha.",
                     "label_source": "generator"})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "data")
    args = ap.parse_args()
    hashes, stats = {}, {}
    for split in ("train", "test", "ood"):
        rows = generate(args.n, split, args.seed, args.out)
        hashes[split] = {r["param_hash"] for r in rows}
        with (args.out / f"{split}.jsonl").open("w") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        stats[split] = {k: dict(Counter(str(r["params"][k]) for r in rows))
                        for k in ("kind", "rotation", "warp", "lines", "noise", "blur", "bg")}
        stats[split]["font"] = dict(Counter(Path(r["params"]["font"]).stem for r in rows))
    print(json.dumps({"overlap": {"train&test": len(hashes["train"] & hashes["test"]),
                                  "train&ood": len(hashes["train"] & hashes["ood"])}, "stats": stats}, indent=1))


if __name__ == "__main__":
    main()
