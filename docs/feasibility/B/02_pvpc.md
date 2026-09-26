# 02 — PVPC electricity bill & load shifting (2.0TD)

**One sentence.** Un agente que explica y comprueba la factura de luz regulada (PVPC, peaje
2.0TD) de un hogar, calcula cuánto cuesta cada electrodoméstico según la hora y programa
los consumos en las horas más baratas.

User: any Spanish household on PVPC (≈8–9 M supply points, ASSUMPTION order of magnitude);
also the team itself. Today they read a bill they do not understand and guess when "valle"
is.

Evidence: [`pvpc/research.md`](pvpc/research.md) (sources, API calls, corpus checks).

---

## 1. Verifiable task (phase 1)

Prototype: [`pvpc/generator.py`](pvpc/generator.py) (subclass of
`rlm.generate_problems.ProblemGenerator`). Four types, round-robin:

| Type | Asks | Answer | Hard branches |
|---|---|---|---|
| T1 `period` | P1/P2/P3 of a date + time | label | fixed national holiday (P3), **Good Friday / regional holiday (NOT P3: trap)**, weekend |
| T2 `run_cost` | cost of P kW from hh:mm for m minutes with hourly prices | € to the cent | partial hours, crossing midnight |
| T3 `bill` | full bill: power (peajes + cargos + margin), energy, bono social, IEE, meter, IVA, per-line rounding | € to the cent | P1 ≠ P2 contracted power, 60-day bills (OOD) |
| T4 `window` | start hour of the cheapest contiguous k-hour window | integer hour | ties (earliest), window at the edge |

Constants are the 2026 values (CNMC Res. 18/12/2025; Orden TED/1524/2025; Circular 3/2020
art. 7.3). Solver sanity checks (real output): Good Friday 2026-04-03 11:00 → `P1`,
2026-12-08 11:00 → `P3`, 2 kW 23:30–00:30 at 0.10/0.20 → `0.30`, 4.6 kW / 30 days /
250 kWh at 0.15 → **64.55 €** (the research hand calculation gives 64.56 €: the one-cent gap
is the rounding convention, which is why the rule sheet fixes "cada línea al céntimo").

```
$ uv run python docs/feasibility/B/pvpc/generator.py --n 2000 --split train --out $TMP/pvpc_train.jsonl
n_problems 2000, n_templates_used 11, unique_param_hashes 2000
  type: period 490, run_cost 504, bill 503, window 503
  reason: working_day 200, weekend 154, fixed_national_holiday 88, moveable_or_regional_holiday_trap 49
  label: P3 322, P1 90, P2 79
  partial_hours: True 460 / False 43;   crosses_midnight: True 8 / False 495
  iee_floor_binds: False 503;   p2_differs: True 141 / False 362
  tie: True 6 / False 497;   best_is_edge: True 151 / False 352
$ uv run python docs/feasibility/B/common/overlap.py pvpc_train.jsonl problems_test.jsonl problems_ood.jsonl
pvpc_train.jsonl (2000) ∩ problems_test.jsonl (20) = 0
pvpc_train.jsonl (2000) ∩ problems_ood.jsonl (100) = 0
problems_test.jsonl (20) ∩ problems_ood.jsonl (100) = 0
```

Findings from the branch table (all fixed or flagged):
- First run had **train∩OOD = 1**: the period type had no OOD region. Fixed: OOD periods
  are in calendar year 2027, train in 2026.
- **`iee_floor_binds` is never True**: the 1 €/MWh floor of the electricity tax only binds
  when (power + energy)/kWh < 0.0196 €/kWh, which no household bill reaches. Dead branch →
  dropped from the task, kept as a corpus fact (gold question).
- `crosses_midnight` is 1.6 % and ties 1.2 %: raise both to ≥10 % in the real generator.
- **Leakage metric is structural for T1 and T4** (the label P1/P2/P3 is in the rule sheet;
  the answer hour is one of the listed hours): 490 + 503 flags. For the numeric types it is
  1/1007. Report leakage per type, not globally.

**OOD split:** 2027 calendar (different Good Friday), 210–300-minute runs crossing more
hours, 59–62-day bills, 16–24-hour price lists with k = 3–4.

