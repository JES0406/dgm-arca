# 02 — Nutri-Score (2023 algorithm) & food-labelling assistant

**One sentence.** Un agente para pequeños productores y técnicos de etiquetado que calcula
el Nutri-Score con el algoritmo actualizado de 2023 a partir de la tabla nutricional,
contrasta el producto con Open Food Facts, responde dudas del Reglamento 1169/2011 y genera
el informe de etiqueta.

User: a small Spanish food producer or a labelling technician. Since 1 Jan 2026 products
carrying Nutri-Score in Spain must use the updated algorithm (AESAN, see research), and the
tables changed substantially from 2017 (sugars, salt, protein, beverages). Today they use the
SPF Excel or a consultant.

Evidence: [`nutriscore/research.md`](nutriscore/research.md).

---

## 1. Verifiable task (phase 1)

Prototype: [`nutriscore/generator.py`](nutriscore/generator.py). Tables from SPF Q&A V11
(Tables 5–10, pp. 27–33), cross-checked by the research agent against the official SPF
calculator xlsx. Answer = final score (integer) or letter A–E. Categories in train/test:
general food, cheese, red-meat product, beverage; **fats/oils/nuts/seeds held out for OOD**
(different tables: energy from saturates, saturates/lipids ratio, protein dropped at N ≥ 7).

Oracle check (asserted every run): Open Food Facts' own 2023 computation for Oreo (energy
2007.7 kJ → 5, sugars 38 → 11, sat. fat 5.4 → 5, salt 0.73 → 3, fibre 2.7 → 0) gives
N = 24, score 24, E — our `solve` returns `24`.

```
$ uv run python docs/feasibility/B/nutriscore/generator.py --n 2000 --split train --out $TMP/ns_train.jsonl
(first version) letter: E 1137, D 479, C 257, B 114, A 13;  n_ge_11 True 1756 / False 244;
                red_meat_cap_binds True 7 / False 493;  n_templates 3
(stratified)    n_problems 2000, n_templates_used 5, unique_param_hashes 2000
  category: general 500, cheese 500, red_meat 500, beverage 500;  ask: score 1004, letter 996
  letter: A 318, B 443, C 468, D 385, E 386
  n_ge_11: True 1046 / False 954;  protein_counted: True 1023 / False 477
  red_meat_cap_binds: True 202 / False 298;  sweeteners: True 136 / False 364
$ ... --split ood → category fat 100; letter A 19, B 18, C 16, D 27, E 20; protein_dropped True 75 / False 25
$ overlap.py → train∩test 0, train∩ood 0, test∩ood 0
```

**What the branch table caught:** uniform nutrient ranges gave 57 % E and 0.6 % A, with the
"protein not counted" branch in 88 % of problems and the red-meat cap binding in 1.4 % —
the model could score well by always answering E. Fix: rejection-sample to a uniformly drawn
target letter and mix three "healthiness" scales. This is the "todo el peso en la rama
fácil" error, found and fixed with numbers.

Leakage: the letter answers A–E are listed in the rule sheet and scores are small integers
that collide with table values, so the substring metric is high (1715/2000) but meaningless
here; report per answer kind. Real leakage risk is elsewhere: **the OFF product already
carries `nutriscore_grade`** — any mined problem must strip it from the statement.

**Verifier edge cases:** `c` = `C`, `Letra: C`, `Nutri-Score: E` accepted; `C o D` rejected;
`−3` (Unicode minus) = `-3`; `3` ≠ `-3`; `+4` = `4`; `4.0` rejected (scores are integers).

**Dataset strategy:** 1 (generator) + 2 (mining Open Food Facts: products with complete
nutriments and `nutriscore_version: "2023"` give real (table, score) pairs, labelled by OFF
and re-verified by our `solve` — disagreements are themselves interesting). Sizes: SFT 600,
GRPO 2000, test 200 (50 audited incl. 30 real OFF products), OOD 100 (fats/oils/nuts).

## 2. Difficulty

<!-- difficulty -->

## 3. External API

**Open Food Facts** — <https://openfoodfacts.github.io/openfoodfacts-server/api/>

```
$ curl -A "ARCA-feasibility/0.1 (email)" "https://world.openfoodfacts.org/api/v2/product/8410000810004.json?fields=code,product_name,nutriscore_grade,nutriscore_score,nutriscore_version,nutriscore,nutriments"
→ 200: nutriscore_grade "e", nutriscore_score 24, nutriscore_version "2023",
       nutriscore.2023.components: energy 2007.7→5, sugars 38→11, saturated_fat 5.4→5, salt 0.73→3, fiber 2.7→0
```

No key; custom User-Agent required; 15 req/min/IP (product), 10 req/min (search); data
ODbL. **Search endpoint returned an HTML "temporarily unavailable" page twice** during the
research run → the grader-facing tool must serve frozen JSON snapshots with live lookup as a
bonus. Staging server exists (world.openfoodfacts.net).

## 4. Compute tool and action tool

- **Compute — `nutriscore(table, category, fvl_pct, sweeteners)`** returning N and P
  components and the letter; plus `convert(sodium→salt, kcal→kJ, per-serving→per-100 g)`.
  Why not in the head: 7–9 threshold tables with 10–20 cuts each, category-dependent rules,
  and the model's prior is the 2017 algorithm (ASSUMPTION to be measured).
