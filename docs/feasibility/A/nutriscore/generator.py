"""Feasibility prototype: Nutri-Score (2023 updated algorithm) from a nutrition label.

Task: given the per-100 g (or 100 mL) values of a product and its category, compute the
Nutri-Score *score* (integer, N - P). The grade letter follows from the score; we grade the
integer because a 5-letter answer can be guessed 20 % of the time.

Tables: Santé publique France, Nutri-Score Conditions of Use (March 2025), Exhibit 1,
tables 5-10 (https://www.santepubliquefrance.fr/sites/default/files/rdd/document/march2025CoU_EN.pdf).
Cross-check oracle: Open Food Facts exposes the per-component points (`nutriscore.2023.data`).

    uv run python docs/feasibility/A/nutriscore/generator.py --n 40
"""

from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.report import run_cli  # noqa: E402
from rlm.generate_problems import ProblemGenerator  # noqa: E402

ENERGY_KJ = [335 * k for k in range(1, 11)]
SAT_FAT = list(range(1, 11))
SUGARS = [3.4, 6.8, 10, 14, 17, 20, 24, 27, 31, 34, 37, 41, 44, 48, 51]
SALT = [round(0.2 * k, 1) for k in range(1, 21)]
PROTEIN = [2.4, 4.8, 7.2, 9.6, 12, 14, 17]
FIBRE = [3.0, 4.1, 5.2, 6.3, 7.4]
BEV_ENERGY = [30, 90, 150, 210, 240, 270, 300, 330, 360, 390]
BEV_SUGARS = [0.5, 2, 3.5, 5, 6, 7, 8, 9, 10, 11]
BEV_PROTEIN = [1.2, 1.5, 1.8, 2.1, 2.4, 2.7, 3.0]
FAT_SAT_ENERGY = [120 * k for k in range(1, 11)]
FAT_RATIO = [10, 16, 22, 28, 34, 40, 46, 52, 58, 64]

RULES = """Nutri-Score (algoritmo actualizado 2023). Puntos por 100 g (o 100 mL en bebidas). Cada puntuación es el número de umbrales que el valor supera estrictamente.
ALIMENTOS GENERALES (incluye quesos y carnes rojas):
- Negativos (N): energía kJ: umbrales 335, 670, ..., 3350 (cada 335; máx. 10). Grasas saturadas g: 1, 2, ..., 10 (máx. 10). Azúcares g: 3,4; 6,8; 10; 14; 17; 20; 24; 27; 31; 34; 37; 41; 44; 48; 51 (máx. 15). Sal g: 0,2; 0,4; ...; 4,0 (cada 0,2; máx. 20).
- Positivos (P): proteínas g: 2,4; 4,8; 7,2; 9,6; 12; 14; 17 (máx. 7). Fibra g: 3,0; 4,1; 5,2; 6,3; 7,4 (máx. 5). Frutas, verduras y legumbres %: más de 40 → 1; más de 60 → 2; más de 80 → 5.
- Si N ≥ 11, las proteínas no cuentan (salvo en quesos, donde siempre cuentan). En carnes rojas, las proteínas cuentan como máximo 2 puntos.
- Letra: A ≤ 0; B 1-2; C 3-10; D 11-18; E ≥ 19.
BEBIDAS:
- Energía kJ: 30, 90, 150, 210, 240, 270, 300, 330, 360, 390 (máx. 10). Azúcares g: 0,5; 2; 3,5; 5; 6; 7; 8; 9; 10; 11 (máx. 10). Grasas saturadas y sal: como en alimentos. Edulcorantes no nutritivos: 4 puntos si los contiene.
- Proteínas g: 1,2; 1,5; 1,8; 2,1; 2,4; 2,7; 3,0 (máx. 7). Fibra: como en alimentos. Frutas/verduras/legumbres %: más de 40 → 2; más de 60 → 4; más de 80 → 6. En bebidas las proteínas siempre cuentan.
- Letra: B ≤ 2 (A solo para agua); C 3-6; D 7-9; E ≥ 10.
GRASAS, ACEITES, FRUTOS SECOS Y SEMILLAS:
- La energía se sustituye por la energía de las saturadas = grasas saturadas × 37 kJ: umbrales 120, 240, ..., 1200 (máx. 10). Las grasas saturadas se sustituyen por el porcentaje saturadas/grasas totales: 10, 16, 22, 28, 34, 40, 46, 52, 58, 64 (el valor puntúa si es igual o mayor que el umbral; máx. 10). Azúcares y sal: como en alimentos.
- Positivos como en alimentos, pero las proteínas no cuentan si N ≥ 7.
- Letra: A ≤ -6; B -5 a 2; C 3-10; D 11-18; E ≥ 19.
Puntuación = N - P. Da la puntuación (un número entero)."""


