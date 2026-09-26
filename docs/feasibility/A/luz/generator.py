"""Feasibility prototype: household electricity bill under the 2.0TD access tariff (Spain).

Task: given a billing period (days, contracted power, kWh per time band, the supplier's
prices, social-bonus status, territory) compute the bill total in euros to the cent.
``solve`` is a reference implementation of the bill and therefore the verifier.

The legal constants live in ``RULES`` and are printed as a rule sheet in every statement,
so the task is well defined even when real-world values change (ASSUMPTION: values checked
against BOE/CNMC in 02_luz.md; the sheet is what the model is graded against).

    uv run python docs/feasibility/A/luz/generator.py --n 40
"""

from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.report import run_cli  # noqa: E402
from rlm.generate_problems import ProblemGenerator  # noqa: E402

IEE_RATE = 0.0511269632
IEE_MIN_EUR_PER_KWH = 0.001  # 1 EUR/MWh floor for domestic supply
METER_EUR_PER_DAY = 0.026630
BONO_FINANCING_EUR_PER_DAY = 0.012742
BONO_DISCOUNT = {"vulnerable": 0.425, "severo": 0.575}
BONO_ANNUAL_CAP_KWH = {"A": 1587, "B": 2222, "C": 4761}
INDIRECT_TAX = {"peninsula": ("IVA", 0.21), "canarias": ("IGIC", 0.03), "ceuta_melilla": ("IPSI", 0.01)}
POWER_OPTIONS = (2.3, 3.3, 3.45, 4.4, 4.6, 5.5, 5.75, 6.9)

RULES = """Reglas de facturación (tarifa de acceso 2.0TD):
1. Término de potencia = kW contratados en P1 × precio P1 (€/kW·día) × días + kW contratados en P2 × precio P2 (€/kW·día) × días.
2. Término de energía = kWh en P1 × precio P1 + kWh en P2 × precio P2 + kWh en P3 × precio P3.
3. Bono social: descuento del 42,5 % (vulnerable) o 57,5 % (vulnerable severo) sobre el término de potencia completo y sobre la parte del término de energía que corresponde al consumo con derecho a descuento. El consumo con derecho a descuento en la factura es el límite anual × días / 365 (categoría A: 1.587 kWh/año; B: 2.222 kWh/año; C: 4.761 kWh/año). Si el consumo total supera ese límite, solo se bonifica la fracción límite/consumo del término de energía.
4. Financiación del bono social: 0,012742 € por día (lo pagan todos los clientes, no recibe descuento).
5. Impuesto especial sobre la electricidad: 5,11269632 % de (potencia + energía − descuento del bono social + financiación del bono social), con un mínimo de 1 € por MWh consumido.
6. Alquiler del contador: 0,026630 € por día.
7. Impuesto indirecto sobre la suma de todo lo anterior: IVA 21 % en península y Baleares; IGIC 3 % en Canarias; IPSI 1 % en Ceuta y Melilla.
8. Cada concepto (potencia, energía, descuento, financiación, impuesto eléctrico, contador, impuesto indirecto) se redondea a céntimos antes de sumar."""

TERRITORY_TEXT = {
    "peninsula": ["Madrid", "Valencia", "Zaragoza", "Palma", "Bilbao", "Sevilla"],
    "canarias": ["Las Palmas de Gran Canaria", "Santa Cruz de Tenerife"],
    "ceuta_melilla": ["Ceuta", "Melilla"],
}
BONO_TEXT = {"none": "no tiene bono social", "vulnerable": "tiene bono social como consumidor vulnerable",
             "severo": "tiene bono social como consumidor vulnerable severo"}


def c(x: float) -> float:
    """Round half away from zero to cents (bills do not use banker's rounding)."""
    from decimal import ROUND_HALF_UP, Decimal

    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


