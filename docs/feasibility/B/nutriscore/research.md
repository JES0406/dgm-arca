# Nutri-Score 2023 & food labelling — research evidence (subagent report, 2026-09-26)

Collected by a research subagent of Agent B. Samples (FAQ V11 PDF, SPF xlsx, OFF JSON,
Reg. 1169/2011) stored under the job's tmp dir, not committed.

## 1. Algorithm (verified against two official SPF sources)
- **SPF Q&A V11** (17 Mar 2025, 58 pp):
  <https://www.santepubliquefrance.fr/sites/default/files/rdd/document/FAQ-updatedAlgo-V11.pdf>
- **SPF official calculator (xlsx)** — usable as grader oracle:
  <https://www.santepubliquefrance.fr/sites/default/files/rdd/document/Nutri-Score_Updated-algorithm_20240404.xlsx>
  Formulas and "Scenario" thresholds match the FAQ tables.
- Background: 2022 main report (135 pp), beverages report V2-2023 (104 pp), both on SPF.

Reading rule: each cut = value *above which* you get that many points (xlsx uses `<=`).

**General foods (incl. cheese, red meat)** — FAQ Tables 5–6 pp. 27–28, N 0–55:
energy kJ steps of 335 (0–10); sat. fat 1…10 g (0–10); sugars 3.4, 6.8, 10, 14, 17, 20,
24, 27, 31, 34, 37, 41, 44, 48, 51 (0–15); salt steps of 0.2 g up to 4.0 (0–20); proteins
2.4, 4.8, 7.2, 9.6, 12, 14, 17 (0–7); fibre 3.0, 4.1, 5.2, 6.3, 7.4 (0–5); FVL % >40 → 1,
>60 → 2, >80 → 5. Score: if N < 11 or cheese, N − P; else N − fibre − FVL (p. 28).
Red meat: protein points capped at 2 (pp. 27–28), applies at ≥20 % red meat (p. 19).
Letters (pp. 32–33): A ≤ 0, B 1–2, C 3–10, D 11–18, E ≥ 19.

**Fats, oils, nuts, seeds** — Tables 7–8 pp. 29–30: energy from saturates = sat. fat × 37
kJ, cuts 120…1200 (0–10); sat/lipids ratio % <10 → 0, 16, 22 … 64 (1–9), ≥64 → 10; protein
dropped when N ≥ 7. Letters: A ≤ −6, B −5…2, C 3–10, D 11–18, E ≥ 19.

**Beverages (per 100 mL)** — Tables 9–10 pp. 31–32: energy 30, 90, 150, 210, 240, 270,
300, 330, 360, 390 (0–10); sugars 0.5, 2, 3.5, 5, 6, 7, 8, 9, 10, 11 (0–10); sweeteners +4;
protein 1.2 … 3.0 (0–7); FVL >40 → 2, >60 → 4, >80 → 6; score N − P always. Letters: A water
only, B ≤ 2, C 3–6, D 7–9, E ≥ 10. Milk/drinkable yoghurt/plant drinks = beverages; soups =
foods (p. 16).

Caveats: the letter table in the FAQ is an image (checked visually + xlsx). xlsx beverage
salt formula has a boundary bug (`G3<3.2`).

**Transition / Spain:** in force 1 Jan 2024 (DE, BE, CH, NL), 5 Mar 2024 (LU), 16 Mar 2025
(FR); 24-month transition (FAQ pp. 6–7). AESAN (Wayback copy of the page updated
27/06/2025): from 1 Jan 2026 Spanish products with Nutri-Score must use the new algorithm.
ASSUMPTION: still voluntary in Spain. Old AESAN URLs now 404.

## 2. Open Food Facts API
`curl -A "ARCA-feasibility/0.1 (email)" "https://world.openfoodfacts.org/api/v2/product/8410000810004.json?fields=code,product_name,nutriscore_grade,nutriscore_score,nutriscore_version,nutriscore,nutriments"`
→ HTTP 200: `nutriscore_grade:"e"`, `nutriscore_score:24`, `nutriscore_version:"2023"`; the
`nutriscore.2023` object gives per-component points (energy 2007.7 kJ → 5, sugars 38 → 11,
sat. fat 5.4 → 5, salt 0.73 → 3, fibre 2.7 → 0) and category flags — recomputed by hand,
match. No key; custom User-Agent required; 15 req/min/IP product reads, 10 req/min search;
ODbL (<https://openfoodfacts.github.io/openfoodfacts-server/api/>). Search endpoint returned
an HTML "temporarily unavailable" page twice → grader must use frozen snapshots.

## 3. Corpus (~30 docs)
- SPF Nutri-Score page links 20 PDFs + xlsx (FAQ EN/FR, reports, conditions of use 2025,
  charter). Licence ASSUMPTION (logo is a trademark).
- EUR-Lex Reg. 1169/2011 ES (46 pp):
  <https://eur-lex.europa.eu/legal-content/ES/TXT/PDF/?uri=CELEX:32011R1169>; reuse allowed
  (Decision 2011/833/EU). Reg. 1924/2006 (claims) likewise.
- AESAN new site: Commission Q&A on 1169/2011, guidance, tolerances/rounding guide 2012
  (17 pp ES), summary table. Licence ASSUMPTION.
- Extraction: regulation clean (two-column interleave on article pages, annex tables
  readable); FAQ point tables extract as column text; letter table and flow diagrams are
  images → hand-written chunk or OCR.

## 4. Gold questions
1. Sodium from salt; rounding rules? → salt ÷ 2.5; no specific rounding. FAQ V11 p. 12.
2. Liquid food declaring per 100 g and per 100 mL → per 100 g. FAQ V11 p. 12.
3. Red-meat rule threshold → ≥20 % red meat. FAQ V11 p. 19.
4. Entry into force FR / LU → 16 Mar 2025 / 5 Mar 2024. FAQ V11 p. 6.
5. Nutrition declaration exemption → largest surface < 25 cm². Reg. 1169/2011 Annex V item 18.
   (Alt.: salt < 1 g/100 g rounded to 0.01 g — EU tolerances guide Cuadro 4 p. 16.)

## 5. Model knowledge (ASSUMPTION, no model run by the subagent)
Small models likely know the 2017 algorithm (sugars 4.5 g steps, sodium 90 mg steps,
protein 1.6 steps, old beverage letters) and will mix it with 2023. Gotchas: salt vs
sodium; per 100 g vs 100 mL; ">" at each cut; fats use energy from saturates; water only
A beverage; sweeteners and FVL % must be given explicitly.
