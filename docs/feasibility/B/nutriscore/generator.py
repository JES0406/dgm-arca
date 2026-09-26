"""Nutri-Score (2023 updated algorithm) problems (feasibility prototype, Agent B).

Tables from Santé publique France, Q&A V11 (Tables 5-10, pp. 27-33), cross-checked with the
official SPF calculator xlsx (see research.md). Each cut is the value *above which* the next
point is earned. Two answer kinds, one generator, ``solve`` is the verifier:

    score   the final Nutri-Score (integer, may be negative)
    letter  the logo letter A-E

Categories: general food, cheese, red-meat product, beverage (train/test); fats, oils, nuts
and seeds are held out for the OOD split (different tables: energy from saturates and the
saturates/lipids ratio).

    uv run python docs/feasibility/B/nutriscore/generator.py --n 20 --split test
"""

from __future__ import annotations

import argparse
import json
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

ENERGY = [335 * i for i in range(1, 11)]
SATFAT = list(range(1, 11))
SUGARS = [3.4, 6.8, 10, 14, 17, 20, 24, 27, 31, 34, 37, 41, 44, 48, 51]
SALT = [round(0.2 * i, 1) for i in range(1, 21)]
PROTEIN = [2.4, 4.8, 7.2, 9.6, 12, 14, 17]
FIBRE = [3.0, 4.1, 5.2, 6.3, 7.4]
BEV_ENERGY = [30, 90, 150, 210, 240, 270, 300, 330, 360, 390]
BEV_SUGARS = [0.5, 2, 3.5, 5, 6, 7, 8, 9, 10, 11]
BEV_PROTEIN = [1.2, 1.5, 1.8, 2.1, 2.4, 2.7, 3.0]
FAT_ENERGY_SAT = [120 * i for i in range(1, 11)]
FAT_RATIO = [10, 16, 22, 28, 34, 40, 46, 52, 58, 64]  # ASSUMPTION: >=10 gives 1 point


def pts(value: float, cuts: list[float]) -> int:
    return sum(1 for c in cuts if value > c + 1e-9)


def fvl_pts(pct: float, beverage: bool) -> int:
    if beverage:
        return 6 if pct > 80 else 4 if pct > 60 else 2 if pct > 40 else 0
    return 5 if pct > 80 else 2 if pct > 60 else 1 if pct > 40 else 0


def letter(score: int, category: str) -> str:
    if category == "beverage":
        return "B" if score <= 2 else "C" if score <= 6 else "D" if score <= 9 else "E"
    if category == "fat":
        return "A" if score <= -6 else "B" if score <= 2 else "C" if score <= 10 else (
            "D" if score <= 18 else "E")
    return "A" if score <= 0 else "B" if score <= 2 else "C" if score <= 10 else (
        "D" if score <= 18 else "E")


RULES_TEXT = """Nutri-Score (algoritmo actualizado 2023). Un punto por cada umbral SUPERADO (estrictamente mayor).
Alimentos generales, quesos y productos de carne roja (por 100 g):
- Negativos N: energía kJ umbrales 335, 670, …, 3350 (cada 335; 0-10); grasas saturadas g 1, 2, …, 10 (0-10);
  azúcares g 3.4, 6.8, 10, 14, 17, 20, 24, 27, 31, 34, 37, 41, 44, 48, 51 (0-15); sal g 0.2, 0.4, …, 4.0 (cada 0.2; 0-20).
- Positivos: proteínas g 2.4, 4.8, 7.2, 9.6, 12, 14, 17 (0-7; carne roja: máximo 2); fibra g 3.0, 4.1, 5.2, 6.3, 7.4 (0-5);
  frutas/verduras/legumbres %: >40 → 1, >60 → 2, >80 → 5.
- Puntuación: si N < 11 o es queso, N − (proteínas + fibra + FVL); si no, N − (fibra + FVL).
- Letra: A ≤ 0, B 1-2, C 3-10, D 11-18, E ≥ 19.
Bebidas (por 100 mL): energía kJ 30, 90, 150, 210, 240, 270, 300, 330, 360, 390 (0-10); azúcares g 0.5, 2, 3.5, 5, 6, 7,
8, 9, 10, 11 (0-10); saturadas y sal con las tablas generales; edulcorantes +4; proteínas g 1.2, 1.5, …, 3.0 (0-7);
fibra tabla general; FVL >40 → 2, >60 → 4, >80 → 6. Puntuación siempre N − P. Letra: B ≤ 2, C 3-6, D 7-9, E ≥ 10.
Grasas, aceites, frutos secos y semillas: energía de saturadas = saturadas × 37 kJ, umbrales 120, 240, …, 1200 (0-10);
saturadas/lípidos % 10, 16, 22, …, 64 (0-10); azúcares y sal generales; proteínas no cuentan si N ≥ 7.
Letra: A ≤ −6, B −5 a 2, C 3-10, D 11-18, E ≥ 19."""

