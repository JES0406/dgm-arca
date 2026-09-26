# 02 — Factura de la luz 2.0TD: calcular, explicar y ahorrar

**One sentence.** Un agente para hogares españoles que recalcula y explica su factura de la luz
(tarifa de acceso 2.0TD), consulta los precios horarios reales de Red Eléctrica y programa en el
calendario cuándo poner los electrodomésticos para pagar menos.

## 1. Verifiable task (phase 1)

Prototype: [`luz/generator.py`](luz/generator.py). Output: [`luz/generator_output.txt`](luz/generator_output.txt).

```
uv run python docs/feasibility/A/luz/generator.py --n 40
```

- **Answer:** the bill total in euros to the cent. Verified numerically with tolerance 0.01 and the comma-aware parser.
- **Parameters:**
  - Days (27–34).
  - Contracted kW in P1/P2, from 8 standard values.
  - Supplier prices: €/kW·día × 2 and €/kWh × 3.
  - kWh per period, with a small-household mode (45 %) that balances the social-bonus-cap branch.
  - Bono social: none / vulnerable / severo, plus category A/B/C.
  - Territory: península / Canarias / Ceuta-Melilla, which sets IVA 21 %, IGIC 3 % or IPSI 1 %.
- **`solve`:** power term, energy term, social-bonus discount with the prorated annual cap, bono financing, electricity tax (IEE) with its €/MWh floor, meter rental and indirect tax. Each concept is rounded half-up to cents before summing. The rule sheet (8 rules) is prepended to every statement.
- **Real output (40/split):** 4 templates, 40/40 distinct answers per split, **0 leaks, 0 param-hash overlap**.
- **Branch table (train/test/OOD):**
  - Territory: península 22/29/33, Canarias 12/8/5, Ceuta-Melilla 6/3/2.
  - Bono: none 17/18/17, vulnerable 14/12/16, severo 9/10/7.
  - The cap binds in 15/13/19 and doesn't in 4/9/1. It was 21 vs 2 before the small-household fix.
  - `p1_eq_p2` True 27/32/26.
  - **The IEE floor never applies (0/40 everywhere).** This is realistic: 5.11 % of any retail price far exceeds 1 €/MWh. So it's a dead branch in the real world. Keep it in the rules and add 5–10 synthetic edge cases (near-zero prices) to the test set so the verifier tests cover it.
- **OOD split:** a mid-period price change (two price sets, two consumption blocks), never in train/test. Statements grow from ~350 to ~650 chars.
- **Legal constants checked against primary sources** (downloaded, parsed with pypdf):
  - IEE 5.11269632 %: **Ley 38/1992 art. 99.1** (p73 of the consolidated BOE PDF). Art. 99.2 floors are 0.5 €/MWh (industrial uses) or 1 €/MWh (rest). Our sheet uses 1 €/MWh.
  - Bono social: RD 897/2017 art. 6.3 says **35 % / 50 %**. The sheet's 42.5 % / 57.5 % are the temporarily raised values (RDL extensions). Whether they are still in force in 2026 is **UNVERIFIED**. The self-contained rule sheet keeps the task well defined either way; for the real tool, check the BOE before phase 2.
  - Meter rental 0.81 €/month single-phase (1.36 three-phase): **CNMC guide p24**. Our 0.026630 €/day = 0.81 × 12 / 365.
  - 2.0TD applies to ≤ 15 kW in every period, with 2 power terms and 3 energy terms: **Circular 3/2020 CNMC art. 6**.
- **Verifier edge cases:**
  1. "79,90 €" / "79.90" / "79,9": all equal, with the comma-aware parser.
  2. The repo's `normalize_number("79,90")` returns **7990**. It is a real bug for any euro topic, so the domain verifier must not use it.
  3. Total vs pre-tax base: a common wrong answer. It must fail (difference ≥ 1 %).
  4. Rounding each concept vs rounding only the total: ±0.01–0.03 €. The tolerance is 0.01, so rule 8 matters. Test it explicitly.
  5. Thousand separators: "1.234,56". This is covered by the parser, with a test.

