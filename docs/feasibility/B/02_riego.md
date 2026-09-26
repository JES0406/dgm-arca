# 02 — FAO-56 irrigation scheduler for small farms and allotments

**One sentence.** Un agente para huertos y pequeñas explotaciones que calcula cuánto y
cuándo regar (método FAO-56 con la ETo real de la semana), responde dudas de las guías de
riego españolas y deja programado el calendario de riego.

User: allotment holders and smallholders (e.g. Murcia, Almería, Valencia) with drip
irrigation and no agronomist. Today they water "by eye" or follow regional SMS services.

Evidence: [`riego/research.md`](riego/research.md).

---

## 1. Verifiable task (phase 1)

Prototype: [`riego/generator.py`](riego/generator.py) with FAO-56 Table 11/12/22 values
(verified with page numbers in research.md). Types: T1 Kc on day d (Eq. 66), T2 weekly net
need Σ(Kc·ETo) − 0.8·rain (≥0), T3 drip minutes/day (gross = net/0.9, t = gross·area/(n·q),
ceil), T4 RAW = p·1000·(θFC − θWP)·Zr. OOD: crops never in train (maize, olive).

Oracle (asserted): FAO-56 Example 37 p. 168 → RAW 64 mm.

```
(first version)
$ overlap.py rg_train.jsonl problems_test.jsonl problems_ood.jsonl
rg_train.jsonl (2000) ∩ problems_test.jsonl (20) = 8        ← leakage
  type: kc 420, net_week 731, drip_min 730, raw 119          ← raw space exhausted (5×3×8 = 120)
(after hash-partitioned splits + continuous θ and Zr)
n_problems 2000, templates 8, unique hashes 2000
  type: kc 352, net_week 558, drip_min 556, raw 534
  stage: development 507, mid 372, late 324, initial 263
  stage_change_in_week: True 182 / False 932;  rain_cancels: True 87 / False 1027
rg_train.jsonl (2000) ∩ problems_test.jsonl (20) = 0;  ∩ ood = 0;  test ∩ ood = 0
```

**The key finding of this prototype: train∩test = 8/20 in the first version** — the Kc type
has only ~5 crops × ~140 days ≈ 700 parameter sets and RAW had 120, so independent sampling
of train and test collided. Fix: hash-partitioned splits (`sha1(params) % 10 == 0` ⇒ test)
so a parameter set can only ever live in one split, and continuous soil/root parameters.
The Kc type remains small (≈700 combinations): the model can memorise it, which also makes
it a good "memorisation vs reasoning" probe.

**Verifier edge cases:** tolerance = half a unit of the asked precision (`0.84` needs two
decimals; `23,45` accepted for `23.4`; `41.6` accepted for `42` minutes, `43` rejected;
`unos 42` rejected); units `mm`, `min`, `L/m²` stripped.