PRODUCTS = {
    "general": ["galletas", "cereales de desayuno", "pizza congelada", "yogur natural", "pan de molde",
                "crema de cacao", "hummus", "lasaña preparada", "patatas fritas de bolsa", "gazpacho"],
    "cheese": ["queso manchego curado", "queso fresco de Burgos", "queso de untar", "queso rallado"],
    "red_meat": ["hamburguesa de ternera", "chorizo", "albóndigas de cerdo", "salchichas de cerdo"],
    "beverage": ["refresco de cola", "zumo de naranja", "bebida de avena", "leche semidesnatada",
                 "té frío", "bebida isotónica"],
    "fat": ["aceite de oliva virgen extra", "mantequilla", "almendras tostadas", "crema de cacahuete"],
}


class NutriScoreGenerator(ProblemGenerator):
    name = "nutriscore_2023"

    def sample_params(self, rng: random.Random, split: str) -> dict[str, Any]:
        """Stratified by target letter (rejection sampling): uniform nutrient ranges give 57 % E
        and <1 % A, i.e. all the weight on the easy branch."""
        self._k = getattr(self, "_k", -1) + 1
        cat = "fat" if split == "ood" else ["general", "cheese", "red_meat", "beverage"][self._k % 4]
        target = rng.choice("BCDE" if cat == "beverage" else "ABCDE")
        for _ in range(400):
            params = self._sample_raw(rng, cat)
            if self.solve(params)[1]["letter"] == target:
                return params
        return params

    def _sample_raw(self, rng: random.Random, cat: str) -> dict[str, Any]:
        scale = rng.choice([0.25, 0.5, 1.0])  # healthier and less healthy profiles
        r = lambda a, b, d=1: round(rng.uniform(a, b), d)  # noqa: E731
        if cat == "beverage":
            v = dict(energy=rng.randint(0, 420), satfat=r(0, 2), sugars=r(0, 13), salt=r(0, 0.4, 2),
                     protein=r(0, 3.6), fibre=r(0, 1.5), fvl=rng.choice([0, 0, 10, 45, 70, 100]),
                     sweeteners=rng.random() < 0.3, fat=None)
        elif cat == "fat":
            fat = r(40, 100)
            v = dict(energy=rng.randint(1500, 3700), fat=fat, satfat=r(fat * 0.05, fat * 0.7),
                     sugars=r(0, 10), salt=r(0, 1.5, 2), protein=r(0, 25), fibre=r(0, 12),
                     fvl=rng.choice([0, 0, 100]), sweeteners=False)
        else:
            v = dict(energy=rng.randint(150, int(2400 * scale) + 150), satfat=r(0, 22 * scale),
                     sugars=r(0, 55 * scale), salt=r(0, 3.5 * scale, 2), protein=r(0, 30), fibre=r(0, 9),
                     fvl=rng.choice([0, 0, 0, 20, 50, 70, 90]), sweeteners=False, fat=None)
        return {"category": cat, "product": rng.choice(PRODUCTS[cat]), "ask": rng.choice(["score", "letter"]),
                **v}

    def solve(self, p: dict[str, Any]) -> tuple[str, dict[str, str]]:
        cat = p["category"]
        b = {"category": cat, "ask": p["ask"]}
        if cat == "beverage":
            n = (pts(p["energy"], BEV_ENERGY) + pts(p["sugars"], BEV_SUGARS) + pts(p["satfat"], SATFAT)
                 + pts(p["salt"], SALT) + (4 if p["sweeteners"] else 0))
            pos = pts(p["protein"], BEV_PROTEIN) + pts(p["fibre"], FIBRE) + fvl_pts(p["fvl"], True)
            score = n - pos
            b["sweeteners"] = str(p["sweeteners"])
            cat_letter = "beverage"
        elif cat == "fat":
            n = (pts(p["satfat"] * 37, FAT_ENERGY_SAT) + pts(p["sugars"], SUGARS) + pts(p["salt"], SALT)
                 + sum(1 for c in FAT_RATIO if 100 * p["satfat"] / p["fat"] >= c))
            prot = 0 if n >= 7 else pts(p["protein"], PROTEIN)
            score = n - prot - pts(p["fibre"], FIBRE) - fvl_pts(p["fvl"], False)
            b["protein_dropped"] = str(n >= 7)
            cat_letter = "fat"
        else:
            n = (pts(p["energy"], ENERGY) + pts(p["satfat"], SATFAT) + pts(p["sugars"], SUGARS)
                 + pts(p["salt"], SALT))
            prot = pts(p["protein"], PROTEIN)
            if cat == "red_meat":
                b["red_meat_cap_binds"] = str(prot > 2 and n < 11)
                prot = min(prot, 2)
            counts_protein = n < 11 or cat == "cheese"
            b["protein_counted"] = str(counts_protein)
            score = n - (prot if counts_protein else 0) - pts(p["fibre"], FIBRE) - fvl_pts(p["fvl"], False)
            cat_letter = "general"
        lt = letter(score, cat_letter)
        b["letter"] = lt
        b["n_ge_11"] = str(n >= 11)
        return (str(score) if p["ask"] == "score" else lt), b

    def render(self, p: dict[str, Any], rng: random.Random) -> tuple[str, int]:
        unit = "100 mL" if p["category"] == "beverage" else "100 g"
        c = lambda x: str(x).replace(".", ",")  # noqa: E731
        kcal = round(p["energy"] / 4.184)
        rows = [f"Valor energético {p['energy']} kJ / {kcal} kcal"]
        if p.get("fat"):
            rows.append(f"Grasas {c(p['fat'])} g")
        rows += [f"de las cuales saturadas {c(p['satfat'])} g", f"Azúcares {c(p['sugars'])} g",
                 f"Fibra alimentaria {c(p['fibre'])} g", f"Proteínas {c(p['protein'])} g",
                 f"Sal {c(p['salt'])} g"]
        rng.shuffle(rows)
        table = "; ".join(rows)
        extra = f" Contiene {p['fvl']} % de frutas, verduras y legumbres."
        if p["category"] == "beverage":
            extra += " Lleva edulcorantes." if p["sweeteners"] else " Sin edulcorantes."
        ask = ("la puntuación Nutri-Score (número entero)" if p["ask"] == "score"
               else "la letra del Nutri-Score (A-E)")
        templates = [
            f"{RULES_TEXT}\n\nProducto: {p['product']}. Información nutricional por {unit}: {table}.{extra} "
            f"Calcula {ask}.",
            f"{RULES_TEXT}\n\nEtiqueta de {p['product']} (por {unit}) — {table}.{extra} ¿Cuál es {ask}?",
            f"{RULES_TEXT}\n\nTengo un {p['product']} con estos valores por {unit}: {table}.{extra} Dime {ask}.",
            f"{RULES_TEXT}\n\n{table} (valores por {unit}; producto: {p['product']}).{extra} Necesito {ask}.",
            f"{RULES_TEXT}\n\nSoy técnico de etiquetado. Para el {p['product']} tenemos, por {unit}: {table}."
            f"{extra} Calcula {ask} según el algoritmo de 2023.",
        ]
        i = rng.randrange(len(templates))
        return templates[i], i


