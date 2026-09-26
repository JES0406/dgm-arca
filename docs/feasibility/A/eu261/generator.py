"""Feasibility prototype: air-passenger compensation under Regulation (EC) 261/2004.

Task: given an incident (delay, cancellation, denied boarding), the route, the carrier and
the circumstances, compute the total compensation owed to the group, in euros.
Rules: Art. 3 (scope), 4 (denied boarding), 5 (cancellation), 7 (amounts and 50 % reduction),
CJEU Sturgeon C-402/07 (delay >= 3 h compensated like cancellation), Wallentin-Hermann
C-549/07 (technical faults are not extraordinary), Krüsemann C-195/17 (own-staff strikes
are not extraordinary), Pešková C-315/15 (bird strike is extraordinary).

    uv run python docs/feasibility/A/eu261/generator.py --n 40
"""

from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.report import run_cli  # noqa: E402
from rlm.generate_problems import ProblemGenerator  # noqa: E402

# Coordinates from OurAirports (public domain, https://ourairports.com/data/), rounded to 4 dp.
AIRPORTS = {
    "MAD": ("Madrid", 40.4934, -3.5722, True), "BCN": ("Barcelona", 41.2971, 2.0785, True),
    "PMI": ("Palma", 39.5517, 2.7388, True), "TFS": ("Tenerife Sur", 28.0445, -16.5725, True),
    "LPA": ("Gran Canaria", 27.9319, -15.3866, True), "AGP": ("Málaga", 36.6749, -4.4991, True),
    "SVQ": ("Sevilla", 37.418, -5.8931, True), "BIO": ("Bilbao", 43.3011, -2.9106, True),
    "LIS": ("Lisboa", 38.7813, -9.1359, True), "CDG": ("París", 49.009, 2.5541, True),
    "FCO": ("Roma", 41.8045, 12.252, True), "BER": ("Berlín", 52.3617, 13.5023, True),
    "HEL": ("Helsinki", 60.3184, 24.9633, True), "ATH": ("Atenas", 37.9364, 23.9445, True),
    "DUB": ("Dublín", 53.4287, -6.2621, True), "WAW": ("Varsovia", 52.1657, 20.9671, True),
    "VIE": ("Viena", 48.1103, 16.5697, True), "CPH": ("Copenhague", 55.6179, 12.656, True),
    "RUN": ("Saint-Denis (La Reunión)", -20.8901, 55.5189, True),
    # Non-EU for Regulation 261/2004. Switzerland, Norway and Iceland apply it by agreement,
    # so ZRH/OSL/KEF are deliberately left out to keep labels unambiguous.
    "LHR": ("Londres", 51.4707, -0.4599, False), "RAK": ("Marrakech", 31.6048, -8.0358, False),
    "IST": ("Estambul", 41.2749, 28.7321, False), "JFK": ("Nueva York", 40.6394, -73.7793, False),
    "BOG": ("Bogotá", 4.7016, -74.1469, False), "MEX": ("Ciudad de México", 19.4358, -99.0703, False),
    "DXB": ("Dubái", 25.2498, 55.371, False), "DOH": ("Doha", 25.2731, 51.6081, False),
}


def great_circle_km(a: str, b: str) -> int:
    """Haversine distance on a 6371 km sphere, rounded to km (Art. 7(4): great-circle route)."""
    from math import asin, cos, radians, sin, sqrt

    _, la1, lo1, _ = AIRPORTS[a]
    _, la2, lo2, _ = AIRPORTS[b]
    h = sin(radians(la2 - la1) / 2) ** 2 + cos(radians(la1)) * cos(radians(la2)) * sin(radians(lo2 - lo1) / 2) ** 2
    return round(2 * 6371 * asin(sqrt(h)))


EU_CARRIERS = ["Iberia", "Vueling", "Air Europa", "Air France", "Lufthansa", "Ryanair", "TAP"]
NON_EU_CARRIERS = ["Turkish Airlines", "Emirates", "Avianca", "Royal Air Maroc", "Qatar Airways", "British Airways"]
EXTRAORDINARY = {"none": False, "tormenta": True, "huelga_control": True, "impacto_ave": True,
                 "averia_tecnica": False, "huelga_tripulacion_propia": False}
EXTRA_TEXT = {
    "none": "La aerolínea no ha alegado ninguna causa.",
    "tormenta": "La aerolínea alega una tormenta severa que cerró el aeropuerto.",
    "huelga_control": "La aerolínea alega una huelga de controladores aéreos.",
    "impacto_ave": "La aerolínea alega que el avión sufrió el impacto de un ave en el vuelo anterior.",
    "averia_tecnica": "La aerolínea alega una avería técnica imprevista del avión.",
    "huelga_tripulacion_propia": "La aerolínea alega una huelga de su propia tripulación.",
}

