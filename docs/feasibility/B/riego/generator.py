"""FAO-56 irrigation problems (feasibility prototype, Agent B).

Crop tables are the FAO-56 values verified in research.md (Table 11 stage lengths, Table 12
Kc, Table 22 p). Four types, one generator, ``solve`` is the verifier:

    T1 kc          Kc on day d after sowing (Eq. 66: flat in initial/mid, linear in dev/late)
    T2 net_week    weekly net need: sum(Kc*ETo) - 0.8*rain (effective rain, MAPA fixed-%),
                   floored at 0, in mm (= L/m2), one decimal
    T3 drip_min    minutes per day of drip for a plot: gross = net/Ea, t = gross*area/(n*q)
    T4 raw         readily available water RAW = p * 1000 (thetaFC - thetaWP) Zr, mm

Crops tomato, lettuce, pepper, potato, grape in train/test; maize and olive are held out
for OOD.

    uv run python docs/feasibility/B/riego/generator.py --n 20 --split test
"""

from __future__ import annotations

import argparse
import hashlib
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

# name: (Lini, Ldev, Lmid, Llate), (Kc_ini, Kc_mid, Kc_end), p      [FAO-56 T11/T12/T22]
CROPS = {
    "tomate": ((30, 40, 45, 30), (0.60, 1.15, 0.80), 0.40),
    "lechuga": ((20, 30, 15, 10), (0.70, 1.00, 0.95), 0.30),
    "pimiento": ((25, 35, 40, 20), (0.60, 1.05, 0.90), 0.30),
    "patata": ((30, 35, 50, 30), (0.50, 1.15, 0.75), 0.35),
    "viña de vinificación": ((30, 60, 40, 80), (0.30, 0.70, 0.45), 0.45),
    "maíz": ((30, 40, 50, 30), (0.30, 1.20, 0.35), 0.55),       # OOD
    "olivo": ((30, 90, 60, 90), (0.65, 0.70, 0.70), 0.65),      # OOD
}
TRAIN_CROPS = ["tomate", "lechuga", "pimiento", "patata", "viña de vinificación"]
OOD_CROPS = ["maíz", "olivo"]
EFFICIENCY = {"goteo": 0.90, "aspersión": 0.80}
SOILS = {"arenoso": (0.12, 0.05), "franco": (0.28, 0.12), "arcilloso": (0.38, 0.22)}


def kc_on(crop: str, day: int) -> tuple[float, str]:
    (li, ld, lm, ll), (ki, km, ke), _ = CROPS[crop]
    if day <= li:
        return ki, "initial"
    if day <= li + ld:
        return ki + (day - li) / ld * (km - ki), "development"
    if day <= li + ld + lm:
        return km, "mid"
    return km + (day - li - ld - lm) / ll * (ke - km), "late"


def stage_text(crop: str) -> str:
    (li, ld, lm, ll), (ki, km, ke), _ = CROPS[crop]
    c = lambda x: f"{x:.2f}".replace(".", ",")  # noqa: E731
    return (f"etapas (días) inicial {li}, desarrollo {ld}, media {lm}, final {ll}; "
            f"Kc inicial {c(ki)}, Kc medio {c(km)}, Kc final {c(ke)}")


RULES = ("Reglas FAO-56: Kc constante en la etapa inicial y en la media; en desarrollo y en la final varía "
         "linealmente entre los valores de las etapas contiguas. ETc = Kc × ETo. Lluvia efectiva = 80 % "
         "de la lluvia. Necesidad neta = ETc − lluvia efectiva (mínimo 0). 1 mm = 1 L/m².")