def pts(value: float, thresholds: list[float]) -> int:
    return sum(value > t for t in thresholds)


def fvl_points(pct: float, beverage: bool) -> int:
    steps = (2, 4, 6) if beverage else (1, 2, 5)
    return steps[2] if pct > 80 else steps[1] if pct > 60 else steps[0] if pct > 40 else 0


def grade(score: int, category: str) -> str:
    if category == "beverage":
        return "B" if score <= 2 else "C" if score <= 6 else "D" if score <= 9 else "E"
    if category == "fat":
        return "A" if score <= -6 else "B" if score <= 2 else "C" if score <= 10 else "D" if score <= 18 else "E"
    return "A" if score <= 0 else "B" if score <= 2 else "C" if score <= 10 else "D" if score <= 18 else "E"


def score(p: dict[str, Any]) -> tuple[int, dict[str, str]]:
    cat = p["category"]
    if cat == "beverage":
        n = (pts(p["energy_kj"], BEV_ENERGY) + pts(p["sugars"], BEV_SUGARS) + pts(p["sat_fat"], SAT_FAT)
             + pts(p["salt"], SALT) + (4 if p["sweeteners"] else 0))
        prot = pts(p["protein"], BEV_PROTEIN)
        protein_rule = "always"
    else:
        if cat == "fat":
            ratio = 100 * p["sat_fat"] / p["fat"] if p["fat"] else 0.0
            n = (pts(p["sat_fat"] * 37, FAT_SAT_ENERGY) + sum(ratio >= t for t in FAT_RATIO)
                 + pts(p["sugars"], SUGARS) + pts(p["salt"], SALT))
            limit = 7
        else:
            n = pts(p["energy_kj"], ENERGY_KJ) + pts(p["sat_fat"], SAT_FAT) + pts(p["sugars"], SUGARS) + pts(p["salt"], SALT)
            limit = 11
        prot = pts(p["protein"], PROTEIN)
        if cat == "red_meat":
            prot = min(prot, 2)
        if n >= limit and cat != "cheese":
            prot, protein_rule = 0, "dropped"
        else:
            protein_rule = "counted"
    positive = prot + pts(p["fibre"], FIBRE) + fvl_points(p["fvl_pct"], cat == "beverage")
    s = n - positive
    return s, {"category": cat, "grade": grade(s, cat), "protein_rule": protein_rule,
               "n_ge_11": str(n >= 11)}


# (category, label, ranges) — plausible per-100 g ranges; kJ derived from macros when possible.
PRODUCTS = {
    "general": ["galletas", "cereales de desayuno", "pan de molde", "pizza congelada", "yogur natural",
                "hummus", "croquetas", "barrita de cereales", "gazpacho", "lentejas cocidas"],
    "cheese": ["queso manchego curado", "queso fresco", "queso de cabra"],
    "red_meat": ["hamburguesa de ternera", "chorizo", "lomo embuchado"],
    "beverage": ["refresco de cola", "zumo de naranja", "bebida de avena", "batido de chocolate", "té frío"],
    "fat": ["aceite de oliva virgen extra", "mantequilla", "crema de cacahuete", "almendras tostadas", "margarina"],
}


