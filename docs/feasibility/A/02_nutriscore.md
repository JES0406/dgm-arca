# 02 — Nutri-Score 2023: de la etiqueta a la nota

**One sentence.** Un agente para consumidores y dietistas que calcula el Nutri-Score (algoritmo
2023) a partir de la tabla nutricional, lo contrasta con Open Food Facts por código de barras y
genera una comparativa o lista de la compra con las alternativas mejor puntuadas.

## 1. Verifiable task (phase 1)

Prototype: [`nutriscore/generator.py`](nutriscore/generator.py). Output: [`nutriscore/generator_output.txt`](nutriscore/generator_output.txt).

```
uv run python docs/feasibility/A/nutriscore/generator.py --n 40
```

- **Answer:** the integer score N − P. We grade the integer, not the letter: a 5-way letter can be guessed 20 % of the time, and the letter follows deterministically from the score and category.
- **Categories:**
  - General food, cheese (protein always counts), red meat (protein capped at 2) and beverages (their own tables, sweeteners +4) in train/test.
  - **Fats, oils, nuts and seeds only in OOD.** They use different negative components (energy from saturates, the saturates/lipids ratio with ≥ thresholds) and a different protein cut-off (N ≥ 7).
- **Tables:** Santé publique France, Conditions of Use March 2025, Exhibit 1 Tables 5–10, extracted by the research pass from the downloaded PDF.
- **Oracle self-check:** Open Food Facts' live 2023 breakdown for barcode 8480000160164 (tomate triturado) is energy 0 + sugars 1 + salt 2 − FVL 2 = **1 → B**. Our `score` reproduces it (an assert in `__main__`).
- **Real output (40/split):**
  - 4 templates; nutrient order shuffled per problem; decimal commas.
  - Param-hash overlap 0.
  - At n=200, grades A/B/C/D/E are 17/20/63/57/43 (train). This is after skewing salt, sugar and fat towards realistic low values; the first version was 0/3/6/12/19 of 40, dominated by E.
  - `protein_rule`: dropped 91, counted 62, always 47 (n=200).
- **Leakage:**
  - The first measurement found 4–6/40, all small integer scores matching digits inside decimals ("4" in "4,0 g"). The shared checker now ignores a number that is followed by a decimal part.
  - Remaining 2–3 % coincidences (e.g. "frutas… 0 %" with score 0; "30 %" with score 30) are not derivable from the text and are reported, not hidden.
- **Realism limitation (honest):** product names and macros are sampled independently ("gazpacho, 32 g azúcares, 1902 kJ"). For the real dataset, use **strategy 2**: mine Open Food Facts products whose `nutriscore_version == "2023"` from the JSONL/parquet dump, with our `score` as verifier. Keep only products where our score equals OFF's (label agreement), and keep the generator for OOD and edge-case coverage.
- **Verifier edge cases:**
  1. Strict ">" vs "≥" at thresholds: general tables use strict ">" (≤335 → 0), but the fats ratio uses "≥" per CoU Table 8. We need unit tests at every boundary (335, 3.4, 0.2, 80 %…).
  2. Negative scores ("-3") need sign-aware parsing. `NumericVerifier` handles "-3"; "− 3" with a Unicode minus must be normalised.
  3. Letter-only answers ("C") have no number, so they fail. Should the domain reward give partial credit if the letter matches?
  4. Water is always A (score irrelevant). This is excluded from generation; add one test.
  5. Missing fibre (OFF often null means 0 points): in mined data, treat null as 0, as OFF does, and document it.

## 2. Difficulty

PASS1_NUTRI

## 3. External API

| API | Docs | Key | Limits | Verified call | Verdict |
|---|---|---|---|---|---|
| **Open Food Facts** | https://openfoodfacts.github.io/openfoodfacts-server/api/ | None for reads; a custom **User-Agent is required** | **15 product reads/min/IP, 10 searches/min/IP**; the IP can be banned above that | `GET /api/v2/product/8480000160164.json` → "Tomate triturado", `nutriscore_version: "2023"`, and the full per-component points (energy 0, sugars 1, salt 2, FVL 2; score 1, grade b) | Good and semantically perfect (it doubles as a test oracle). The rate limit forces a cache and backoff in the tool |

Data licence: ODbL (database), DbCL (contents), images CC BY-SA. Bulk dumps: CSV 1.28 GB gz,
JSONL 13 GB, HF parquet 7.9 GB.

## 4. Compute and action tools

- **Compute:** `nutriscore(nutrients, category)` returns N, P, per-component points, score and letter. The model must not do it in its head: 7–9 table lookups across 5 category rule sets.
- **Action:** `generar_lista_compra(productos)` writes a Markdown/PDF comparison (each product, its letter and the better alternative) to `outputs/listas/`, with `requires_confirmation=True`. The grader observes the file path and content: the letters must match the computed ones.

## 5. Corpus

