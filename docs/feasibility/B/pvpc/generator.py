"""PVPC 2.0TD electricity problems (feasibility prototype, Agent B).

Four types, one generator, ``solve`` is the verifier:

    T1 period     P1/P2/P3 of a given date and time (weekends, fixed national holidays;
                  trap: Good Friday and regional holidays are NOT valle)
    T2 run_cost   cost of running an appliance of P kW from hh:mm for m minutes, with the
                  hourly PVPC prices of those hours given (partial hours)
    T3 bill       full household bill to the cent: power terms (peajes + cargos + margin),
                  energy at given per-period average prices, bono social, electricity tax with
                  its 1 EUR/MWh floor, meter rental, VAT; every line rounded to cents
    T4 window     start hour of the cheapest contiguous k-hour window in a list of prices

Constants are the 2026 values verified in ``research.md`` (CNMC Res. 18/12/2025, Orden
TED/1524/2025, Circular 3/2020 art. 7.3). Items marked ASSUMPTION there (margin, bono social
pass-through, meter rental, /365) are stated in the rule sheet, so the task is well-defined
even if the real bill differs.

    uv run python docs/feasibility/B/pvpc/generator.py --n 20 --split test
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
sys.path.insert(0, str(HERE.parent / "common"))

from harness import report  # noqa: E402

from rlm.generate_problems import ProblemGenerator  # noqa: E402

POWER_P1 = 23.324952 + 4.379461 + 3.113  # peaje + cargo + marketing margin, EUR/kW-year
POWER_P2 = 0.443770 + 0.281653
BONO_SOCIAL_YEAR = 6.979247
IEE_RATE = 0.0511269632
IEE_MIN_EUR_PER_KWH = 0.001
METER_MONTH = 0.81
VAT = 0.21
# Fixed-date national holidays that make a weekday all-P3 (Circular 3/2020 art. 7.3).
FIXED_NATIONAL = {(1, 1), (1, 6), (5, 1), (8, 15), (10, 12), (11, 1), (12, 6), (12, 8), (12, 25)}
MOVEABLE = {dt.date(2026, 4, 3): "Viernes Santo", dt.date(2027, 3, 26): "Viernes Santo",
            dt.date(2026, 4, 2): "Jueves Santo (festivo autonómico)",
            dt.date(2026, 5, 2): "Día de la Comunidad de Madrid (autonómico)"}
WEEKDAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre"]

RULES_TEXT = """Reglas (peaje 2.0TD, península, 2026):
- Periodos de energía en días laborables de lunes a viernes: P1 de 10 a 14 h y de 18 a 22 h;
  P2 de 8 a 10 h, de 14 a 18 h y de 22 a 24 h; P3 de 0 a 8 h. Sábados, domingos y festivos
  nacionales de fecha fija (1 ene, 6 ene, 1 may, 15 ago, 12 oct, 1 nov, 6 dic, 8 dic, 25 dic):
  todo el día P3. Festivos autonómicos, locales o sin fecha fija NO cuentan.
- Potencia: P1 31,017413 €/kW·año; P2 0,725423 €/kW·año; se prorratea por días/365.
- Bono social: 6,979247 €/año, prorrateado por días/365.
- Impuesto eléctrico: 5,11269632 % de (potencia + energía + bono social), con un mínimo de
  1 €/MWh consumido.