def is_correct(predicted: str | None, expected: str) -> bool:
    """Letter: exactly one of A-E. Score: one signed integer (Unicode minus accepted)."""
    if predicted is None:
        return False
    p = predicted.replace("−", "-").strip().strip("*`. ").upper()
    p = re.sub(r"^(NUTRI-?SCORE|LETRA|PUNTUACI[OÓ]N)\s*:?\s*", "", p)
    if expected in "ABCDE":
        return p == expected
    return bool(re.fullmatch(r"[+-]?\d+", p)) and int(p) == int(expected)


EDGE_CASES = [("C", "C", True), ("c", "C", True), ("Letra: C", "C", True), ("C o D", "C", False),
              ("-3", "-3", True), ("−3", "-3", True), ("3", "-3", False), ("+4", "4", True),
              ("4.0", "4", False), ("Nutri-Score: E", "E", True), (None, "A", False)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--split", default="test")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    for pred, exp, ok in EDGE_CASES:
        assert is_correct(pred, exp) == ok, (pred, exp, ok)
    gen = NutriScoreGenerator()
    # Oracle check against Open Food Facts' own 2023 computation for Oreo (research.md):
    # energy 2007.7 kJ, sugars 38, sat 5.4, salt 0.73, fibre 2.7 -> N = 5+11+5+3 = 24, E.
    oreo = {"category": "general", "product": "x", "ask": "score", "energy": 2007.7, "satfat": 5.4,
            "sugars": 38, "salt": 0.73, "protein": 5.0, "fibre": 2.7, "fvl": 0, "sweeteners": False,
            "fat": None}
    assert gen.solve(oreo)[0] == "24", gen.solve(oreo)
    problems = gen.generate(args.n, args.split, args.seed)
    out = Path(args.out or HERE / f"problems_{args.split}.jsonl")
    print(json.dumps(report(problems, out, args.split), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
