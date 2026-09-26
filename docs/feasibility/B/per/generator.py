"""PER (recreational boating licence) navigation arithmetic (feasibility prototype, Agent B).

Only the text-solvable part of RD 875/2014 UT10-UT11 (see research.md): no chart plotting,
no wind or current. Conventions: E positive, W negative; Ct = dm + delta; Rv = Ra + Ct.

    T1 true_course      Rv from Ra, dm and delta (wrap to 000-359)
    T2 compass_course   Ra from Rv, dm and delta (inverse)
    T3 declination      dm for this year from the chart value and the annual change,
                        rounded to the nearest 0.5 degree (sign = E/W)
    T4 eta              arrival clock time from departure time, distance and speed
    OOD chained         declination update, then Rv (two steps; never in train)

    uv run python docs/feasibility/B/per/generator.py --n 20 --split test
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
sys.path.insert(0, str(HERE.parent / "common"))

from harness import report  # noqa: E402

from rlm.generate_problems import ProblemGenerator  # noqa: E402


def ew(deg: float) -> str:
    """Exam spelling: 3,5° W / 2° E."""
    s = f"{abs(deg):g}".replace(".", ",")
    return f"{s}° {'E' if deg >= 0 else 'W'}"


def dm_str(minutes: int) -> str:
    m = abs(minutes)
    return f"{m // 60}° {m % 60:02d}' {'E' if minutes >= 0 else 'W'}"


def round_half_deg(x: float) -> float:
    return math.floor(x * 2 + 0.5) / 2


class PerGenerator(ProblemGenerator):
    name = "per_navigation"

    def sample_params(self, rng: random.Random, split: str) -> dict[str, Any]:
        self._k = getattr(self, "_k", -1) + 1
        t = "chained" if split == "ood" else ["true_course", "compass_course", "declination", "eta"][self._k % 4]
        p: dict[str, Any] = {"type": t}
        if t in ("true_course", "compass_course", "chained"):
            # 30 % of courses near north, so wrapping past 000/360 is not a <1 % branch
            course = rng.randint(0, 359) if rng.random() > 0.3 else (rng.randint(-15, 15) % 360)
            p.update(course=course, delta=rng.choice([-1, 1]) * rng.randint(0, 8))
        if t in ("true_course", "compass_course"):
            p["dm"] = rng.choice([-1, 1]) * rng.randint(0, 12) / 2  # half degrees
        if t in ("declination", "chained"):
            while True:
                chart_year = rng.randint(1985, 2020)
                year = rng.randint(2024, 2027)
                dm0 = rng.choice([-1, 1]) * rng.randint(0, 9 * 60)  # minutes
                annual = rng.choice([-1, 1]) * rng.randint(3, 10)  # minutes/year, usually E in Spain
                now = (dm0 + annual * (year - chart_year)) / 60
                if abs(now * 2 - round(now * 2)) != 0.5:  # avoid .25/.75 ties
                    break
            p.update(chart_year=chart_year, year=year, dm0=dm0, annual=annual)
        if t == "eta":
            dep = rng.randint(6 * 60, 20 * 60) if rng.random() > 0.2 else rng.randint(21 * 60, 23 * 60 + 59)
            p.update(dep=dep, dist=rng.randint(4, 60) / 2 * 1.0,
                     speed=rng.choice([4, 5, 6, 7.5, 8, 10, 12, 15, 18]))
        return p

    def solve(self, p: dict[str, Any]) -> tuple[str, dict[str, str]]:
        t = p["type"]
        b = {"type": t}
        if t == "eta":
            minutes = round(p["dist"] / p["speed"] * 60)
            arr = p["dep"] + minutes
            b.update(crosses_midnight=str(arr >= 1440), non_integer_hours=str(minutes % 60 != 0))
            arr %= 1440
            return f"{arr // 60:02d}:{arr % 60:02d}", b
        if t in ("declination", "chained"):
            dm = round_half_deg((p["dm0"] + p["annual"] * (p["year"] - p["chart_year"])) / 60)
            b["sign_flip"] = str((p["dm0"] > 0) != (dm > 0) and dm != 0)
            if t == "declination":
                return f"{dm:g}", b
        else:
            dm = p["dm"]
        ct = dm + p["delta"]
        if t == "compass_course":
            out = (p["course"] - ct) % 360
        else:
            out = (p["course"] + ct) % 360
        b["wraps"] = str(not 0 <= (p["course"] + (ct if t != "compass_course" else -ct)) < 360)
        b["signs_opposite"] = str(dm * p["delta"] < 0)
        return f"{round(out):03d}" if out == int(out) else f"{out:05.1f}", b

    def render(self, p: dict[str, Any], rng: random.Random) -> tuple[str, int]:
        t = p["type"]
        conv = "Criterio: E positivo, W negativo; Ct = dm + Δ; Rv = Ra + Ct."
        if t == "eta":
            h, m = divmod(p["dep"], 60)
            d, v = str(p["dist"]).replace(".", ",").removesuffix(",0"), str(p["speed"]).replace(".", ",")
            tpl = [f"Salimos a las {h:02d}:{m:02d} (hora reloj de bitácora) hacia un punto a {d} millas, "
                   f"navegando a {v} nudos sin viento ni corriente. ¿Hora de llegada (HH:MM, redondeando al minuto)?",
                   f"Distancia {d} M, velocidad {v} nudos, hora de salida {h:02d}:{m:02d}. Calcula la hora "
                   f"estimada de llegada en formato HH:MM.",
                   f"A {v} kn, ¿a qué hora llegamos si zarpamos a las {h:02d}:{m:02d} y la distancia es {d} millas? "
                   f"Da HH:MM."]
        elif t == "declination":
            tpl = [f"La carta indica declinación magnética {dm_str(p['dm0'])} en {p['chart_year']}, con variación "
                   f"anual {abs(p['annual'])}' {'E' if p['annual'] > 0 else 'W'}. ¿Declinación en {p['year']}, "
                   f"redondeada al medio grado? Responde con signo (E positivo, W negativo).",
                   f"dm {p['chart_year']}: {dm_str(p['dm0'])}; decremento/incremento anual "
                   f"{abs(p['annual'])}' {'E' if p['annual'] > 0 else 'W'}. Actualiza la dm a {p['year']} "
                   f"(al 0,5° más próximo; E +, W −).",
                   f"En la rosa de la carta: '{dm_str(p['dm0'])} {p['chart_year']} "
                   f"({abs(p['annual'])}' {'E' if p['annual'] > 0 else 'W'})'. ¿Qué declinación usamos en "
                   f"{p['year']}? Medio grado; E positivo."]
        else:
            delta = f"{abs(p['delta'])}°({'+' if p['delta'] >= 0 else '-'})"
            if t == "chained":
                dm_txt = (f"declinación de la carta {dm_str(p['dm0'])} en {p['chart_year']} con variación anual "
                          f"{abs(p['annual'])}' {'E' if p['annual'] > 0 else 'W'} (estamos en {p['year']}; "
                          f"redondea la dm al medio grado)")
            else:
                dm_txt = f"declinación {ew(p['dm'])}"
            asked, given = ("rumbo verdadero", "rumbo de aguja") if t != "compass_course" else (
                "rumbo de aguja", "rumbo verdadero")
            tpl = [f"{conv} Navegamos con {given} {p['course']:03d}°, {dm_txt} y desvío {delta}. "
                   f"¿Cuál es el {asked}? Responde en grados (000-359).",
                   f"{conv} Datos: {given} = {p['course']:03d}°; {dm_txt}; Δ = {delta}. Calcula el {asked}.",
                   f"{conv} Queremos saber el {asked}. Tenemos {dm_txt}, desvío de la aguja {delta} y "
                   f"{given} {p['course']:03d}°."]
        i = rng.randrange(len(tpl))
        return tpl[i], i + 10 * ["true_course", "compass_course", "declination", "eta", "chained"].index(t)


def is_correct(predicted: str | None, expected: str) -> bool:
    if predicted is None:
        return False
    p = predicted.replace("−", "-").replace("º", "").replace("°", "").strip().strip("*`. ")
    if ":" in expected:
        m = re.fullmatch(r"(\d{1,2})[:h.](\d{2})", p)
        return bool(m) and f"{int(m[1]):02d}:{m[2]}" == expected
    p = p.replace(",", ".")
    m = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)\s*([EW])?", p.upper())
    if not m:
        return False
    val = float(m[1]) * (-1 if m[2] == "W" and not m[1].startswith("-") else 1)
    return abs(val - float(expected)) < 1e-6


EDGE_CASES = [("045", "045", True), ("45", "045", True), ("045°", "045", True), ("45º", "045", True),
              ("-3.5", "-3.5", True), ("3,5 W", "-3.5", True), ("3.5", "-3.5", False),
              ("3,5° E", "3.5", True), ("09:05", "09:05", True), ("9:05", "09:05", True),
              ("9h05", "09:05", True), ("09:5", "09:05", False), ("045 o 046", "045", False),
              (None, "000", False), ("360", "000", False)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--split", default="test")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    for pred, exp, ok in EDGE_CASES:
        assert is_correct(pred, exp) == ok, (pred, exp, ok)
    gen = PerGenerator()
    # Oracle: research.md worked example 6°40'W (1992), 8'E/yr, 23 years -> 3°36'W -> -3.5
    assert gen.solve({"type": "declination", "dm0": -400, "annual": 8, "chart_year": 1992,
                      "year": 2015})[0] == "-3.5"
    problems = gen.generate(args.n, args.split, args.seed)
    out = Path(args.out or HERE / f"problems_{args.split}.jsonl")
    print(json.dumps(report(problems, out, args.split), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