class RiegoGenerator(ProblemGenerator):
    name = "fao56_irrigation"

    def sample_params(self, rng: random.Random, split: str) -> dict[str, Any]:
        """Hash-partitioned: a parameter set belongs to test iff sha1(params) % 10 == 0, so
        train and test can never share a problem even when a type's space is small (the Kc
        type has only ~5 crops x ~140 days; independent sampling gave train∩test = 8/20)."""
        while True:
            params = self._sample(rng, split)
            if split == "ood":
                return params
            in_test = int(hashlib.sha1(self.key(params).encode()).hexdigest(), 16) % 10 == 0
            if in_test == (split == "test"):
                return params

    def _sample(self, rng: random.Random, split: str) -> dict[str, Any]:
        self._k = getattr(self, "_k", -1) + 1
        t = ["kc", "net_week", "drip_min", "raw"][self._k % 4]
        crop = rng.choice(OOD_CROPS if split == "ood" else TRAIN_CROPS)
        total = sum(CROPS[crop][0])
        p: dict[str, Any] = {"type": t, "crop": crop}
        if t in ("kc", "net_week", "drip_min"):
            p["day"] = rng.randint(1, total - 7)
        if t in ("net_week", "drip_min"):
            p["eto"] = [rng.randint(15, 75) / 10 for _ in range(7)]
            p["rain"] = [0.0] * 7
            for _ in range(rng.choice([0, 0, 1, 2])):
                p["rain"][rng.randrange(7)] = rng.randint(2, 250) / 10
        if t == "drip_min":
            p.update(area=rng.choice([10, 20, 25, 40, 50, 100]), emitters=rng.choice([10, 20, 40, 60, 100]),
                     q=rng.choice([1.6, 2.0, 4.0]), system="goteo")
        if t == "raw":
            soil = rng.choice(list(SOILS))
            fc, wp = SOILS[soil]
            p.update(soil=soil, zr=rng.randint(6, 30) * 0.05, fc=round(fc + rng.randint(-4, 4) / 100, 2),
                     wp=round(wp + rng.randint(-3, 3) / 100, 2))
        return p

    def _net(self, p: dict[str, Any]) -> tuple[float, dict[str, str]]:
        etc, stages = 0.0, set()
        for i, eto in enumerate(p["eto"]):
            kc, st = kc_on(p["crop"], p["day"] + i)
            etc += round(kc, 2) * eto
            stages.add(st)
        net = max(0.0, etc - 0.8 * sum(p["rain"]))
        return net, {"stage_change_in_week": str(len(stages) > 1), "rain_cancels": str(net == 0),
                     "stage": sorted(stages)[0]}

    def solve(self, p: dict[str, Any]) -> tuple[str, dict[str, str]]:
        t = p["type"]
        b = {"type": t, "crop_group": "tree/vine" if p["crop"] in ("olivo", "viña de vinificación") else "annual"}
        if t == "kc":
            kc, st = kc_on(p["crop"], p["day"])
            b["stage"] = st
            return f"{kc:.2f}", b
        if t == "raw":
            fc, wp = p["fc"], p["wp"]
            raw = CROPS[p["crop"]][2] * 1000 * (fc - wp) * p["zr"]
            b["soil"] = p["soil"]
            return f"{raw:.1f}", b
        net, extra = self._net(p)
        b.update(extra)
        if t == "net_week":
            return f"{net:.1f}", b
        gross_l = net / EFFICIENCY[p["system"]] / 7 * p["area"]  # litres per day for the plot
        minutes = math.ceil(gross_l / (p["emitters"] * p["q"]) * 60 - 1e-9)
        return str(minutes), b

    def render(self, p: dict[str, Any], rng: random.Random) -> tuple[str, int]:
        t, crop = p["type"], p["crop"]
        c = lambda x: f"{x:g}".replace(".", ",")  # noqa: E731
        if t == "raw":
            fc, wp = p["fc"], p["wp"]
            pp = CROPS[crop][2]
            tpl = [f"Suelo {p['soil']}: capacidad de campo {c(fc)} m³/m³, punto de marchitez {c(wp)} m³/m³. "
                   f"Raíces del {crop} a {c(p['zr'])} m, fracción de agotamiento p = {c(pp)}. ¿Agua fácilmente "
                   f"disponible (RAW) en mm, con un decimal? RAW = p·1000·(θCC − θPM)·Zr.",
                   f"Calcula la RAW (mm, un decimal) para {crop} con Zr = {c(p['zr'])} m y p = {c(pp)} en un "
                   f"suelo con θCC = {c(fc)} y θPM = {c(wp)}. Usa RAW = p × 1000 × (θCC − θPM) × Zr."]
        else:
            head = f"{RULES} {crop.capitalize()}: {stage_text(crop)}."
            if t == "kc":
                tpl = [f"{head} ¿Qué Kc tiene el cultivo el día {p['day']} desde la siembra? Dos decimales.",
                       f"{head} Estamos en el día {p['day']} del ciclo. Calcula el Kc (dos decimales)."]
            else:
                eto = ", ".join(c(x) for x in p["eto"])
                rain = ", ".join(c(x) for x in p["rain"])
                week = (f"Semana que empieza el día {p['day']} del ciclo. ETo diaria (mm): {eto}. Lluvia diaria "
                        f"(mm): {rain}. Usa el Kc de cada día redondeado a dos decimales.")
                if t == "net_week":
                    tpl = [f"{head} {week} ¿Necesidad neta de riego de la semana en mm (un decimal)?",
                           f"{head} {week} Calcula cuántos L/m² netos hay que aportar esta semana (un decimal)."]
                else:
                    tpl = [f"{head} {week} Riego por goteo (eficiencia 0,9) en {p['area']} m² con {p['emitters']} "
                           f"goteros de {c(p['q'])} L/h. Repartiendo la necesidad bruta semanal por igual en 7 días, "
                           f"¿cuántos minutos al día hay que regar? Redondea hacia arriba al minuto.",
                           f"{head} {week} Tengo {p['emitters']} goteros de {c(p['q'])} L/h en {p['area']} m², "
                           f"eficiencia del goteo 0,9. Minutos de riego diarios (entero, hacia arriba), igual "
                           f"todos los días de la semana."]
        i = rng.randrange(len(tpl))
        return tpl[i], i + 10 * ["kc", "net_week", "drip_min", "raw"].index(t)