RULES = """Reglas (Reglamento (CE) 261/2004 y jurisprudencia del TJUE):
1. Ámbito: se aplica a vuelos que salen de un aeropuerto de la UE (cualquier aerolínea) y a vuelos que llegan a la UE desde fuera si la aerolínea es de la UE. En otro caso no hay compensación.
2. Importe por pasajero según distancia ortodrómica: hasta 1500 km, 250 €; vuelos intracomunitarios de más de 1500 km y resto de vuelos de 1500 a 3500 km, 400 €; resto, 600 €. En vuelos con conexión cuenta la distancia entre el origen y el destino final.
3. Retraso: hay compensación si se llega al destino final con 3 horas o más de retraso. En vuelos del tramo de 600 € con un retraso de llegada de al menos 3 horas pero menos de 4, la compensación se reduce un 50 %.
4. Cancelación: no hay compensación si se avisó con 14 días o más; tampoco si se avisó con 7 a 13 días y el vuelo alternativo sale como máximo 2 horas antes y llega menos de 4 horas después de lo previsto; ni si se avisó con menos de 7 días y el alternativo sale como máximo 1 hora antes y llega menos de 2 horas después.
5. Denegación de embarque contra la voluntad del pasajero: siempre hay compensación (las circunstancias extraordinarias no eximen). Los voluntarios que aceptan renunciar no reciben esta compensación.
6. Si en una cancelación o denegación de embarque se ofrece un vuelo alternativo que llega con un retraso no superior a 2 h (tramo de 250 €), 3 h (tramo de 400 €) o 4 h (tramo de 600 €), la compensación se reduce un 50 %.
7. Circunstancias extraordinarias (meteorología, huelga de control aéreo, impacto de ave) eximen de compensar retrasos y cancelaciones. Una avería técnica o una huelga del propio personal de la aerolínea NO son extraordinarias.
8. La compensación total es la suma de la de todos los pasajeros del grupo."""


def hm(minutes: int) -> str:
    """Durations as 'X h YY min' so that minute counts never collide with euro answers."""
    h, m = divmod(minutes, 60)
    if minutes == 0:
        return "sin adelanto, a la misma hora,"
    return f"{h} h {m:02d} min" if h else f"{m} min"


def notice(days: int) -> str:
    return "el mismo día del vuelo" if days == 0 else f"con {days} días de antelación"


def band(distance: int, intra_eu: bool) -> int:
    if distance <= 1500:
        return 250
    if intra_eu or distance <= 3500:
        return 400
    return 600


def reroute_limit_h(amount: int) -> int:
    return {250: 2, 400: 3, 600: 4}[amount]


