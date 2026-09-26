"""Feasibility prototype: CVSS v3.1 base score from a natural-language vulnerability report.

Task: read a short triage note describing how a vulnerability is exploited and what it
affects, and give the CVSS v3.1 base score (one decimal). The model must map prose to the
eight base metrics and then apply the specification's formula, including the Roundup
function and the Scope-dependent weights of Privileges Required.

Formula: FIRST CVSS v3.1 specification, section 7 and Appendix A
(https://www.first.org/cvss/v3.1/specification-document).

    uv run python docs/feasibility/A/cvss/generator.py --n 40
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.report import run_cli  # noqa: E402
from rlm.generate_problems import ProblemGenerator  # noqa: E402

AV = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}
AC = {"L": 0.77, "H": 0.44}
PR_U = {"N": 0.85, "L": 0.62, "H": 0.27}
PR_C = {"N": 0.85, "L": 0.68, "H": 0.5}
UI = {"N": 0.85, "R": 0.62}
CIA = {"H": 0.56, "L": 0.22, "N": 0.0}


def roundup(x: float) -> float:
    """CVSS v3.1 Appendix A: smallest number, to one decimal, >= x, robust to float error."""
    i = round(x * 100000)
    return i / 100000.0 if i % 10000 == 0 else (math.floor(i / 10000) + 1) / 10.0


def base_score(m: dict[str, str]) -> float:
    iss = 1 - (1 - CIA[m["C"]]) * (1 - CIA[m["I"]]) * (1 - CIA[m["A"]])
    if m["S"] == "U":
        impact = 6.42 * iss
    else:
        impact = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15
    pr = (PR_U if m["S"] == "U" else PR_C)[m["PR"]]
    exploit = 8.22 * AV[m["AV"]] * AC[m["AC"]] * pr * UI[m["UI"]]
    if impact <= 0:
        return 0.0
    if m["S"] == "U":
        return roundup(min(impact + exploit, 10))
    return roundup(min(1.08 * (impact + exploit), 10))


def raw_sum(m: dict[str, str]) -> float:
    """The unrounded base value: a model that rounds half-up instead of Roundup gets this."""
    iss = 1 - (1 - CIA[m["C"]]) * (1 - CIA[m["I"]]) * (1 - CIA[m["A"]])
    impact = 6.42 * iss if m["S"] == "U" else 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15
    pr = (PR_U if m["S"] == "U" else PR_C)[m["PR"]]
    exploit = 8.22 * AV[m["AV"]] * AC[m["AC"]] * pr * UI[m["UI"]]
    if impact <= 0:
        return 0.0
    return min(impact + exploit, 10) if m["S"] == "U" else min(1.08 * (impact + exploit), 10)


def severity(score: float) -> str:
    if score == 0:
        return "none"
    return "low" if score < 4 else "medium" if score < 7 else "high" if score < 9 else "critical"


# Several phrasings per metric value: lexical diversity is one of the four errors graded.
PHRASES = {
    "AV": {
        "N": ["se explota de forma remota a través de Internet", "basta con enviar peticiones HTTP al servicio expuesto",
              "el atacante puede estar en cualquier red con acceso al puerto publicado"],
        "A": ["el atacante tiene que estar en el mismo segmento de red local", "solo es alcanzable desde la misma VLAN o red Wi-Fi",
              "requiere estar en la red adyacente (mismo dominio de broadcast)"],
        "L": ["requiere una sesión local en la máquina", "el atacante necesita ejecutar código en el propio equipo",
              "se explota abriendo un fichero manipulado en el equipo de la víctima"],
        "P": ["exige acceso físico al dispositivo", "hay que conectar un USB al equipo", "requiere manipular físicamente el hardware"],
    },
    "AC": {
        "L": ["la explotación es fiable y repetible", "no hay condiciones especiales: funciona siempre",
              "no depende de ninguna condición fuera del control del atacante"],
        "H": ["depende de ganar una condición de carrera", "requiere conocer un secreto de configuración previo",
              "exige preparar el entorno objetivo (p. ej. un ataque man-in-the-middle)"],
    },
    "PR": {
        "N": ["no necesita autenticarse", "no requiere ningún privilegio previo", "un usuario anónimo puede lanzarlo"],
        "L": ["requiere una cuenta de usuario normal", "hace falta estar autenticado con privilegios básicos",
              "cualquier usuario registrado puede explotarlo"],
        "H": ["requiere privilegios de administrador", "solo un usuario con rol de administrador puede lanzarlo",
              "exige credenciales con control total del componente"],
    },
    "UI": {
        "N": ["no requiere interacción de ninguna víctima", "funciona sin que nadie haga nada"],
        "R": ["la víctima tiene que hacer clic en un enlace", "requiere que un usuario abra un documento preparado",
              "necesita que un administrador visite una página manipulada"],
    },
    "S": {
        "U": ["el impacto se queda dentro del componente vulnerable", "no afecta a recursos fuera de su autoridad de seguridad"],
        "C": ["permite escapar del sandbox y afectar al sistema anfitrión", "el impacto alcanza a otros componentes (p. ej. el navegador de otros usuarios)",
              "cambia el ámbito: afecta a recursos gestionados por otra autoridad"],
    },
    "C": {"H": ["se pueden leer todos los datos", "divulgación total de información"],
          "L": ["se filtra información parcial y limitada", "se obtiene acceso a algunos datos no críticos"],
          "N": ["no hay pérdida de confidencialidad", "no se expone ningún dato"]},
    "I": {"H": ["se puede modificar cualquier fichero", "pérdida total de integridad"],
          "L": ["solo se pueden modificar algunos datos sin control total", "modificación limitada de datos"],
          "N": ["no hay impacto en la integridad", "no se puede alterar nada"]},
    "A": {"H": ["el servicio cae por completo", "denegación de servicio total y sostenida"],
          "L": ["el rendimiento se degrada parcialmente", "interrupciones intermitentes del servicio"],
          "N": ["no afecta a la disponibilidad", "el servicio sigue funcionando con normalidad"]},
}
PRODUCTS = ["un CMS de código abierto", "un router doméstico", "una API REST interna", "un cliente de correo",
            "un plugin de WordPress", "un servidor de impresión", "una app móvil bancaria", "un NAS", "un hipervisor"]


class CVSSGenerator(ProblemGenerator):
    name = "cvss31"

    def sample_params(self, rng: random.Random, split: str) -> dict[str, Any]:
        m = {
            "AV": rng.choices("NALP", weights=[5, 2, 3, 1])[0],
            "AC": rng.choices("LH", weights=[3, 1])[0],
            "PR": rng.choice("NLH"),
            "UI": rng.choice("NR"),
            # OOD: Scope Changed never appears in train/test; it switches the PR weights and
            # the impact formula, so memorised sums fail and the spec has to be applied.
            "S": "C" if split == "ood" else "U",
            "C": rng.choice("HLN"), "I": rng.choice("HLN"), "A": rng.choice("HLN"),
        }
        if m["C"] == m["I"] == m["A"] == "N":
            m["C"] = "L"  # zero-impact vulnerabilities are not reported
        return {"metrics": m, "product": rng.randrange(len(PRODUCTS)),
                "phr": {k: rng.randrange(len(PHRASES[k][v])) for k, v in m.items()}}

    def key(self, params: dict[str, Any]) -> str:
        return str(sorted(params["metrics"].items())) + str(params["product"])

    def solve(self, params: dict[str, Any]) -> tuple[str, dict[str, str]]:
        m = params["metrics"]
        score = base_score(m)
        branches = {"severity": severity(score), "scope": m["S"], "AV": m["AV"], "PR": m["PR"],
                    "roundup_beats_round": str(score != round(raw_sum(m), 1))}
        return f"{score:.1f}", branches

    def render(self, params: dict[str, Any], rng: random.Random) -> tuple[str, int]:
        m = params["metrics"]
        facts = {k: PHRASES[k][v][params["phr"][k]] for k, v in m.items()}
        product = PRODUCTS[params["product"]]
        order = ["AV", "AC", "PR", "UI", "S", "C", "I", "A"]
        body = ", ".join(facts[k] for k in rng.sample(order, len(order)))
        templates = [
            f"Nota de triaje: vulnerabilidad en {product}. Según el informe, {body}. Calcula la puntuación "
            f"base CVSS v3.1 (con un decimal).",
            f"Un investigador ha reportado un fallo en {product}: {body}. ¿Cuál es la puntuación base CVSS v3.1?",
            f"Evalúa esta vulnerabilidad con CVSS v3.1 y devuelve solo la puntuación base. Producto: {product}. "
            f"Detalles: {body}.",
            f"Hemos reproducido un bug en {product}. Observaciones: {body}. Puntuación base CVSS 3.1 con un decimal.",
        ]
        tid = rng.randrange(len(templates))
        return templates[tid], tid


if __name__ == "__main__":
    # Self-checks against published NVD vectors before generating anything.
    log4shell = dict(AV="N", AC="L", PR="N", UI="N", S="C", C="H", I="H", A="H")  # CVE-2021-44228: 10.0
    classic = dict(AV="N", AC="L", PR="N", UI="N", S="U", C="H", I="H", A="H")  # 9.8
    xss = dict(AV="N", AC="L", PR="N", UI="R", S="C", C="L", I="L", A="N")  # typical reflected XSS: 6.1
    assert base_score(log4shell) == 10.0 and base_score(classic) == 9.8 and base_score(xss) == 6.1
    assert roundup(4.02) == 4.1 and roundup(4.0) == 4.0 and roundup(4.000001) == 4.0
    run_cli(CVSSGenerator(), Path(__file__).parent / "data")