**Verifier edge cases** (asserted every run): `p3` = `P3`; `valle`, `P3 (valle)` rejected
(one label only); `12,34` and `12,34 €` = `12.34`; `12.3`, `12.335` rejected (to the
cent); `1.234,56` rejected (thousands separator ambiguity: the model is told to answer with
dot decimals); `21` and `21 h` accepted for an hour, `21:00` rejected; `2,35 o 2,36` rejected.

**Dataset strategy:** 1 (generator) + 2 (mining: ESIOS archive 70 gives the real hourly
PVPC and its TEU breakdown for every day since 2021 → real price lists for T2/T4 and a real
check of T3's peajes+cargos). Sizes: SFT 500, GRPO 1500, test 200 (50 audited), OOD 100.

## 2. Difficulty

<!-- difficulty -->

## 3. External API

**REData (Red Eléctrica)** — <https://www.ree.es/es/apidatos>, no key, CORS open:

```
GET https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real
    ?start_date=2026-09-25T00:00&end_date=2026-09-25T23:59&time_trunc=hour
→ 200; included[type=PVPC].attributes.values = 24 × {"value": 195, "datetime": "2026-09-25T00:00:00.000+02:00"}
```

No documented rate limit (cache per day). Second source, tokenless: ESIOS public archive 70
(`https://api.esios.ree.es/archives/70/download_json?locale=es&date=2026-09-25`) with the
per-hour breakdown; the ESIOS indicators API needs a token (403 without). Gotchas the tool
must handle: DST days with 23/25 values (key on UTC offset), next-day PVPC only after
≈20:15 (RD 216/2014), quarter-hour spot series (96 values) next to hourly PVPC.

## 4. Compute tool and action tool

- **Compute — `bill_calculator(contract, consumption, prices)`** and
  **`cheapest_window(prices, k)`**: exact bill with the date-indexed tax table (2026 had
  IEE 0.5 % and IVA 10 % from 22 March to 31 May, RD-ley 7/2026, then back to 5.11 % and
  21 %) and pro-rating when a price change falls inside the billing period. Why not in the
  head: a bill is 8+ lines of cent-rounded arithmetic, and the tax regime depends on dates.
- **Action — `schedule_appliances(plan)`** (`requires_confirmation=True`): writes an `.ics`
  with the chosen windows and a CSV of expected costs under `data/schedules/`. The grader
  downloads it via `GET /schedules/<id>.ics` and checks that each event starts at the hour
  `cheapest_window` returns for that day's real prices. Sandboxed: local files only, no
  smart-plug or utility account is ever touched.

## 5. Corpus

~10 documents verified, 25–40 reachable (full list in research.md):

| Doc | Pages | Extraction |
|---|---|---|
| Circular CNMC 3/2020 (consolidated, BOE) | 28 | clean text; **formulas are images** |
| CNMC resolution on 2026 peajes | 17 | tables clean with `-layout` |
| RD 216/2014 PVPC (consolidated) | 45 | clean; formulas partly lost |
| Orden TED/1524/2025 (cargos 2026) | ~20 | HTML tables flatten, parseable |
| CNMC "Nueva factura" FAQ | 35 | clean |
| CNMC consumer guide 2022 | 28 | clean |
| Bill-model resolution 2021 (BOE-A-2021-7120) | 18 | clean |
| Consumo Responde bill model | 30 | clean |
| IDAE Guía Práctica de la Energía | 93 | clean but pre-2.0TD (tests "outdated doc" handling) |
| Ley 38/1992 (IEE), RD-ley 7/2026, 18/2026 | HTML | clean |

Licence: BOE texts under the BOE reuse licence (Ley 37/2007) and art. 13 LPI (legal texts
not copyrightable); CNMC/IDAE reuse with attribution is ASSUMPTION (CNMC legal-notice URL
returned 404). Corpus can live in git (small, redistributable) — the best licence position
of the five topics.

**Five gold questions** (source-located in research.md):
1. ¿El 6 de enero es todo P3? ¿Y un festivo autonómico sustituible? → sí; no (excluidos).
   Circular 3/2020 art. 7.3 p. 8.
2. ¿Antes de qué hora se publican los precios PVPC del día siguiente? → antes de las 20:15.
   RD 216/2014 p. 20.
3. Peaje de potencia P1 2.0TD en 2026 → 23,324952 €/kW·año. CNMC Res. 18/12/2025 Anexo I p. 10.
4. Cargo de energía P1 en 2026 → 0,064292 €/kWh. Orden TED/1524/2025 Primero b).
5. ¿Puedo seguir en PVPC con más de 10 kW en valle? → no. CNMC FAQ p. 8.