def is_correct(predicted: str | None, expected: str) -> bool:
    """One number; tolerance half a unit of the last digit the task asks for."""
    if predicted is None:
        return False
    p = re.sub(r"\s*(mm|min(utos)?|l/m²|l/m2)\.?$", "", predicted.strip().strip("*`. "), flags=re.I)
    if not re.fullmatch(r"-?\d+(?:[.,]\d+)?", p):
        return False
    decimals = len(expected.split(".")[1]) if "." in expected else 0
    return abs(float(p.replace(",", ".")) - float(expected)) < 0.5 * 10 ** -decimals + 1e-9


EDGE_CASES = [("0.84", "0.84", True), ("0,84", "0.84", True), ("0.8", "0.84", False),
              ("23.4 mm", "23.4", True), ("23,45", "23.4", True), ("23.5", "23.4", False),
              ("42", "42", True), ("42 minutos", "42", True), ("41.6", "42", True), ("43", "42", False),
              ("unos 42", "42", False), (None, "1.0", False)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--split", default="test")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    for pred, exp, ok in EDGE_CASES:
        assert is_correct(pred, exp) == ok, (pred, exp, ok)
    gen = RiegoGenerator()
    # Oracle: FAO-56 Example 37 (p. 168): Zr 0.8, p 0.40, thetaFC 0.32, thetaWP 0.12 -> RAW 64 mm
    assert round(0.40 * 1000 * (0.32 - 0.12) * 0.8, 1) == 64.0
    problems = gen.generate(args.n, args.split, args.seed)
    out = Path(args.out or HERE / f"problems_{args.split}.jsonl")
    print(json.dumps(report(problems, out, args.split), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