- Alquiler de contador: 0,81 €/mes (días/365 × 12 meses).
- IVA 21 % sobre todo lo anterior. Cada línea se redondea al céntimo antes de sumar."""


def fmt_date(day: dt.date) -> str:
    return f"{WEEKDAYS[day.weekday()]} {day.day} de {MONTHS[day.month - 1]} de {day.year}"


def eur(x: float) -> float:
    return round(x + 1e-9, 2)


def period_of(day: dt.date, hour: int) -> tuple[str, str]:
    if day.weekday() >= 5:
        return "P3", "weekend"
    if (day.month, day.day) in FIXED_NATIONAL:
        return "P3", "fixed_national_holiday"
    reason = "moveable_or_regional_holiday_trap" if day in MOVEABLE else "working_day"
    if hour < 8:
        return "P3", reason
    if 10 <= hour < 14 or 18 <= hour < 22:
        return "P1", reason
    return "P2", reason


class PvpcGenerator(ProblemGenerator):
    name = "pvpc_2_0td"

    def sample_params(self, rng: random.Random, split: str) -> dict[str, Any]:
        self._k = getattr(self, "_k", -1) + 1
        ptype = ["period", "run_cost", "bill", "window"][self._k % 4]
        ood = split == "ood"
        p: dict[str, Any] = {"type": ptype}
        if ptype == "period":
            year = 2027 if ood else 2026  # OOD = a calendar year never seen in train
            pool = [dt.date(year, m, d) for m, d in FIXED_NATIONAL] + [
                d for d in MOVEABLE if d.year == year]
            day = rng.choice(pool) if rng.random() < 0.4 else (
                dt.date(year, 1, 1) + dt.timedelta(days=rng.randint(0, 364)))
            p.update(date=day.isoformat(), hour=rng.randint(0, 23), minute=rng.choice([0, 15, 30, 45]))
        elif ptype == "run_cost":
            start = rng.randint(0, 22) * 60 + rng.choice([0, 15, 30, 45])
            length = rng.choice([30, 45, 60, 90, 120, 150]) if not ood else rng.choice([210, 240, 300])
            n_hours = (start + length - 1) // 60 - start // 60 + 1
            p.update(start_min=start, length_min=length, kw=rng.choice([0.8, 1.2, 2.0, 2.2, 3.5]),
                     prices=[rng.randint(40, 320) / 1000 for _ in range(n_hours)])
        elif ptype == "bill":
            days = rng.choice([28, 29, 30, 31, 32, 33]) if not ood else rng.choice([59, 60, 61, 62])
            p.update(days=days, kw_p1=rng.choice([2.3, 3.3, 3.45, 4.4, 4.6, 5.75, 6.9]),
                     kw_p2=None, kwh=[rng.randint(10, 150), rng.randint(10, 150), rng.randint(20, 250)],
                     price=[rng.randint(150, 320) / 1000, rng.randint(90, 200) / 1000,
                            rng.randint(40, 120) / 1000])
            p["kw_p2"] = p["kw_p1"] if rng.random() < 0.7 else rng.choice([3.3, 4.6, 6.9])
        else:
            n = rng.randint(8, 12) if not ood else rng.randint(16, 24)
            first = rng.randint(0, 24 - n)
            p.update(first_hour=first, k=rng.choice([2, 3]) if not ood else rng.choice([3, 4]),
                     prices=[rng.randint(20, 300) / 1000 for _ in range(n)])
        return p

    def solve(self, p: dict[str, Any]) -> tuple[str, dict[str, str]]:
        b = {"type": p["type"]}
        if p["type"] == "period":
            label, reason = period_of(dt.date.fromisoformat(p["date"]), p["hour"])
            b.update(reason=reason, label=label)
            return label, b
        if p["type"] == "run_cost":
            cost, t, end = 0.0, p["start_min"], p["start_min"] + p["length_min"]
            while t < end:
                nxt = min((t // 60 + 1) * 60, end)
                cost += p["kw"] * (nxt - t) / 60 * p["prices"][t // 60 - p["start_min"] // 60]
                t = nxt
            b.update(partial_hours=str(p["start_min"] % 60 != 0 or p["length_min"] % 60 != 0),
                     crosses_midnight=str(end > 24 * 60), n_prices=str(len(p["prices"])))
            return f"{eur(cost):.2f}", b
        if p["type"] == "bill":
            f = p["days"] / 365
            power = eur(p["kw_p1"] * POWER_P1 * f) + eur(p["kw_p2"] * POWER_P2 * f)
            energy = eur(sum(k * c for k, c in zip(p["kwh"], p["price"])))
            bono = eur(BONO_SOCIAL_YEAR * f)
            base = power + energy + bono
            kwh = sum(p["kwh"])
            iee_pct, iee_min = base * IEE_RATE, kwh * IEE_MIN_EUR_PER_KWH
            iee = eur(max(iee_pct, iee_min))
            meter = eur(METER_MONTH * 12 * f)
            vat = eur((base + iee + meter) * VAT)
            total = eur(base + iee + meter + vat)
            b.update(iee_floor_binds=str(iee_min > iee_pct), p2_differs=str(p["kw_p2"] != p["kw_p1"]),
                     long_period=str(p["days"] > 40))
            return f"{total:.2f}", b
        prices, k = p["prices"], p["k"]
        sums = [sum(prices[i:i + k]) for i in range(len(prices) - k + 1)]
        best = min(range(len(sums)), key=lambda i: (sums[i], i))
        b.update(tie=str(sums.count(sums[best]) > 1), k=str(k),
                 best_is_edge=str(best in (0, len(sums) - 1)))
        return str(p["first_hour"] + best), b

    def render(self, p: dict[str, Any], rng: random.Random) -> tuple[str, int]:
        t = p["type"]
        if t == "period":
            day = dt.date.fromisoformat(p["date"])
            clock = f"{p['hour']}:{p['minute']:02d}"
            note = f" ({MOVEABLE[day]})" if day in MOVEABLE else ""
            templates = [
                f"{RULES_TEXT}\n\n¿En qué periodo de energía (P1, P2 o P3) cae el consumo del "
                f"{fmt_date(day)}{note} a las {clock}?",
                f"{RULES_TEXT}\n\nTengo tarifa 2.0TD. Pongo la lavadora el {fmt_date(day)}{note} a "
                f"las {clock}. ¿Es punta, llano o valle? Responde P1, P2 o P3.",
                f"{RULES_TEXT}\n\nFecha: {fmt_date(day)}{note}. Hora: {clock}. Periodo 2.0TD:",
            ]
        elif t == "run_cost":
            s = p["start_min"]
            first = s // 60
            table = "; ".join(f"{(first + i) % 24}-{(first + i) % 24 + 1} h: "
                              f"{str(c).replace('.', ',')} €/kWh" for i, c in enumerate(p["prices"]))
            kw = str(p["kw"]).replace(".", ",")
            templates = [
                f"Un aparato de {kw} kW funciona desde las {s // 60}:{s % 60:02d} durante "
                f"{p['length_min']} minutos. Precios PVPC por hora: {table}. ¿Cuánto cuesta la "
                f"energía, en euros con dos decimales?",
                f"Precios horarios: {table}. Enciendo el horno ({kw} kW) a las {s // 60}:{s % 60:02d} "
                f"y lo tengo {p['length_min']} min. Coste en €:",
                f"Calcula el coste en euros (dos decimales) de consumir {kw} kW constantes entre "
                f"las {s // 60}:{s % 60:02d} y {p['length_min']} minutos después, con estos precios "
                f"PVPC: {table}.",
            ]
        elif t == "bill":
            kwh = ", ".join(f"P{i + 1} {k} kWh" for i, k in enumerate(p["kwh"]))
            pr = ", ".join(f"P{i + 1} {str(c).replace('.', ',')} €/kWh" for i, c in enumerate(p["price"]))
            pw = (f"{str(p['kw_p1']).replace('.', ',')} kW en P1 y "
                  f"{str(p['kw_p2']).replace('.', ',')} kW en P2")
            templates = [
                f"{RULES_TEXT}\n\nFactura de {p['days']} días. Potencia contratada: {pw}. Consumo: "
                f"{kwh}. Precio medio de la energía (PVPC, ya incluye peajes y cargos): {pr}. "
                f"¿Importe total de la factura en euros?",
                f"{RULES_TEXT}\n\nMi factura PVPC cubre {p['days']} días; tengo {pw}. Consumí {kwh}, "
                f"a precios medios {pr}. Calcula el total con impuestos (dos decimales).",
            ]
        else:
            first = p["first_hour"]
            table = "; ".join(f"{first + i} h: {str(c).replace('.', ',')}" for i, c in enumerate(p["prices"]))
            templates = [
                f"Precios PVPC de mañana (€/kWh, hora de inicio): {table}. Quiero poner el lavavajillas "
                f"{p['k']} horas seguidas lo más barato posible. ¿A qué hora empiezo? Responde solo la "
                f"hora (si hay empate, la más temprana).",
                f"Tengo que cargar el coche {p['k']} horas consecutivas. Precios por hora: {table}. "
                f"Hora de inicio del tramo más barato (entero; empate → la primera):",
                f"¿Qué ventana de {p['k']} horas seguidas es más barata? {table}. Da la hora de inicio "
                f"(la más temprana en caso de empate).",
            ]
        i = rng.randrange(len(templates))
        return templates[i], i + 10 * ["period", "run_cost", "bill", "window"].index(t)


def _clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("−", "-").strip().strip("*` .")
    return re.sub(r"\s*(€|eur(os)?|h|horas?)$", "", text, flags=re.IGNORECASE).strip()


def is_correct(predicted: str | None, expected: str) -> bool:
    """Labels exact (P1/P2/P3, case-insensitive); euros to the cent; hours as integers.
    One value only: '2,35 o 2,36' is wrong."""
    if predicted is None:
        return False
    p = _clean(predicted)
    if expected in {"P1", "P2", "P3"}:
        return p.upper() == expected
    if not re.fullmatch(r"-?\d+(?:[.,]\d{1,2})?", p):  # to the cent, no more digits
        return False
    return abs(float(p.replace(",", ".")) - float(expected)) < 0.005


EDGE_CASES = [
    ("P3", "P3", True), ("p3", "P3", True), ("valle", "P3", False), ("P3 (valle)", "P3", False),
    ("12,34", "12.34", True), ("12,34 €", "12.34", True), ("12.3", "12.34", False),
    ("12.335", "12.34", False), ("1.234,56", "1234.56", False), ("21", "21", True),
    ("21 h", "21", True), ("21:00", "21", False), ("2,35 o 2,36", "2.35", False), (None, "P1", False),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--split", default="test")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    for pred, exp, ok in EDGE_CASES:
        assert is_correct(pred, exp) == ok, (pred, exp, ok)
    # sanity: the worked example of research.md (4.6 kW, 30 days, 250 kWh at 0.15) ≈ 64.56
    problems = PvpcGenerator().generate(args.n, args.split, args.seed)
    out = Path(args.out or HERE / f"problems_{args.split}.jsonl")
    print(json.dumps(report(problems, out, args.split), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