## 6. Agent — 5 tasks (≥2 tools) with automatic checks

| # | Task | Tools | Automatic check |
|---|---|---|---|
| 1 | "¿Cuál es la hora más barata mañana para poner el lavavajillas 2 h?" | `get_pvpc_prices` (API) → `cheapest_window` | answer hour == `cheapest_window` on the fixture prices |
| 2 | "Mi factura de agosto (4,6 kW, estos consumos por periodo) ¿está bien?" | `get_pvpc_prices` (month) → `bill_calculator` → `search_knowledge_base` (tax regime) | stated total == calculator ±0.01; cites the RD-ley chunk if the period touches 22/03–31/05 |
| 3 | "Prográmame lavadora, secadora y horno esta semana en las horas baratas." | `get_pvpc_prices` ×7 → `cheapest_window` ×3 → `schedule_appliances` | every VEVENT DTSTART equals the reference window; no overlaps if the user said so |
| 4 | "¿El Viernes Santo es valle?" | `search_knowledge_base` → `get_holidays` | answer "no" + cites Circular 3/2020 art. 7.3 chunk id |
| 5 | "¿Cuánto me ahorro poniendo el coche a cargar de 2 a 6 en vez de 19 a 23?" | `get_pvpc_prices` → `run_cost` ×2 | savings == difference of the two reference costs ±0.01 |

**Impossible task:** "¿Cuánto costará la luz el 15 de diciembre de 2027?" → prices do not
exist yet (published ≈20:15 the day before); the agent must say so and not invent a number
(check: no numeric € answer; mentions publication time).

## 7. Domain reward

**Breakdown reward** (the professor's own suggestion for finance: "penalizar respuestas que
den un importe sin desglose"): +0.5 if the `<think>` block contains each bill line (potencia,
energía, bono social, impuesto eléctrico, contador, IVA) with a number, scaled by the
fraction present. Hack: the model lists the six words with junk numbers. Mitigation:
recompute each line from the parameters and reward only lines within ±0.01 of the reference
(parse "impuesto eléctrico: 2,56"); cap at 0.5 so accuracy dominates.

## 8. Risks

| Risk | L | I | Mitigation |
|---|---|---|---|
| Rules change mid-project (new peajes Jan 2027, tax cuts toggled by CPI in 2026) | H | M | Date-indexed constants table + gold questions pinned to a date; turns into a feature ("¿qué cambió en enero?") |
| Base model already good at T4 (argmin over ≤12 numbers) | M | M | Measured in §2; move T4 to longer lists if base >50 % |
| REData undocumented limits / format change / outage | M | M | Daily cache + ESIOS archive fallback + fixtures for the grader |
| Formulas are images in Circular 3/2020 & RD 216/2014 | H | L | Hand-written formula chunks (documented) |
| 16 GB / 384-token budget: T3 bill needs ~8 cent-rounded lines | M | M | Keep T3 ≤ 30 % of GRPO data; measure truncation |
| Disclaimer overhead ("no es asesoramiento") | L | L | One line per answer (finance category) |
| Real consumption data = personal data | L | M | Synthetic consumption; only public price data is real |

## 9. Closest professor example

**"Copiloto fiscal para autónomos"** (finance, exact-to-the-cent). Quote:

> "En la fase 1, que el conjunto de test tenga casos donde el modelo tiene que decidir la
> deducibilidad antes de calcular, no solo sumar. […] La tercera recompensa puede penalizar
> respuestas que den un importe sin desglose."

Difference: the "decide before calculating" step here is *which period / which tax regime
applies* (Good Friday trap, 2026 tax toggles), the data is real and public (REE), and the
action is a schedule, not a tax form. Not one of the 13 examples.

## 10. Scorecard

<!-- scorecard -->
