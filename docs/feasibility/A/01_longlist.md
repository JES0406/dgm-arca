# 01 — Longlist (Agent A)

Agent A brief: evaluate the user's candidate (**captcha solving**) plus at least 4 own topics,
biased towards high feasibility and high portfolio value. Quick filter on the four kill rows of
the scorecard (`docs/topic_debate_brief.md` §6), from desk knowledge only (0–3 each):

- **A** verifiable task exists
- **B** dataset without hand labels
- **C** right difficulty for Qwen3-0.6B–1.7B
- **D** real, free external HTTP API

Any 0 is a kill unless fixable. Scores here are *desk* scores. The deep phase (`02_*.md`)
re-scores the shortlisted topics with evidence.

| # | Topic (working title) | Domain | Close to a professor example? | A | B | C | D | Sum | Decision | One-line reason |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Laboratorio de robustez de captchas** (user's candidate): which preprocessing pipeline makes a self-generated captcha legible to OCR | Security / computer vision | No (new domain) | 2 | 3 | 1 | 1 | 7 | **KEEP** (mandatory) | Executable verifier and unlimited generator, but text-only phase-1 contract, weak API fit, ethics framing needed |
| 2 | **Factura de la luz 2.0TD**: compute and explain a household electricity bill; schedule appliances by hourly price | Energy / consumer, Spain | Partly (Finanzas: fiscal copilot) | 3 | 3 | 2 | 3 | 11 | **KEEP** | BOE rules → generator; REData API with no key; every Spanish household is a user |
| 3 | **Reclamación de derechos del pasajero aéreo (Reg. 261/2004)**: compensation amount + claim letter | Legal / consumer, EU/Spain | Partly (Legal: plazos) | 3 | 3 | 2 | 1 | 9 | **KEEP** | Crisp rule tree with CJEU edge cases; flight-status APIs are the weak spot |
| 4 | **Triaje de vulnerabilidades CVSS**: prose report → CVSS v3.1 score; NVD/OSV lookup; ticket | Cybersecurity | Partly (Software: bug triage) | 3 | 3 | 2 | 3 | 11 | **KEEP** | Official formula = verifier; NVD/OSV no-key APIs; 30k mineable real pairs; strong portfolio |
| 5 | **Nutri-Score 2023**: label → score; Open Food Facts lookup; shopping comparison | Food / health | No | 3 | 3 | 2 | 2 | 10 | **KEEP** | Published tables + OFF per-component oracle; 15 req/min limit and health disclaimer |
| 6 | Text-to-SQL over INE/datos.gob.es tables | Public statistics | Yes (fact checker) | 3 | 2 | 1 | 3 | 9 | cut | Close to the professor's fact-checker example; generating natural and diverse NL→SQL pairs is itself a project |
| 7 | Nómina neta: IRPF withholding (AEAT algorithm) + Social Security | Payroll / tax, Spain | Yes (fiscal copilot) | 3 | 3 | 1 | 1 | 8 | cut | AEAT withholding algorithm is ~40 pages of branches (too long for 384-token GRPO); no public API |
| 8 | METAR/TAF decoder: crosswind, density altitude, VFR/IFR category | Aviation weather | No | 3 | 3 | 2 | 3 | 11 | cut (contrast) | Excellent A–D (aviationweather.gov, no key), but corpus rights (ICAO docs are paid; FAA public domain but US-centric) and niche user |
| 9 | Renfe/EMT trip planner: earliest arrival over GTFS timetables | Transport, Spain | No | 2 | 3 | 1 | 2 | 8 | cut | Answers need long timetable context (hurts 384-token completions); EMT API needs registration |
| 10 | WCAG 2.2 accessibility auditor: colour contrast, target size | Web accessibility | No | 3 | 3 | 3 | 1 | 10 | cut (contrast) | Contrast ratio is too easy (one formula, base model likely >50 %); no natural external API |
| 11 | Hipoteca: French amortisation, TAE, Euríbor (BCE API) | Finance | Yes (credit risk, almost verbatim) | 3 | 3 | 2 | 3 | 11 | cut | Almost verbatim the professor's credit-risk example: differentiation row O ≈ 0 |

## Shortlist for the deep phase

1. Captcha robustness lab (mandatory, the user's candidate)
2. Factura de la luz 2.0TD
3. Reclamación pasajero aéreo (Reg. 261/2004)
4. Triaje CVSS
5. Nutri-Score 2023

The cut topics with an 11 (METAR, hipoteca) were cut on rows O/G/L, not A–D. They are listed so
the ranking can be challenged: if the team has a pilot or a banker, METAR or the mortgage
topic come back.

## Notes on the filter

- Row C is desk-only here. The deep phase replaces it with a measured Qwen3-0.6B pass@1
  (or, for captcha, an OCR headroom measurement: see `02_captcha.md`).
- Row D was spot-checked live during the deep phase, not at this stage.