class EU261Generator(ProblemGenerator):
    name = "eu261"

    def sample_params(self, rng: random.Random, split: str) -> dict[str, Any]:
        eu = [k for k, v in AIRPORTS.items() if v[3]]
        non_eu = [k for k, v in AIRPORTS.items() if not v[3]]
        # Band sampled first, then a real route in that band (rejection), so bands stay balanced.
        target = rng.choice([250, 400, 600])
        for _ in range(5000):
            dep_eu, arr_eu = rng.choices([(True, True), (True, False), (False, True)], weights=[5, 3, 2])[0]
            origin = rng.choice(eu if dep_eu else non_eu)
            dest = rng.choice([a for a in (eu if arr_eu else non_eu) if a != origin])
            if band(great_circle_km(origin, dest), dep_eu and arr_eu) == target:
                break
        carrier_eu = rng.random() < 0.7
        params: dict[str, Any] = {
            "origin": origin, "dest": dest, "dep_eu": dep_eu, "arr_eu": arr_eu,
            "carrier": rng.choice(EU_CARRIERS if carrier_eu else NON_EU_CARRIERS), "carrier_eu": carrier_eu,
            "distance_km": great_circle_km(origin, dest), "passengers": rng.randint(1, 4),
            "incident": rng.choices(["delay", "cancellation", "denied_boarding"], weights=[4, 4, 2])[0],
            # Extraordinary causes are 3 of 6 labels; weight them down so "0" does not dominate.
            "cause": rng.choices(list(EXTRAORDINARY), weights=[4, 1, 1, 1, 2, 2])[0], "connection": None,
        }
        if params["incident"] == "delay":
            params["arrival_delay_min"] = rng.choice([rng.randint(60, 179), rng.randint(180, 239),
                                                      rng.randint(240, 600), rng.randint(170, 190),
                                                      rng.randint(181, 400), rng.randint(200, 300)])
        elif params["incident"] == "cancellation":
            params["notice_days"] = rng.choices([rng.randint(0, 6), rng.randint(7, 13), rng.randint(14, 30)],
                                                weights=[5, 2, 1])[0]
            params["alt_dep_earlier_min"] = rng.choice([0, 30, 60, 75, 90, 120, 150])
            params["alt_arr_later_min"] = rng.choice([45, 100, 119, 150, 179, 200, 235, 239, 265, 310, 420, 505])
        else:
            params["volunteer"] = rng.random() < 0.15
            params["alt_arr_later_min"] = rng.choice([90, 115, 150, 175, 210, 235, 290, 330])
        if split == "ood":
            # OOD family: connecting itinerary, distance counted origin -> final destination.
            hub = rng.choice([h for h in ("CDG", "FCO", "BER", "DOH", "IST") if h not in (origin, dest)])
            params["connection"] = hub
            params["first_leg_km"] = great_circle_km(origin, hub)
        return params

    def solve(self, params: dict[str, Any]) -> tuple[str, dict[str, str]]:
        intra = params["dep_eu"] and params["arr_eu"]
        amount = band(params["distance_km"], intra)
        in_scope = params["dep_eu"] or (params["arr_eu"] and params["carrier_eu"])
        extraordinary = EXTRAORDINARY[params["cause"]]
        inc = params["incident"]
        reason, per_pax = "", 0.0
        if not in_scope:
            reason = "out_of_scope"
        elif inc == "delay":
            d = params["arrival_delay_min"]
            if d < 180:
                reason = "delay_under_3h"
            elif extraordinary:
                reason = "extraordinary"
            else:
                per_pax, reason = amount, "delay_compensated"
                if amount == 600 and d < 240:
                    per_pax, reason = amount / 2, "delay_longhaul_reduced"
        elif inc == "cancellation":
            n, early, late = params["notice_days"], params["alt_dep_earlier_min"], params["alt_arr_later_min"]
            if n >= 14:
                reason = "notice_14d"
            elif 7 <= n <= 13 and early <= 120 and late < 240:
                reason = "notice_7_13_good_reroute"
            elif n < 7 and early <= 60 and late < 120:
                reason = "notice_lt7_good_reroute"
            elif extraordinary:
                reason = "extraordinary"
            else:
                per_pax, reason = amount, "cancel_compensated"
                if late <= reroute_limit_h(amount) * 60:
                    per_pax, reason = amount / 2, "cancel_reduced"
        else:
            if params["volunteer"]:
                reason = "volunteer"
            else:
                per_pax, reason = amount, "denied_compensated"
                if params["alt_arr_later_min"] <= reroute_limit_h(amount) * 60:
                    per_pax, reason = amount / 2, "denied_reduced"
        total = per_pax * params["passengers"]
        branches = {
            "incident": inc, "outcome": reason, "band": str(amount),
            "intra_eu_over_3500": str(intra and params["distance_km"] > 3500),
            "extraordinary_claimed": str(extraordinary), "scope": "in" if in_scope else "out",
            "zero": str(total == 0),
        }
        return f"{total:g}", branches

    def render(self, params: dict[str, Any], rng: random.Random) -> tuple[str, int]:
        oa, da = params["origin"], params["dest"]
        oc, dc = AIRPORTS[oa][0], AIRPORTS[da][0]
        pax = params["passengers"]
        who = "Viajo solo" if pax == 1 else f"Viajamos {pax} personas"
        route = f"{oc} ({oa}) a {dc} ({da})"
        dist = f"{params['distance_km']} km"
        if params["connection"]:
            route = f"{oc} ({oa}) a {dc} ({da}) con escala en {AIRPORTS[params['connection']][0]}"
            dist = (f"{params['first_leg_km']} km el primer tramo; la distancia ortodrómica entre el origen y el "
                    f"destino final es de {params['distance_km']} km")
        inc = params["incident"]
        if inc == "delay":
            what = f"llegamos al destino final con {hm(params['arrival_delay_min'])} de retraso"
        elif inc == "cancellation":
            what = (f"nos cancelaron el vuelo avisando {notice(params['notice_days'])}; el vuelo "
                    f"alternativo salía {hm(params['alt_dep_earlier_min'])} antes y llegaba "
                    f"{hm(params['alt_arr_later_min'])} después de lo previsto")
        else:
            vol = "nos ofrecimos voluntarios para ceder la plaza" if params["volunteer"] else \
                "nos denegaron el embarque por overbooking sin que fuéramos voluntarios"
            what = f"{vol}; nos recolocaron en un vuelo que llegó {hm(params['alt_arr_later_min'])} más tarde"
        cause = EXTRA_TEXT[params["cause"]]
        templates = [
            f"{who} en un vuelo de {params['carrier']} de {route} ({dist}). {what[0].upper() + what[1:]}. "
            f"{cause} ¿Cuánto nos corresponde de compensación en total, en euros?",
            f"Vuelo {route}, operado por {params['carrier']}. Distancia: {dist}. Pasajeros: {pax}. "
            f"Incidencia: {what}. {cause} Calcula la compensación total en euros según el Reglamento 261/2004.",
            f"{cause} Así nos lo explicó {params['carrier']} cuando, en el vuelo de {route}, {what}. "
            f"Son {dist} y {'viajaba solo' if pax == 1 else f'éramos {pax} pasajeros'}. ¿Qué compensación total "
            f"podemos reclamar?",
            f"Reclamación a {params['carrier']}: trayecto {route}, {dist}, {pax} pasajero(s). Hechos: {what}. "
            f"{cause} Indica el importe total de la compensación en euros.",
        ]
        tid = rng.randrange(len(templates))
        return templates[tid], tid


if __name__ == "__main__":
    run_cli(EU261Generator(), Path(__file__).parent / "data", rules_text=RULES)