**Sizes:** SFT 500, GRPO 1500, test 200, OOD 100 (maize, olive). Strategy 1 + optional 4
(reverse construction from Spanish guide examples, e.g. Cajamar's 23 min/day).

## 2. Difficulty

<!-- difficulty -->

## 3. External API

**Open-Meteo** forecast with daily `et0_fao_evapotranspiration` (no key):

```
GET https://api.open-meteo.com/v1/forecast?latitude=37.98&longitude=-1.13
    &daily=et0_fao_evapotranspiration,precipitation_sum,temperature_2m_max,temperature_2m_min
    &timezone=Europe/Madrid&forecast_days=7
→ 200: ETo [4.04, 3.25, 2.86, 2.80, 3.74, 3.51, 2.33] mm; rain [0, …, 0.30]
```

Terms: non-commercial, <10,000 calls/day, 600/min, CC-BY 4.0. Official alternative **SIAR
(MAPA)** needs a token tied to a **NIF/NIE** registration (30 req/min, 1,000/day) → optional;
AEMET OpenData needs a key and has no ETo.

## 4. Compute tool and action tool

- **Compute — `water_balance(crop, sowing_date, soil, eto[], rain[], system)`**: daily
  FAO-56 soil-water balance (Dr, Ks, RAW trigger) → irrigation events and run times. Why not
  in the head: 7–14 days of multiply-accumulate with stage interpolation and a depletion
  state.
- **Action — `write_irrigation_schedule`** (`requires_confirmation=True`): `.ics` + CSV for
  the controller in `data/riego/<plot>/`. Grader checks event durations == `water_balance`.
  Sandboxed: never talks to a real irrigation controller.

## 5. Corpus

~25 documents found, 12 downloaded: FAO-56 (EN HTML, ES PDF), FAO TM3, FAO-66, MAPA hoja
divulgadora 17/1990 (24 pp, **OCR errors**), MAPA Kc and effective-rain sheets, Calera et al.
2016 (19 pp), IFAPA strawberry balance (19 pp), NEIKER (12 pp), IVIA Fichas 2/8/9 (**Ficha 2
garbled layers; Ficha 8 table is an image**), Cajamar Almería 2005 (9 pp, table-driven),
SIAR manual. **Licence is the weak point:** FAO-56 1998 "All rights reserved"; InfoRiego
"Todos los derechos reservados"; Cajamar private; MAPA/IVIA reuse ASSUMPTION. FAO-56 PDF
tables fuse footnote superscripts into numbers ("1.152" = 1.15 + note 2) → hand-curate
Tables 11/12/19/22 as JSON; RAG only for prose.

**Five gold questions:** tomato p and Zr → 0.40, 0.7–1.5 m (FAO-56 T22 p. 163); Example 37
TAW/RAW → 160 / 64 mm (p. 168); minimum wetted share in horticulture → 70 % (MAPA HD 17/1990
p. 9); Cajamar minutes/day → 23 (p. 4); Calera vineyard NDVI 0.4 → Kcb 0.48, 3.12 → 2.2
mm/day (p. 12).

## 6. Agent — 5 tasks with automatic checks

| # | Task | Tools | Check |
|---|---|---|---|
| 1 | "Tomates trasplantados el 1 de mayo en Murcia, 20 goteros de 2 L/h en 10 m²: ¿cuánto riego esta semana?" | `get_et0` (API) → `water_balance` | minutes/day == reference on the fixture ETo |
| 2 | "¿Qué Kc tiene la lechuga a los 35 días y de dónde sale?" | `search_knowledge_base` → `kc_on` | value == reference; cites FAO-56 Table 12 chunk |
| 3 | "Ha llovido 18 mm el martes, ¿cambio el riego?" | `get_et0` → `water_balance` (with rain) | new schedule == reference |
| 4 | "Prográmame el riego de las dos próximas semanas." | `get_et0` ×2 → `water_balance` → `write_irrigation_schedule` | `.ics` durations == reference |
| 5 | "Mi suelo es arcilloso y las raíces llegan a 0,6 m: ¿cada cuánto riego?" | `search_knowledge_base` (soil table) → `water_balance` | RAW and interval == reference |

**Impossible task:** "¿Cuánto regar el aguacate tropical en mi azotea de Burgos?" → crop not
in tables/corpus; agent says so rather than inventing a Kc.

## 7. Domain reward

**Unit discipline**: reward stating the unit at each step (mm/día, L/m², L/h, min) and the
final unit matching the question. The professor's own suggestion for pharmacy/chemistry
("unidades"). Hack: sprinkle units everywhere. Mitigation: check the unit adjacent to the
*final* number and to the gross-depth line only.

## 8. Risks

| Risk | L | I | Mitigation |
|---|---|---|---|
| Corpus licence (FAO-56 all rights reserved; noisy Spanish PDFs) | H | M | RAG over local copy, not redistributed; hand-curated tables |
| Regional Kc and effective-rain conventions disagree (MAPA 70/−24 vs FAO 75/−25) | H | M | Fix one convention in the rule sheet; gold questions on the disagreement |
| Kc type has a tiny space (≈700) → memorisation | H | L | Keep it ≤20 %; use as memorisation probe |
| Open-Meteo non-commercial terms, SIAR needs NIF | L | M | Coursework is non-commercial; SIAR optional |
| Nobody in team farms (ASSUMPTION) | M | M | Motivation in the defence |
| Model already knows FAO-56 basics | M | M | Measured in §2 |

## 9. Closest professor example

**"Tutor de química"** (generator + unit reward) — no agriculture example exists. Quote:

> "Aquí es donde más sentido tiene el reto de 'SFT memoriza, RL generaliza': entrenad con
> unas familias de reacciones y evaluad con otras."

Here: train with 5 crops, evaluate on maize and olive.

## 10. Scorecard

<!-- scorecard -->