- **Action — `write_label_report(product)`** (`requires_confirmation=True`): renders an
  HTML/PDF label sheet (nutrition table in the Reg. 1169/2011 Annex XV order, Nutri-Score
  with per-component breakdown, allergen list) into `data/reports/<sku>.html`. Grader
  checks the file exists and the letter/score inside equals `nutriscore()`. Sandboxed:
  local files; OFF writes are never enabled.

## 5. Corpus

~30 documents:
- SPF Nutri-Score page: ~20 PDFs + xlsx (Q&A V11 58 pp, 2022 main report 135 pp, beverages
  report 104 pp, conditions of use 2025, charter). Licence ASSUMPTION (logo is a registered
  trademark; documents are public).
- EUR-Lex: Reg. 1169/2011 (ES, 46 pp) and Reg. 1924/2006 — reuse explicitly allowed
  (Decision 2011/833/EU).
- AESAN: Commission Q&A on 1169/2011, general guidance, tolerances/rounding guide (17 pp
  ES), summary table. Licence ASSUMPTION (Spanish public sector). Old AESAN URLs 404 after a
  site restructure; Wayback copies needed for some.

Extraction (pdftotext): regulation clean (two-column interleave on article pages; annex
tables readable); FAQ point tables extract as column text; **the letter-threshold table and
the flow diagrams are images** → hand-written chunk.

**Five gold questions** (research.md):
1. ¿Cómo se obtiene el sodio a partir de la sal y hay redondeos específicos? → sal ÷ 2,5; no. FAQ V11 p. 12.
2. Alimento líquido con valores por 100 g y por 100 mL: ¿cuál se usa? → por 100 g. FAQ V11 p. 12.
3. ¿A partir de qué proporción de carne roja se aplica el tope de proteínas? → ≥ 20 %. FAQ V11 p. 19.
4. ¿Cuándo entró en vigor el algoritmo actualizado en Francia y en Luxemburgo? → 16/03/2025; 05/03/2024. FAQ V11 p. 6.
5. ¿Qué envases están exentos de la declaración nutricional por tamaño? → superficie mayor < 25 cm². Reg. 1169/2011 Anexo V punto 18.

## 6. Agent — 5 tasks with automatic checks

| # | Task | Tools | Check |
|---|---|---|---|
| 1 | "Mi galleta tiene esta tabla (…). ¿Qué Nutri-Score le toca con el algoritmo nuevo?" | `nutriscore` → `search_knowledge_base` (category rule) | letter == `nutriscore()`; cites FAQ table chunk |
| 2 | "Compárala con las Oreo (EAN 8410000810004)." | `off_lookup` → `nutriscore` ×2 | both scores correct; states the difference in points |
| 3 | "¿Qué cambio de receta mínimo la sube de D a C?" | `nutriscore` in a loop (what-if) | proposed change, re-scored, gives C |
| 4 | "Mi bebida de avena lleva edulcorante: ¿cómo afecta?" | `search_knowledge_base` (beverage rules) → `nutriscore` | answer contains +4 N points; letter correct |
| 5 | "Hazme la ficha de etiqueta del chorizo con su Nutri-Score." | `nutriscore` → `write_label_report` | file exists; letter/score inside == reference; red-meat cap applied |

**Impossible task:** "¿Qué Nutri-Score tendrá este producto con el algoritmo de 2030?" (or a
product with no nutrition table and an EAN unknown to OFF) → the agent says it cannot and
does not guess a letter.

## 7. Domain reward

**Component consistency**: reward the fraction of the five/six component point values in
the `<think>` block that match the reference components (energy, sugars, sat. fat, salt,
protein, fibre, FVL). User value: a technician needs to know *which* nutrient to change.
Hack: dump every possible value or copy the table header. Mitigation: parse "azúcares: 11"
style lines, count only the first value per component, penalise more than one value per
component; weight 0.3 vs accuracy 1.0.

## 8. Risks

| Risk | L | I | Mitigation |
|---|---|---|---|
| Base model confuses 2017 and 2023 tables | H | + (good for RL/RAG story) | Measure: base with and without the rule sheet |
| Category classification (is it a beverage? cheese? red meat ≥ 20 %?) is ambiguous in the wild | M | M | Category given explicitly in phase 1; agent asks when unsure; gold questions on p. 16–19 rules |
| OFF instability / crowdsourced errors | H | M | Frozen snapshots; label_source="off" rows never in test unless re-verified |
| Letter table & diagrams are images | H | L | Hand-written chunk, documented |
| Health-adjacent → disclaimer overhead | M | L | One-line disclaimer: informative, not a regulatory filing |
| Trademark/licence of SPF documents | L | M | Use for RAG only, link rather than redistribute |
| 16 GB / 384 tokens: 7 components + rule sheet in prompt (~450 tokens) | M | M | Rule sheet only for SFT warm-up; GRPO without it ("recall" ablation) |

## 9. Closest professor example

**"Redactor de fichas de producto con verificación contra el catálogo"** (marketing,
strict extraction) and, for the rule engine, **"Navegador de ayudas"**. Quote:

> "La fase 1 es un caso bonito de recompensa de formato llevada al extremo: el esquema JSON
> es la recompensa. Quiero ver cómo evoluciona la tasa de JSON válido durante GRPO y qué
> campos se resisten."

Difference: the verifiable task is a published scoring algorithm (not extraction), with a
known model prior that is *wrong* (2017 tables) — a clean setting for "RL corrects a
miscalibrated prior" and for RAG earning its place. Not one of the 13 examples.

## 10. Scorecard

<!-- scorecard -->