## 2. Difficulty

PASS1_LUZ

## 3. External API

| API | Docs | Key | Limits | Verified call | Verdict |
|---|---|---|---|---|---|
| **REData (Red Eléctrica)** | https://www.ree.es/es/apidatos | **None** | Not published (ASSUMPTION: fair use) | `GET https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=2026-09-20T00:00&end_date=2026-09-20T23:59&time_trunc=hour` → 200, series **"PVPC" (24 values, first 216.88 €/MWh at 00:00+02:00)** and "Precio mercado spot" (96 quarter-hour values) | Excellent: official, keyless, stable URL scheme for years |
| ESIOS (REE) | https://api.esios.ree.es | Token by e-mail request | — | not called | A fallback with richer data |

Row D is strong.

## 4. Compute and action tools

- **Compute:** `calcular_factura(...)` (the same engine as `solve`), plus `mejor_franja(precios_horarios, duracion_h, kwh)`, which finds the cheapest window for an appliance over the 24 REData prices. The model must not add 24 prices × kWh in its head, and the cent-level answer requires 7 rounded concepts.
- **Action:** `programar_electrodomestico(aparato, inicio, fin)` writes an `.ics` calendar event to `outputs/calendar/`. It is registered with `requires_confirmation=True`. The grader observes the returned path, parses the ICS, and checks that DTSTART equals the window computed by the tool. It is sandboxed because it writes only a local file, with no smart-plug or real calendar.

## 5. Corpus

| Source | URL | Licence | Format | Size | Parse check |
|---|---|---|---|---|---|
| CNMC "Guía de la factura" / consumer guides | cnmc.es | CNMC web reuse with attribution (ASSUMPTION; aviso legal not parsed) | PDF | 3–6 docs × 20–30 pp | `cnmc_guia_2022.pdf`: **65,365 chars, 0.7 % table-like lines**, 67 odd chars (ligatures) |
| CNMC Res. 18-12-2025, 2026 tolls (BOE-A-2025-26348) | boe.es | **BOE: free reuse with attribution** (aviso legal) | PDF/HTML | 11 pp | **32,638 chars, 16.9 % table-like lines**. The tariff tables flatten into one line per group ("2.0 TD 3,233054 0,003283 3.0 TD 2,016722…"), so table-aware chunking is needed |
| Orden TED/1524/2025, 2026 charges (BOE-A-2025-26705) | boe.es | BOE | PDF/HTML | 11 pp | downloaded |
| Circular 3/2020 CNMC (toll methodology) | boe.es | BOE | PDF/HTML | ~40 pp | downloaded, 2.0TD definition found |
| RD 216/2014 (PVPC), RD 897/2017 (bono social), Ley 38/1992 (IEE) consolidated | boe.es | BOE | PDF | 33–81 pp each | parsed with pypdf, text clean |
| OCU/IDAE saving guides | idae.es | IDAE: public reuse (ASSUMPTION) | PDF | 3–5 docs | not checked |

Estimated corpus: 15–25 documents, 400–600 pages, mostly Spanish legal text. This is
exactly the "Spanish domain under-represented in the model" that the brief recommends.

**Five gold questions only answerable from the corpus:**
1. "¿Cuánto vale en 2026 el término de potencia del peaje de transporte 2.0TD en P1?" → **3,233054 €/kW·año** (BOE-A-2025-26348, p6).
2. "¿Y el de distribución en P2?" → **0,440487 €/kW·año** (same table).
3. "¿Cuál es el mínimo del impuesto eléctrico para usos industriales?" → 0,5 €/MWh (Ley 38/1992 art. 99.2.a).
4. "¿Cuánto cuesta el alquiler de un contador trifásico?" → 1,36 €/mes (CNMC guide p24).
5. "¿Qué descuento fija el RD 897/2017 para el consumidor vulnerable severo?" → 50 % (art. 6.3). This also tests the corpus-vs-temporary-RDL conflict: the agent should mention both.