class ElectricityBillGenerator(ProblemGenerator):
    name = "factura_2_0td"

    def sample_params(self, rng: random.Random, split: str) -> dict[str, Any]:
        p1 = rng.choice(POWER_OPTIONS)
        p2 = p1 if rng.random() < 0.6 else rng.choice(POWER_OPTIONS)
        bono = rng.choices(["none", "vulnerable", "severo"], weights=[5, 3, 2])[0]
        # Small households keep the social-bonus cap branch balanced (cap ~130-390 kWh/period).
        scale = 0.3 if rng.random() < 0.45 else 1.0
        params = {
            "days": rng.randint(27, 34),
            "kw": [p1, p2],
            "power_price": [round(rng.uniform(0.070, 0.115), 6), round(rng.uniform(0.002, 0.045), 6)],
            "energy_price": [round(rng.uniform(0.15, 0.30), 6), round(rng.uniform(0.10, 0.20), 6),
                             round(rng.uniform(0.06, 0.14), 6)],
            "kwh": [max(5, round(rng.randint(25, 220) * scale)), max(5, round(rng.randint(25, 200) * scale)),
                    max(8, round(rng.randint(40, 380) * scale))],
            "bono": bono,
            "bono_cat": rng.choice("ABC") if bono != "none" else None,
            "territory": rng.choices(list(INDIRECT_TAX), weights=[7, 2, 1])[0],
            "city_idx": rng.randrange(6),
            "price_change_day": None,
        }
        if split == "ood":
            # OOD family: the supplier changes prices mid-period (prorated), never in train/test.
            params["price_change_day"] = rng.randint(5, params["days"] - 5)
            params["energy_price_2"] = [round(p * rng.uniform(0.8, 1.25), 6) for p in params["energy_price"]]
            params["kwh_2"] = [rng.randint(10, 120), rng.randint(10, 110), rng.randint(20, 200)]
        return params

    def solve(self, params: dict[str, Any]) -> tuple[str, dict[str, str]]:
        days = params["days"]
        potencia = sum(k * p * days for k, p in zip(params["kw"], params["power_price"]))
        energia = sum(k * p for k, p in zip(params["kwh"], params["energy_price"]))
        kwh_total = sum(params["kwh"])
        if params["price_change_day"] is not None:
            energia += sum(k * p for k, p in zip(params["kwh_2"], params["energy_price_2"]))
            kwh_total += sum(params["kwh_2"])
        potencia, energia = c(potencia), c(energia)

        descuento, cap_binds = 0.0, "n/a"
        if params["bono"] != "none":
            cap = BONO_ANNUAL_CAP_KWH[params["bono_cat"]] * days / 365
            frac = min(1.0, cap / kwh_total)
            cap_binds = str(frac < 1.0)
            descuento = c(BONO_DISCOUNT[params["bono"]] * (potencia + energia * frac))
        financiacion = c(BONO_FINANCING_EUR_PER_DAY * days)
        iee_base = potencia + energia - descuento + financiacion
        iee_pct = IEE_RATE * iee_base
        iee_min = IEE_MIN_EUR_PER_KWH * kwh_total
        iee = c(max(iee_pct, iee_min))
        contador = c(METER_EUR_PER_DAY * days)
        base = potencia + energia - descuento + financiacion + iee + contador
        _, rate = INDIRECT_TAX[params["territory"]]
        indirecto = c(base * rate)
        total = c(base + indirecto)
        branches = {
            "territory": params["territory"],
            "bono": params["bono"],
            "bono_cap_binds": cap_binds,
            "iee_minimum_applies": str(iee_min > iee_pct),
            "p1_eq_p2": str(params["kw"][0] == params["kw"][1]),
            "price_change": str(params["price_change_day"] is not None),
        }
        return f"{total:.2f}", branches

    def render(self, params: dict[str, Any], rng: random.Random) -> tuple[str, int]:
        city_list = TERRITORY_TEXT[params["territory"]]
        city = city_list[params["city_idx"] % len(city_list)]
        kw1, kw2 = (str(k).replace(".", ",") for k in params["kw"])
        pp1, pp2 = (f"{p:.6f}".replace(".", ",") for p in params["power_price"])
        e1, e2, e3 = (f"{p:.6f}".replace(".", ",") for p in params["energy_price"])
        k1, k2, k3 = params["kwh"]
        bono = BONO_TEXT[params["bono"]]
        if params["bono_cat"]:
            bono += f" (categoría {params['bono_cat']})"
        d = params["days"]
        extra = ""
        if params["price_change_day"] is not None:
            f1, f2, f3 = (f"{p:.6f}".replace(".", ",") for p in params["energy_price_2"])
            j1, j2, j3 = params["kwh_2"]
            extra = (
                f" Atención: a partir del día {params['price_change_day']} del periodo la comercializadora "
                f"cambió los precios de energía a P1 {f1}, P2 {f2} y P3 {f3} €/kWh; los consumos anteriores "
                f"son los de antes del cambio y después del cambio se consumieron {j1}, {j2} y {j3} kWh en "
                f"P1, P2 y P3. Los precios de potencia no cambian."
            )
        templates = [
            f"Calcula el importe total de la factura de luz de un hogar en {city}. Periodo de facturación: "
            f"{d} días. Potencia contratada: {kw1} kW en P1 y {kw2} kW en P2, a {pp1} y {pp2} €/kW·día. "
            f"Consumo: {k1} kWh en P1, {k2} kWh en P2 y {k3} kWh en P3, a {e1}, {e2} y {e3} €/kWh. "
            f"El titular {bono}.{extra} Da el total en euros con dos decimales.",
            f"Mi factura cubre {d} días y vivo en {city}. Consumí {k3} kWh en valle (P3), {k2} kWh en llano "
            f"(P2) y {k1} kWh en punta (P1). Pago la energía a {e1} €/kWh en punta, {e2} en llano y {e3} en "
            f"valle, y la potencia a {pp1} €/kW·día (P1) y {pp2} €/kW·día (P2), con {kw1} kW y {kw2} kW "
            f"contratados. El titular {bono}.{extra} ¿Cuánto tengo que pagar en total?",
            f"Suministro en {city}. Días facturados: {d}. P1: {kw1} kW a {pp1} €/kW·día; P2: {kw2} kW a "
            f"{pp2} €/kW·día. Energía P1/P2/P3: {k1}/{k2}/{k3} kWh a {e1}/{e2}/{e3} €/kWh. Bono social: "
            f"el titular {bono}.{extra} Importe total de la factura con dos decimales.",
            f"Un cliente de {city} {bono}. En {d} días ha consumido {k1 + k2 + k3} kWh repartidos así: "
            f"{k1} en P1, {k2} en P2 y {k3} en P3. Su oferta cobra {e1}, {e2} y {e3} €/kWh por periodo y "
            f"{pp1} y {pp2} €/kW·día por la potencia, y tiene {kw1} kW (P1) y {kw2} kW (P2).{extra} "
            f"Calcula el total a pagar en euros.",
        ]
        tid = rng.randrange(len(templates))
        return templates[tid], tid


if __name__ == "__main__":
    run_cli(ElectricityBillGenerator(), Path(__file__).parent / "data", rules_text=RULES)
