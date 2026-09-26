"""Single source of truth for the 15-row scorecards (brief §6) of the five shortlisted topics.

Renders each topic's table into its 02_<topic>.md (replacing the SCORECARD_<KEY> marker or the
previous table between the markers) and prints the ranking table used in 03_decision.md.

    uv run python docs/feasibility/A/common/scorecards.py
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROWS = [
    ("A", "Verifiable task exists"), ("B", "Dataset without hand labels"), ("C", "Right difficulty for 0.6B-1.7B"),
    ("D", "Real, free external API"), ("E", "Meaningful compute tool"), ("F", "Action tool, sandboxed, observable"),
    ("G", "Corpus: available, licensed, parseable"), ("H", "Gold set writable & meaningful"),
    ("I", "Agent tasks chain >= 2 tools, auto-checkable"), ("J", "Domain reward is natural"),
    ("K", "Interpretation material"), ("L", "Real user & portfolio value"), ("M", "Risk / safety overhead (3 = light)"),
    ("N", "Team fit & motivation"), ("O", "Differentiation from the 13 examples"),
]

# N (team fit) is unknown to this study: scored 2 for everyone (ASSUMPTION) so it does not decide.
CARDS: dict[str, dict] = {
    "LUZ": {
        "file": "02_luz.md", "title": "Factura de la luz 2.0TD",
        "verdict": "GO",
        "rows": {
            "A": (3, "Bill total to the cent; `solve` implements BOE rules; tolerance 0.01 with comma-aware parser"),
            "B": (3, "Generator, 0 leaks, 0 overlap, 4 templates, OOD = mid-period price change"),
            "C": (None, "see §2"),
            "D": (3, "REData keyless, verified 2026-09-26 (24 PVPC values)"),
            "E": (3, "7 rounded concepts + cheapest-window search over 24 prices"),
            "F": (3, ".ics file, DTSTART checkable against recomputed optimum"),
            "G": (3, "BOE (reusable with attribution), Spanish, parses; tables need row chunking (16.9 %)"),
            "H": (3, "2026 toll values, IEE floors, bono rules: facts a 2025 model lacks"),
            "I": (3, "5 tasks with numeric/file checks; impossible task = switch supplier"),
            "J": (3, "Breakdown reward = the professor's own finance suggestion"),
            "K": (2, "Bono-cap branch, territory, OOD, regulatory drift; dead IEE-floor branch"),
            "L": (3, "Every household; team members are users"),
            "M": (2, "Financial disclaimer + regulated values drift"),
            "N": (2, "ASSUMPTION: unknown team"),
            "O": (2, "Near the fiscal-copilot example; different base, live API, scheduling action"),
        },
    },
    "CVSS": {
        "file": "02_cvss.md", "title": "Triaje CVSS v3.1",
        "verdict": "GO",
        "rows": {
            "A": (3, "Closed-form FIRST formula; self-checked vs NVD (Log4Shell 10.0)"),
            "B": (3, "Generator + 30,030 mineable NVD pairs (2023 feed)"),
            "C": (None, "see §2"),
            "D": (3, "NVD API (200, keyless) + OSV.dev (18 advisories) + KEV feed (1,726)"),
            "E": (3, "Formula with Roundup trap (~50 % of problems)"),
            "F": (2, "Ticket file/webhook; fine but generic"),
            "G": (2, "Public-domain NIST + FIRST docs parse cleanly; English-only"),
            "H": (2, "Spec/examples details; the model partly knows CVSS already"),
            "I": (3, "NVD/OSV/KEV + calculator + ticket; exact checks"),
            "J": (3, "Per-metric partial credit: dense and aligned"),
            "K": (3, "Scope-Changed OOD, Roundup trap, template vs real NVD prose"),
            "L": (3, "Security teams; strong portfolio"),
            "M": (3, "Scoring/patching only; no personal data"),
            "N": (2, "ASSUMPTION: unknown team"),
            "O": (2, "Related to bug triage example, different verifier and domain"),
        },
    },
    "EU261": {
        "file": "02_eu261.md", "title": "Pasajero aéreo (Reg. 261/2004)",
        "verdict": "GO-IF-FIXED (flight API: free OpenSky account token)",
        "rows": {
            "A": (3, "Rule tree Art. 3/5/7 + CJEU; integer euros"),
            "B": (3, "Generator with real airport distances; 0 leaks; OOD = connections"),
            "C": (None, "see §2"),
            "D": (1, "OpenSky historical = HTTP 403 anonymous; OurAirports is a file"),
            "E": (2, "Haversine + rule engine; modest"),
            "F": (3, "Claim-letter PDF"),
            "G": (3, "EUR-Lex/CURIA in Spanish, reusable; bot challenge on bulk HTML"),
            "H": (3, "Case-law answers (Krüsemann, Bossen) the model may not recall"),
            "I": (3, "5 tasks, numeric checks"),
            "J": (2, "Decisive-article reward; some hacking surface"),
            "K": (3, "45 % zero baseline, band edges, intra-EU >3500 km, OOD"),
            "L": (3, "Every traveller; AirHelp-like product"),
            "M": (2, "Legal disclaimer"),
            "N": (2, "ASSUMPTION: unknown team"),
            "O": (2, "Legal like the plazos example, different law"),
        },
    },
    "NUTRI": {
        "file": "02_nutriscore.md", "title": "Nutri-Score 2023",
        "verdict": "GO-IF-FIXED (mine OFF labels; confirm SpF document licence)",
        "rows": {
            "A": (3, "Integer score from official tables; OFF oracle check passes"),
            "B": (3, "Generator + OFF mining (strategy 2)"),
            "C": (None, "see §2"),
            "D": (2, "OFF keyless but 15 req/min, User-Agent required"),
            "E": (2, "Table lookups; model could learn them"),
            "F": (2, "Shopping-list file"),
            "G": (1, "SpF docs EN/FR with unclear reuse licence; AESAN Spanish but generic"),
            "H": (2, "Algorithm-update details"),
            "I": (2, "Barcode comparisons; OFF rate limit"),
            "J": (3, "Per-component reward"),
            "K": (2, "Category switches; synthetic realism limited"),
            "L": (2, "Consumers/dietitians"),
            "M": (2, "Health disclaimer"),
            "N": (2, "ASSUMPTION: unknown team"),
            "O": (3, "No close example"),
        },
    },
    "CAPTCHA": {
        "file": "02_captcha.md", "title": "Laboratorio de captchas",
        "verdict": "GO-IF-FIXED (professor approves image input to /reasoning; else KILL)",
        "rows": {
            "A": (2, "Executable pipeline verifier works (RapidOCR); depends on OCR engine"),
            "B": (3, "Unlimited renderer, clean charset"),
            "C": (2, "Headroom measured: random 32 %, best fixed 50 %, oracle 71 %; VLM pass@1 ESTIMATE"),
            "D": (1, "HF datasets-server real but artificial for the user"),
            "E": (3, "OpenCV + OCR execution is the experiment"),
            "F": (2, "Robustness report file"),
            "G": (2, "CC BY arXiv papers parse; English, generic"),
            "H": (1, "Model already knows generic CV/captcha literature"),
            "I": (2, "Tasks checkable but self-referential"),
            "J": (2, "Cost penalty; 'do nothing' hack"),
            "K": (3, "Headroom, policy vs fixed pipeline, OOD surprise"),
            "L": (1, "Portfolio perception risk; no external user"),
            "M": (1, "ToS/ethics framing + API contract change"),
            "N": (2, "User's own idea: motivation high (+), but ASSUMPTION"),
            "O": (3, "New domain"),
        },
    },
}


def fill_c(pass1: dict[str, str]) -> None:
    """Row C from measured pass@1 (0.6B): score 3 if 5-50 %, 2 if 50-70 % or <5 % with a sound teacher path."""
    for key, text in pass1.items():
        score, why = text
        CARDS[key]["rows"]["C"] = (score, why)


def table(card: dict) -> str:
    lines = ["<!-- scorecard:start -->", "| Row | Criterion | Score | Justification |", "|---|---|---|---|"]
    total = 0
    for code, name in ROWS:
        s, why = card["rows"][code]
        total += s or 0
        lines.append(f"| {code} | {name} | {s if s is not None else 'tbd'} | {why} |")
    lines.append(f"| | **Total** | **{total}/45** | kill rows A-D all > 0 |")
    lines.append(f"\n**Verdict: {card['verdict']}**")
    lines.append("<!-- scorecard:end -->")
    return "\n".join(lines)


def render() -> None:
    for key, card in CARDS.items():
        path = ROOT / card["file"]
        text = path.read_text(encoding="utf-8")
        new = table(card)
        if f"SCORECARD_{key}" in text:
            text = text.replace(f"SCORECARD_{key}", new)
        else:
            text = re.sub(r"<!-- scorecard:start -->.*?<!-- scorecard:end -->", new, text, flags=re.S)
        path.write_text(text, encoding="utf-8")
    header = "| Topic | " + " | ".join(c for c, _ in ROWS) + " | Total | Verdict |"
    print(header)
    print("|---|" + "---|" * len(ROWS) + "---|---|")
    ranked = sorted(CARDS.values(), key=lambda c: -sum(s or 0 for s, _ in c["rows"].values()))
    for card in ranked:
        scores = [card["rows"][c][0] for c, _ in ROWS]
        print(f"| {card['title']} | " + " | ".join(str(s) for s in scores)
              + f" | **{sum(s or 0 for s in scores)}** | {card['verdict']} |")


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) > 1:
        fill_c({k: tuple(v) for k, v in json.loads(Path(sys.argv[1]).read_text()).items()})
    render()
