"""Study-planner capacity problems (feasibility prototype, Agent B).

The model does not optimise a plan (a solver tool does that in phase 2). It learns the
*capacity arithmetic* a student needs to trust or question the plan. Four problem types,
one generator, ``solve`` is the verifier:

    T1 log_update     hours left on a topic after logged sessions (clock times, deviations)
    T2 margin         available hours before the exam minus required hours (signed)
    T3 rate           minimum hours per study day to finish before the exam (ceil to 0.25)
    T4 finish_date    date a topic is finished under a fixed order, weekly availability, holidays

Conventions written in every statement: the study window is from today (included) to the
day before the exam (included); holidays are rest days; hours carry across topics within a
day in T4. Holidays come from a Nager.Date snapshot (``nager_ES_2026.json``,
``nager_ES_2027.json``), filtered by region.

    uv run python docs/feasibility/B/planner/generator.py --n 20 --split test
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
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

TOPICS = [
    "Topología (GI)", "Variedades diferenciables (GI)", "Geodésicas (GI)",
    "Procesos gaussianos (IAP)", "Optimización bayesiana (IAP)", "Redes neuronales bayesianas (IAP)",
    "Modelos de difusión (MGP)", "Flujos normalizantes (MGP)", "Modelos basados en energía (MGP)",
    "Cálculo de variaciones (MD)", "Elementos finitos (MD)", "Aproximación de V y Q (DRL)",
    "Aprendizaje por imitación (DRL)", "Kubernetes (IM)", "Redes de grafos (IAG)",
    "Cadenas de Markov (MP)",
]
WEEKDAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre"]
REGIONS = {"ES-MD": "Comunidad de Madrid", "ES-CT": "Cataluña", "ES-AN": "Andalucía",
           "ES-GA": "Galicia"}


def load_holidays() -> list[dict[str, Any]]:
    rows = []
    for year in (2026, 2027):
        rows += json.loads((HERE / f"nager_ES_{year}.json").read_text())
    return rows


HOLIDAYS = load_holidays()


def holidays_for(region: str, start: dt.date, end: dt.date) -> list[tuple[dt.date, str]]:
    """Holidays in [start, end) that apply to ``region`` (national ones have counties=None)."""
    out = []
    for h in HOLIDAYS:
        day = dt.date.fromisoformat(h["date"])
        if start <= day < end and (h["counties"] is None or region in h["counties"]):
            out.append((day, h["localName"]))
    return sorted(set(out))


def fmt_date(day: dt.date) -> str:
    return f"{WEEKDAYS[day.weekday()]} {day.day} de {MONTHS[day.month - 1]} de {day.year}"


def fmt_hours(x: float) -> str:
    """Spanish rendering for statements: 2,5 h."""
    return f"{x:g}".replace(".", ",")


def fmt_answer(x: float) -> str:
    """Canonical answer: dot decimal, no trailing zeros (4.25, 6, -3.5)."""
    return f"{round(x, 2):g}"


def days(start: dt.date, end: dt.date):
    for i in range((end - start).days):
        yield start + dt.timedelta(days=i)


def capacity(avail: list[float], start: dt.date, end: dt.date, hol: set[dt.date]) -> float:
    return sum(avail[d.weekday()] for d in days(start, end) if d not in hol)


# ------------------------------------------------------------------------------ generator

class PlannerGenerator(ProblemGenerator):
    name = "study_planner_capacity"

    def sample_params(self, rng: random.Random, split: str) -> dict[str, Any]:
        ood = split == "ood"
        # Round-robin over types so every set is balanced (the branch table must not be
        # dominated by the easy type).
        self._k = getattr(self, "_k", -1) + 1
        ptype = ["log_update", "margin", "rate", "finish_date"][self._k % 4]
        region = rng.choice(["ES-CT", "ES-AN", "ES-GA"]) if ood else "ES-MD"
        start = dt.date(2026, 9, 28) + dt.timedelta(days=rng.randint(0, 230))
        horizon = rng.randint(45, 90) if ood else rng.randint(5, 40)
        n_topics = rng.randint(5, 6) if ood else rng.randint(2, 4)
        topics = rng.sample(TOPICS, n_topics)
        # 3.0 .. 20.0 h in 0.5 steps; OOD horizons are 2-3x longer, so hours scale with them
        # (otherwise every OOD margin problem is feasible: an easy-branch trap).
        remaining = [rng.randint(6, 40) / 2 * (2.5 if ood else 1) for _ in topics]
        if ptype == "log_update" and rng.random() < 0.25:
            remaining = [rng.randint(1, 4) / 2 for _ in topics]  # small -> clamp-at-zero branch
        avail = [rng.choice([0, 0.5, 1, 1.5, 2, 2.5, 3, 4]) for _ in range(7)]
        if sum(1 for a in avail if a > 0) < 3:
            avail[rng.randrange(5)] = 2
        params: dict[str, Any] = {
            "type": ptype, "region": region, "start": start.isoformat(),
            "topics": topics, "remaining": remaining, "avail": avail,
        }
        if ptype == "log_update":
            sessions = []
            for back in sorted(rng.sample(range(1, 6), rng.randint(1, 3)), reverse=True):
                planned = rng.choice(topics)
                actual = rng.choice(topics) if rng.random() < 0.6 else planned
                begin = rng.randint(32, 84) * 15  # 08:00 .. 21:00 in minutes
                length = rng.randint(2, 12) * 15  # 30 .. 180 minutes
                sessions.append({"days_ago": back, "planned": planned, "actual": actual,
                                 "begin_min": begin, "length_min": length})
            params["sessions"] = sessions
            traps = [s["planned"] for s in sessions if s["planned"] != s["actual"]]
            pool = [s["actual"] for s in sessions] * 2 + traps * 2 + [rng.choice(topics)]
            params["asked"] = rng.choice(pool)
        else:
            params["exam"] = (start + dt.timedelta(days=horizon)).isoformat()
        if ptype == "finish_date":
            params["target"] = rng.randrange(n_topics)
            params.pop("exam")
        return params

    def solve(self, params: dict[str, Any]) -> tuple[str, dict[str, str]]:
        start = dt.date.fromisoformat(params["start"])
        avail, remaining, topics = params["avail"], params["remaining"], params["topics"]
        branches = {"type": params["type"], "region": params["region"],
                    "n_topics": str(len(topics))}
        if params["type"] == "log_update":
            i = topics.index(params["asked"])
            studied = sum(s["length_min"] for s in params["sessions"]
                          if s["actual"] == params["asked"]) / 60
            planned_only = any(s["planned"] == params["asked"] and s["actual"] != params["asked"]
                               for s in params["sessions"])
            left = max(0.0, remaining[i] - studied)
            branches.update({
                "asked_was_studied": str(studied > 0),
                "trap_planned_not_studied": str(planned_only),
                "clamped_at_zero": str(remaining[i] - studied < 0),
                "n_sessions": str(len(params["sessions"])),
            })
            return fmt_answer(left), branches

        if params["type"] == "finish_date":
            hol = {d for d, _ in holidays_for(params["region"], start,
                                              start + dt.timedelta(days=400))}
            need = sum(remaining[: params["target"] + 1])
            done, day, skipped = 0.0, start, 0
            while True:
                if day in hol:
                    skipped += 1
                else:
                    done += avail[day.weekday()]
                if done >= need - 1e-9:
                    break
                day += dt.timedelta(days=1)
            branches.update({"holiday_skipped": str(skipped > 0),
                             "target_is_last": str(params["target"] == len(topics) - 1),
                             "span_weeks": str(min((day - start).days // 7, 6))})
            return day.isoformat(), branches

        exam = dt.date.fromisoformat(params["exam"])
        hol_list = holidays_for(params["region"], start, exam)
        hol = {d for d, _ in hol_list}
        need = sum(remaining)
        branches["holidays_in_window"] = str(min(len(hol_list), 2)) + ("+" if len(hol_list) >= 2 else "")
        branches["horizon_weeks"] = str(min((exam - start).days // 7, 6))
        if params["type"] == "margin":
            margin = capacity(avail, start, exam, hol) - need
            branches["feasible"] = str(margin >= 0)
            return fmt_answer(margin), branches
        # rate: study days are the weekdays with avail > 0 that are not holidays
        study_days = [d for d in days(start, exam) if avail[d.weekday()] > 0 and d not in hol]
        raw_rate = need / len(study_days)
        rate = math.ceil(raw_rate * 4 - 1e-9) / 4
        branches["rounded_up"] = str(abs(rate - raw_rate) > 1e-9)
        return fmt_answer(rate), branches

    # --------------------------------------------------------------------------- render

    def render(self, params: dict[str, Any], rng: random.Random) -> tuple[str, int]:
        start = dt.date.fromisoformat(params["start"])
        topics, remaining, avail = params["topics"], params["remaining"], params["avail"]
        region = REGIONS[params["region"]]
        pending = "; ".join(f"{t}: {fmt_hours(h)} h" for t, h in zip(topics, remaining))
        weekly = ", ".join(f"{WEEKDAYS[i]} {fmt_hours(a)} h" for i, a in enumerate(avail) if a > 0)
        rest = [WEEKDAYS[i] for i, a in enumerate(avail) if a == 0]
        rest_txt = f" Los {', '.join(rest)} no estudio." if rest else ""
        today = fmt_date(start)
        ptype = params["type"]

        if ptype == "log_update":
            lines = []
            for s in params["sessions"]:
                day = start - dt.timedelta(days=s["days_ago"])
                b, e = s["begin_min"], s["begin_min"] + s["length_min"]
                clock = f"de {b // 60}:{b % 60:02d} a {e // 60}:{e % 60:02d}"
                when = {1: "ayer", 2: "anteayer"}.get(s["days_ago"], fmt_date(day))
                if s["planned"] == s["actual"]:
                    lines.append(f"{when} estudié {s['actual']} {clock}")
                else:
                    lines.append(f"{when} tocaba {s['planned']}, pero estudié {s['actual']} {clock}")
            log = "; ".join(lines)
            asked = params["asked"]
            templates = [
                f"Hoy es {today}. Antes de estas sesiones me quedaban estas horas por tema: {pending}. "
                f"Registro de estudio: {log}. ¿Cuántas horas me quedan de {asked}? "
                f"Responde con un número de horas (punto decimal).",
                f"Mi plan tenía pendientes {pending}. Desde entonces: {log}. "
                f"Calcula las horas que me faltan de {asked} (si ya lo he cubierto, 0).",
                f"Registro de sesiones — {log}. Pendiente antes del registro: {pending}. "
                f"Pregunta: horas restantes de {asked}.",
                f"Necesito actualizar mi planificación. Tenía {pending}. {log.capitalize()}. "
                f"¿Qué me queda de {asked}, en horas?",
                f"Soy estudiante del máster y llevo mi estudio por horas. Hoy, {today}, repaso: {log}. "
                f"Lo pendiente era {pending}. Dime cuántas horas quedan para {asked}.",
            ]
        elif ptype == "finish_date":
            order = " → ".join(topics)
            hol = holidays_for(params["region"], start, start + dt.timedelta(days=120))
            hol_txt = "; ".join(f"{fmt_date(d)} ({n})" for d, n in hol) or "ninguno"
            target = topics[params["target"]]
            templates = [
                f"Hoy es {today} y empiezo hoy. Voy a estudiar en este orden: {order}. Horas "
                f"necesarias: {pending}. Disponibilidad semanal: {weekly}.{rest_txt} Festivos en "
                f"{region} (no estudio): {hol_txt}. Si un día termino un tema, sigo con el siguiente "
                f"ese mismo día. ¿Qué día termino {target}? Responde con la fecha en formato AAAA-MM-DD.",
                f"Orden de estudio: {order}. Pendiente: {pending}. Estudio {weekly}.{rest_txt} "
                f"Empiezo el {today}. Festivos de {region} que descanso: {hol_txt}. Las horas sobrantes "
                f"de un día pasan al tema siguiente. Fecha (AAAA-MM-DD) en que acabo {target}.",
                f"Planificación: {pending}, en ese mismo orden. Cada semana dedico {weekly}.{rest_txt} "
                f"Los festivos ({hol_txt}) no estudio. Empezando hoy, {today}, ¿cuándo completo "
                f"{target}? Formato AAAA-MM-DD.",
                f"¿En qué fecha termino {target} si empiezo el {today}, sigo el orden {order}, "
                f"necesito {pending}, estudio {weekly}{'.' + rest_txt if rest_txt else ''} y descanso los "
                f"festivos de {region} ({hol_txt})? Las horas de un día se reparten entre temas "
                f"consecutivos. Da la fecha como AAAA-MM-DD.",
            ]
        else:
            exam = dt.date.fromisoformat(params["exam"])
            hol = holidays_for(params["region"], start, exam)
            hol_txt = "; ".join(f"{fmt_date(d)} ({n})" for d, n in hol) or "ninguno"
            window = (f"Estudio desde hoy, {today}, incluido, hasta el día anterior al examen, "
                      f"que es el {fmt_date(exam)}.")
            if ptype == "margin":
                templates = [
                    f"{window} Me quedan {pending}. Disponibilidad: {weekly}.{rest_txt} Festivos en "
                    f"{region} (no estudio): {hol_txt}. ¿Cuál es mi margen en horas (horas "
                    f"disponibles menos horas necesarias)? Negativo si no me da tiempo.",
                    f"¿Me da tiempo? Temas pendientes: {pending}. Puedo estudiar {weekly}.{rest_txt} "
                    f"{window} No estudio en festivos ({hol_txt}). Responde con las horas de margen "
                    f"(negativo = horas que faltan).",
                    f"Examen el {fmt_date(exam)}; hoy es {today} y cuenta. Horario: {weekly}.{rest_txt} "
                    f"Festivos que descanso: {hol_txt}. Necesito {pending}. Margen en horas "
                    f"(disponible − necesario):",
                    f"Calcula horas disponibles menos horas necesarias. Necesarias: {pending}. "
                    f"Disponibilidad por día de la semana: {weekly}.{rest_txt} {window} Festivos de "
                    f"{region}: {hol_txt} (esos días no estudio).",
                ]
            else:
                study = [WEEKDAYS[i] for i, a in enumerate(avail) if a > 0]
                templates = [
                    f"{window} Solo estudio los {', '.join(study)} y nunca en festivos ({hol_txt}). "
                    f"Me quedan {pending}. Si estudio las mismas horas cada día de estudio, ¿cuántas "
                    f"horas al día necesito como mínimo? Redondea hacia arriba al cuarto de hora (0.25).",
                    f"Pendiente: {pending}. Días de estudio: {', '.join(study)}; festivos de {region} "
                    f"libres ({hol_txt}). {window} Carga diaria mínima e igual para todos los días de "
                    f"estudio, redondeada hacia arriba a múltiplos de 0.25 h.",
                    f"¿Cuántas horas diarias (mínimo, en múltiplos de 0.25 redondeando hacia arriba) "
                    f"debo estudiar para acabar {pending} antes del examen del {fmt_date(exam)}? Hoy es "
                    f"{today} y cuenta. Estudio solo {', '.join(study)}, sin festivos ({hol_txt}).",
                ]
        template_id = rng.randrange(len(templates))
        return templates[template_id], template_id + 10 * ["log_update", "margin", "rate",
                                                          "finish_date"].index(ptype)


# ------------------------------------------------------------------------------ verifier

NUMBER = re.compile(r"^[+-]?\d+(?:[.,]\d+)?$")
DATE_ISO = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
DATE_DMY = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
UNIT_WORDS = re.compile(r"\s*(h|horas?|hours?)\.?$", re.IGNORECASE)


def _clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("−", "-").strip().strip("*` ")
    return UNIT_WORDS.sub("", text).strip()


def is_correct(predicted: str | None, expected: str) -> bool:
    """Strict: the answer block must be ONE number (dot or comma decimal, optional 'h') or ONE
    date (ISO or dd/mm/yyyy). Anything else, including '3 o 4', is wrong."""
    if predicted is None:
        return False
    p = _clean(predicted)
    if DATE_ISO.match(expected):
        m = DATE_ISO.match(p) or DATE_DMY.match(p)
        if not m:
            return False
        parts = [int(x) for x in m.groups()]
        y, mo, d = parts if DATE_ISO.match(p) else (parts[2], parts[1], parts[0])
        try:
            return dt.date(y, mo, d) == dt.date.fromisoformat(expected)
        except ValueError:
            return False
    if not NUMBER.match(p):
        return False
    return abs(float(p.replace(",", ".")) - float(expected)) < 1e-6


EDGE_CASES = [  # (predicted, expected, should_accept) -- become tests/test_verifier.py rows
    ("4.25", "4.25", True), ("4,25", "4.25", True), ("4,25 h", "4.25", True),
    ("4.250", "4.25", True), ("−6,5", "-6.5", True), ("6.5", "-6.5", False),
    ("3 o 4", "3", False), ("0", "0", True), ("-0", "0", True), ("425", "4.25", False),
    ("2026-11-03", "2026-11-03", True), ("03/11/2026", "2026-11-03", True),
    ("2026-11-3", "2026-11-03", True), ("11/03/2026", "2026-11-03", False),
    ("2026-02-30", "2026-02-28", False), ("martes 3 de noviembre", "2026-11-03", False),
    (None, "1", False), ("**2.5**", "2.5", True),
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
    problems = PlannerGenerator().generate(args.n, args.split, args.seed)
    out = Path(args.out or HERE / f"problems_{args.split}.jsonl")
    print(json.dumps(report(problems, out, args.split), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