## 6. Agent tasks

1. "¿A qué hora de mañana me sale más barato poner la lavadora 2 h? Añádelo al calendario." → REData + `mejor_franja` + `programar_electrodomestico`. Check: the ICS DTSTART equals the argmin of the 2-h rolling sum of the fetched prices.
2. "Mi factura: 31 días, 4,6 kW, 120/95/210 kWh a [precios], soy vulnerable categoría A: ¿está bien cobrada si me piden 61,37 €?" → `calcular_factura` + KB (bono rules). Check: the boolean plus the correct total.
3. "¿Cuánto pagaría este mes con PVPC si consumo 250 kWh repartidos 30/25/45 %?" → REData (average PVPC by period) + `calcular_factura`. Check: within 0.5 % of a reference computed from the same prices (±1 €).
4. "Vivo en Las Palmas, ¿qué impuesto me aplican en la factura y cuánto es sobre 70 € de base?" → KB + calculator. Check: IGIC 3 %, 2.10 €.
5. "¿Me compensa bajar la potencia de 5,75 a 4,6 kW?": power-term savings over 365 days. → `calcular_factura` ×2. Check: the numeric difference.
- **Impossible task:** "Cámbiame de compañía a la más barata ahora mismo." There's no switching API and it would be a real contract. The agent must decline and point to the CNMC comparator.

## 7. Domain reward

`breakdown_reward`: +1 if the `<think>` contains the 7 concepts of rule 8 with values that, re-summed, give the `<answer>` (checked by regex plus sum). This matches the professor's own suggestion for finance ("penalizar respuestas que den un importe sin desglose").

- **Hacking:** the model can list 7 invented numbers that sum to its answer.
- **Mitigation:** compare each concept against `solve`'s intermediate values (known at training time), with 1/7 credit per correct concept.

## 8. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Regulated values change during the course (bono %, taxes; the 2024–25 temporary IVA/IEE cuts) | High | Medium | Rule sheet in the prompt with a date; the KB carries the dated BOE; the agent cites the version |
| Rule sheet ≈ 1,900 chars + case ≈ 350 chars ≈ 800 tokens prompt; long arithmetic chains need > 384 tokens | High | High for GRPO | Measure the completion-length distribution (§2); raise max_completion to 768; or drop the rule sheet once SFT has taught it (R1 "with-rules" ablation) |
| Decimal-comma verifier bug in the repo's `normalize_number` | Verified | High if unnoticed | Own verifier plus tests (§1) |
| Table-heavy BOE PDFs (16.9 % table-like lines) | Verified | Medium | Use the BOE HTML version (same content, `<table>` tags) and chunk by table row |
| Close to the professor's fiscal-copilot example (row O) | Medium | Low | Different tax base, a real-time API, and the scheduling action |
| Financial disclaimer | Certain | Low | Fixed footer line |

## 9. Closest professor example

**"Copiloto fiscal para autónomos"** (Finanzas). Quote:

> "En la fase 1, que el conjunto de test tenga casos donde el modelo tiene que decidir la
> deducibilidad antes de calcular, no solo sumar. En la fase 2, la herramienta que lee el CSV
> tiene que validar el esquema y devolver errores útiles cuando la factura está mal. En la fase 4,
> valoraría que el agente detecte inconsistencias (una factura sin NIF, un gasto duplicado) y las
> pregunte en vez de tragárselas."

**How ours differs:**
- The "decide before you calculate" steps are the bono cap, the territory tax and the mid-period price change, not deductibility.
- The data comes from a live public API rather than a user CSV.
- The action optimises future consumption instead of filing a form.
- The inconsistency analogue: a bill whose days don't match its date range, or a P1 power above 15 kW (so not 2.0TD). The agent should flag these.

## 10. Scorecard

SCORECARD_LUZ
