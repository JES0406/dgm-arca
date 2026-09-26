"""Pipeline DSL, executor and verifier for the captcha robustness lab.

The model's answer is a JSON list of ops, e.g. ``[{"op": "median", "k": 3}, {"op": "otsu"}]``.
``verify`` runs it on the image, reads the result with RapidOCR (pip-only, deterministic on
CPU) and compares with the ground truth. Invalid pipelines score 0 with a reason, never raise.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import cv2
import numpy as np

HARD_CAP_OPS = 20  # safety net; the soft length penalty lives in the GRPO reward
OPS = {
    "median": {"k": (3, 5, 7)},
    "gaussian": {"k": (3, 5)},
    "otsu": {},
    "adaptive": {"block": (11, 15, 21, 31), "c": (2, 5, 10)},
    "open": {"k": (2, 3)},
    "close": {"k": (2, 3)},
    "erode": {"k": (2, 3)},
    "dilate": {"k": (2, 3)},
    "remove_lines": {"length": (15, 25, 40)},
    "invert": {},
    "upscale": {"f": (2, 3)},
}


class PipelineError(ValueError):
    pass


def parse(answer: str) -> list[dict]:
    try:
        ops = json.loads(answer)
    except json.JSONDecodeError as exc:
        raise PipelineError(f"not JSON: {exc.msg}") from exc
    if not isinstance(ops, list):
        raise PipelineError("pipeline must be a JSON list")
    if len(ops) > HARD_CAP_OPS:
        raise PipelineError(f"more than {HARD_CAP_OPS} ops")
    for step in ops:
        if not isinstance(step, dict) or step.get("op") not in OPS:
            raise PipelineError(f"unknown op: {step!r}")
        for arg, allowed in OPS[step["op"]].items():
            if step.get(arg) not in allowed:
                raise PipelineError(f"{step['op']}.{arg} must be one of {allowed}")
    return ops


def run(img: np.ndarray, ops: list[dict]) -> np.ndarray:
    out = img.copy()
    for s in ops:
        op = s["op"]
        kernel = lambda k: cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))  # noqa: E731
        if op == "median":
            out = cv2.medianBlur(out, s["k"])
        elif op == "gaussian":
            out = cv2.GaussianBlur(out, (s["k"], s["k"]), 0)
        elif op == "otsu":
            _, out = cv2.threshold(out, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        elif op == "adaptive":
            out = cv2.adaptiveThreshold(out, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, s["block"], s["c"])
        elif op in ("open", "close", "erode", "dilate"):
            # Text is dark on light: "open" on the inverted image removes thin dark specks.
            inv = 255 - out
            inv = {"open": lambda a: cv2.morphologyEx(a, cv2.MORPH_OPEN, kernel(s["k"])),
                   "close": lambda a: cv2.morphologyEx(a, cv2.MORPH_CLOSE, kernel(s["k"])),
                   "erode": lambda a: cv2.erode(a, kernel(s["k"])),
                   "dilate": lambda a: cv2.dilate(a, kernel(s["k"]))}[op](inv)
            out = 255 - inv
        elif op == "remove_lines":
            inv = 255 - out
            horiz = cv2.morphologyEx(inv, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (s["length"], 1)))
            out = 255 - cv2.subtract(inv, horiz)
        elif op == "invert":
            out = 255 - out
        elif op == "upscale":
            out = cv2.resize(out, None, fx=s["f"], fy=s["f"], interpolation=cv2.INTER_CUBIC)
    return out


_OCR = None


def ocr(img: np.ndarray) -> str:
    global _OCR
    if _OCR is None:
        from rapidocr_onnxruntime import RapidOCR

        # One thread per process: parallelism comes from the process pool in headroom.py.
        _OCR = RapidOCR(intra_op_num_threads=1, inter_op_num_threads=1)
    bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    # A captcha is a single text line: recognition only (no detection pass), ~10x faster.
    result, _ = _OCR(bgr, use_det=False, use_cls=False, use_rec=True)
    if not result:
        return ""
    return "".join(r[0] for r in result)


def normalise(text: str) -> str:
    return re.sub(r"[^A-Z0-9+\-X=*]", "", text.upper()).replace("*", "X")


@dataclass
class Verdict:
    ok: bool
    read: str
    n_ops: int
    error: str | None = None


def verify(img: np.ndarray, answer: str, truth: str, kind: str) -> Verdict:
    """Deterministic: same image + same pipeline -> same verdict. Case-insensitive."""
    from generator import eval_math  # local import keeps this module usable standalone

    try:
        ops = parse(answer)
    except PipelineError as exc:
        return Verdict(False, "", 0, str(exc))
    read = normalise(ocr(run(img, ops)))
    if kind == "math":
        value = eval_math(read)
        return Verdict(value is not None and str(value) == truth, read, len(ops))
    return Verdict(read == truth.upper(), read, len(ops))