class NutriScoreGenerator(ProblemGenerator):
    name = "nutriscore_2023"

    def sample_params(self, rng: random.Random, split: str) -> dict[str, Any]:
        cat = "fat" if split == "ood" else rng.choices(["general", "cheese", "red_meat", "beverage"],
                                                        weights=[6, 2, 2, 3])[0]
        u = rng.uniform
        if cat == "beverage":
            sugars = round(u(0, 13), 1)
            p = {"energy_kj": round(sugars * 17 + u(0, 120)), "sugars": sugars, "sat_fat": round(u(0, 2.5), 1),
                 "salt": round(u(0, 0.3), 2), "protein": round(u(0, 3.6), 1), "fibre": round(u(0, 1.5), 1),
                 "fvl_pct": rng.choice([0, 0, 10, 45, 65, 100]), "sweeteners": rng.random() < 0.3, "fat": None}
        elif cat == "fat":
            fat = round(u(40, 100), 1)
            p = {"energy_kj": round(fat * 37 + u(0, 400)), "fat": fat, "sat_fat": round(fat * u(0.08, 0.68), 1),
                 "sugars": round(u(0, 8), 1), "salt": round(u(0, 1.8), 2), "protein": round(u(0, 26), 1),
                 "fibre": round(u(0, 10), 1), "fvl_pct": rng.choice([0, 0, 50, 90, 100]), "sweeteners": False}
        else:
            fat = round(0.5 + 30 * rng.random() ** 1.5, 1)
            sugars = round((40 if cat == "general" else 3) * rng.random() ** 2, 1)
            protein = round(u(1, 30 if cat != "general" else 15), 1)
            carbs = u(0, 70) if cat == "general" else u(0, 4)
            p = {"fat": fat, "sat_fat": round(fat * u(0.1, 0.7), 1), "sugars": sugars,
                 "energy_kj": round(37 * fat + 17 * (carbs + sugars) + 17 * protein),
                 "salt": round(3.0 * rng.random() ** 2, 2), "protein": protein, "fibre": round(u(0, 9 if cat == "general" else 0.5), 1),
                 "fvl_pct": rng.choice([0, 0, 0, 30, 50, 70, 90]) if cat == "general" else 0, "sweeteners": False}
        p["category"] = cat
        p["product"] = rng.choice(PRODUCTS[cat])
        return p

    def solve(self, params: dict[str, Any]) -> tuple[str, dict[str, str]]:
        s, branches = score(params)
        return str(s), branches

    def render(self, params: dict[str, Any], rng: random.Random) -> tuple[str, int]:
        p = params
        unit = "100 mL" if p["category"] == "beverage" else "100 g"
        f = lambda x: str(x).replace(".", ",")  # noqa: E731
        items = [f"energía {p['energy_kj']} kJ", f"grasas saturadas {f(p['sat_fat'])} g", f"azúcares {f(p['sugars'])} g",
                 f"sal {f(p['salt'])} g", f"proteínas {f(p['protein'])} g", f"fibra {f(p['fibre'])} g",
                 f"frutas, verduras y legumbres {p['fvl_pct']} %"]
        if p.get("fat") is not None:
            items.insert(1, f"grasas {f(p['fat'])} g")
        if p["category"] == "beverage":
            items.append("contiene edulcorantes" if p["sweeteners"] else "sin edulcorantes")
        rng.shuffle(items)
        label = ", ".join(items)
        cat_txt = {"general": "alimento general", "cheese": "queso", "red_meat": "producto de carne roja",
                   "beverage": "bebida", "fat": "grasa, aceite, fruto seco o semilla"}[p["category"]]
        templates = [
            f"Etiqueta de {p['product']} ({cat_txt}), por {unit}: {label}. Calcula la puntuación Nutri-Score.",
            f"Tengo en la mano un envase de {p['product']}. La tabla nutricional dice, por {unit}: {label}. "
            f"¿Qué puntuación Nutri-Score le corresponde? Es un {cat_txt}.",
            f"Categoría: {cat_txt}. Producto: {p['product']}. Valores por {unit}: {label}. Puntuación Nutri-Score (N - P):",
            f"Quiero comprobar el Nutri-Score que imprime el fabricante de {p['product']}. Valores por {unit}: {label}. "
            f"Trátalo como {cat_txt} y dame la puntuación numérica.",
        ]
        tid = rng.randrange(len(templates))
        return templates[tid], tid


if __name__ == "__main__":
    # Oracle check against Open Food Facts' 2023 breakdown for barcode 8480000160164 (tomate triturado):
    # energy 115.9 kJ -> 0, sugars 4.7 -> 1, sat fat -> 0, salt 0.5 -> 2, FVL 74.5 % -> 2; score 1, grade B.
    tomato = {"category": "general", "energy_kj": 115.9, "sugars": 4.7, "sat_fat": 0.0, "salt": 0.5,
              "protein": 1.5, "fibre": 0.0, "fvl_pct": 74.5, "fat": 0.2}
    assert score(tomato)[0] == 1 and score(tomato)[1]["grade"] == "B"
    run_cli(NutriScoreGenerator(), Path(__file__).parent / "data", rules_text=RULES)