| Source | URL | Licence | Format | Size | Parse check |
|---|---|---|---|---|---|
| SpF Conditions of Use (Mar 2025), with the tables | santepubliquefrance.fr | **UNVERIFIED**: the CoU licenses the logo, and no document reuse licence was found. Cite, don't redistribute (keep a download script) | PDF | 81 pp | **230,405 chars, 3.4 % table-like lines**; minor ligature splits ("fro m") |
| SpF Q&A updated algorithm V11 | same | UNVERIFIED | PDF | 58 pp | extracted OK |
| SpF scientific committee update report 2022 | same | UNVERIFIED | PDF | 135 pp | extracted OK |
| AESAN sustainable dietary recommendations 2022 | aesan.gob.es (a mirror used; the AESAN URL gave 404) | AESAN aviso legal: reuse with citation (from a search summary) | PDF | 60 pp | **220,185 chars, 2.6 % table-like, 0 garbage** |
| EU Reg. 1169/2011 (food information to consumers) | EUR-Lex | EUR-Lex reuse | HTML | ~46 pp | **The PDF download failed (HTTP 202 bot challenge, empty body)**; use HTML |
| EFSA opinions | efsa.onlinelibrary.wiley.com | CC BY-ND (derivatives unclear for chunking) | PDF | optional | not checked (403) |

**Main weakness:** the most authoritative sources (SpF) are in English/French, with an unclear reuse
licence. The Spanish sources (AESAN) are about diet in general, not the algorithm.

**Five gold questions:**
1. "¿Desde cuándo es obligatorio el algoritmo actualizado en Francia y cuánto dura la transición?" → 16 Mar 2025, 24 months (CoU).
2. "¿Por qué la leche pasa a clasificarse como bebida en el algoritmo nuevo?" (Q&A V11).
3. "¿Qué edulcorantes cuentan como 'no nutritivos' para los 4 puntos?" (Q&A Appendix 3).
4. "¿Cuántas raciones de frutos secos recomienda la AESAN?" → 3 or more per week, per the report (the sample chunk mentions 1–2 daily raciones from the Mediterranean pyramid). A good *ambiguous* gold item.
5. "¿Qué productos quedan excluidos de llevar Nutri-Score?" (CoU scope section).

## 6. Agent tasks

1. "Compara por código de barras 8480000160164 y 8410076472663, ¿cuál tiene mejor Nutri-Score? Hazme la lista." → OFF ×2 + `generar_lista_compra`. Check: the chosen product equals the lower score.
2. "Esta etiqueta [valores] dice Nutri-Score A, ¿es verdad?" → `nutriscore` + KB (category rule). Check: the boolean.
3. "¿Por qué este yogur bebible puntúa distinto que el yogur normal?" → KB (milk drinks = beverages) + `nutriscore` ×2. Check: both scores correct, and the category difference is cited.
4. "Recalcula el Nutri-Score de este aceite y dime qué regla especial se aplica" → `nutriscore` (fat category) + KB. Check: the score.
5. "¿Qué nota tendría esta galleta si reducen la sal a la mitad?" → `nutriscore` ×2. Check: the delta.
- **Impossible task:** "Dime si este producto es sano para mi hijo diabético." A medical judgement: the agent must decline, give the Nutri-Score only, and refer to a professional.

## 7. Domain reward

`component_reward`: 1/7 per correct component point (energy, sugars, sat fat, salt, protein, fibre, FVL) found in the `<think>` in a fixed format "energía: k". It is dense and aligned with the user's question ("¿qué le baja la nota?").

- **Hacking:** writing all components without using them. They're checked against the truth, so writing them is doing the task.
- **Risk:** format coupling. Mitigation: a lenient regex.

## 8. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| OFF rate limit 15/min during grading | Medium | Medium | Cache, backoff, User-Agent; tasks use ≤ 3 lookups |
| Corpus licence of SpF documents unclear | Medium | Medium (completeness: licence documented) | Don't redistribute; a download script plus a citation-only rationale |
| Health topic: disclaimer in every answer | Certain | Low | Fixed footer, per the professor's rule |
| Synthetic labels unrealistic | Verified | Medium | Mine OFF (strategy 2) as the main train source |
| Boundary semantics (> vs ≥) mis-specified | Medium | High (silent label noise) | Cross-check 500 OFF products: our score equals OFF's 2023 score; report the agreement % |
| Task too table-lookup-like (little "reasoning") | Medium | Medium (interpretation) | Multi-product comparisons and category edge cases as the harder family |

## 9. Closest professor example

No close example. The nearest is **"Asistente de interacciones y posología"** (Farmacia/salud), for the health
disclaimer and the unit discipline. Quote:

> "En la fase 1 miraría sobre todo el verificador de unidades (mg/kg/día frente a mg/dosis es el
> error clásico) y que el conjunto de test tenga casos límite: neonatos, obesidad, diálisis."

**How ours differs:** food rather than drugs; the "casos límite" are category switches (cheese,
red meat, beverages, fats) and threshold boundaries; and the API is also a label oracle.

## 10. Scorecard

SCORECARD_NUTRI
