# 02 — PER boating-licence navigation tutor

**One sentence.** Un tutor para quien prepara el examen teórico del Patrón de Embarcaciones
de Recreo (PER) que corrige los ejercicios de navegación paso a paso, responde dudas del
reglamento con cita al BOE y prepara un plan de travesía con la meteo real.

User: PER candidates (tens of thousands per year, ESTIMATE) and nautical schools. Today:
paper manuals and past papers without explanations.

Evidence: [`per/research.md`](per/research.md).

---

## 1. Verifiable task (phase 1)

Two sources, which is this topic's strength:

1. **Generator** ([`per/generator.py`](per/generator.py)) for the text-solvable arithmetic
   of RD 875/2014 UT10–UT11: T1 Rv from Ra + dm + Δ, T2 Ra from Rv (inverse), T3 declination
   update to the nearest 0.5°, T4 ETA (HH:MM). OOD = *chained* declination update → Rv
   (two-step family never in train).
2. **Mining (strategy 2): official DGMM past papers with answer keys** — ≈22 sittings
   (2016 → June 2026) × ≈4 PER variants × 45 MCQ ≈ **3,500–4,000 real questions with gold
   letters** (ESTIMATE from the April 2026 paper; older PDFs may be scanned). Verified: April
   2026 paper (147 pp, text layer) + key align (Q38 = C "suma algebraica de dm y desvío").

Oracle (asserted): 6°40′W (1992), 8′E/yr, 23 years → 3°36′W → `-3.5` (Greenwich Náutica
worked example).

```
$ uv run python docs/feasibility/B/per/generator.py --n 2000 --split train --out $TMP/per_train.jsonl
n_problems 2000, n_templates_used 12, unique_param_hashes 2000, answer_leaked 66
  type: true_course 500, compass_course 499, declination 501, eta 500
  wraps (crosses 000/360): True 55 / False 944     (first version: 10 / 990)
  signs_opposite (dm and Δ): True 419 / False 580
  sign_flip (declination E↔W over the years): True 58 / False 443
  crosses_midnight: True 54 / False 446            (first version: 5 / 495)
$ overlap.py → train∩test 0, train∩ood 0, test∩ood 0
```

Branch fixes: the two hard cases — crossing 000/360 and arriving after midnight — were at
1 %; biased sampling raised them to 5.5 % and 11 %.

**Verifier edge cases:** `45`, `045°`, `45º` = `045`; `3,5 W` = `-3.5`, `3.5` ≠ `-3.5`;
`3,5° E` = `3.5`; `9:05`, `9h05` = `09:05`, `09:5` rejected; `360` ≠ `000`; `045 o 046`
rejected.

**Sizes:** generator SFT 500 / GRPO 1500 / test 200 / OOD 100; mined MCQ as a second test
family (not RL-trained: MCQ with 4 options gives a 25 % guessing floor and invites reward
hacking by letter priors).

## 2. Difficulty

<!-- difficulty -->

## 3. External API

- **Open-Meteo Marine + Forecast** (no key): marine call off Valencia returned wave height
  0.20 m, direction 74°, period 6.15 s; forecast call **first returned `{"reason":"The
  service is overloaded","error":true}`**, retry succeeded (wind 5.6 kn from 102°, 1019.2
  hPa). Needs retry/backoff + fixtures. Tide only as modelled `sea_level_height_msl`.
- **NOAA geomagnetic calculator** (declination for passage plans): key required (free
  registration); returned WMM-2025 declination +1.516°, annual +0.126°/yr.
- Puertos del Estado (Portus): no documented REST API (404/405) → excluded.

Weak point: the API is only loosely tied to the *exam* task (exams give dm in the text);
it serves the passage-plan part of the agent.

## 4. Compute tool and action tool

- **Compute — `nav_calc`**: Ct/Rv/Ra conversions, declination update, ETA, plane-sailing
  dead reckoning; optional `chart_solver` over a gazetteer of ≈40 Strait-of-Gibraltar
  landmarks (the exam chart) to make the 3/4 Carta questions that need coordinates solvable
  (ASSUMPTION: gazetteer untested).
- **Action — `write_passage_plan`** (`requires_confirmation=True`): writes a GPX route +
  Markdown/PDF plan (waypoints, Rv/Ra per leg, ETA, forecast snapshot) to
  `data/plans/<id>/`. Grader checks the GPX parses, leg courses equal `nav_calc`, ETA matches.
  Sandboxed: files only.

## 5. Corpus

~30 documents: RD 875/2014 consolidated (116 pp, clean; two-column syllabus tables
interleave), RIPA/COLREG in Spanish (BOE, 28 pp, very clean) + 3 amendments, IALA R1001
Spanish draft (34 pp; 66 images lost, tables legible with `-layout`; final Ed. 2.0 URL 404),
AEMET maritime meteorology guides (not yet downloaded), DGMM papers (evaluation set, not
corpus). Licence: BOE/ministry reuse (Ley 37/2007, ASSUMPTION verified only for BOE);
**IALA material copyrighted (ASSUMPTION)**. **Buoyage and lights are drawings** — the
most-asked topic (Balizamiento, 5 questions, ≤2 errors allowed) loses its figures.

**Five gold questions:** masthead light range <12 m → 2 millas (RIPA Regla 22 c));
overtaking angle → más de 22,5° a popa del través (RIPA Regla 13); PER limits → 15 m,
12 millas, interinsular Baleares/Canarias (RD 875 art. 8 c) p. 9); Carta errors allowed →
2, pass 32/45 (RD 875 Anexo II p. 43); South cardinal light → CtRp(6)+DL 10 s or Rp(6)+DL
15 s (IALA R1001 ES, Cuadro 6 p. 14).

## 6. Agent — 5 tasks with automatic checks

| # | Task | Tools | Check |
|---|---|---|---|
| 1 | "Pregunta 42 del examen de abril: ¿cuál es la respuesta y por qué?" | `exam_lookup` → `nav_calc` | letter == key; Ct computed == reference |
| 2 | "Salgo de Valencia a las 09:30 a 6 nudos hacia un punto a 14 millas: ¿llego antes del viento de la tarde?" | `nav_calc` (ETA) → `marine_forecast` (API) | ETA == reference; quotes forecast wind at ETA hour from fixture |
| 3 | "¿Qué luces debo llevar con 11 m de eslora de noche?" | `search_knowledge_base` → (none) | cites RIPA Regla 22/23 chunk; range values correct |
| 4 | "Hazme el plan de travesía Tarifa → Ceuta con dm actualizada." | `noaa_declination` → `nav_calc` → `write_passage_plan` | GPX legs Rv/Ra == reference |
| 5 | "Corrige mi examen: estas son mis 45 respuestas." | `exam_lookup` → count by unit | pass/fail computed with per-unit error limits == reference |

**Impossible task:** "Dibújame la derrota sobre la carta del Estrecho y dime la sonda en
ese punto" → needs the chart image and the Anuario de mareas; the agent must say it cannot
see the chart and not invent a depth.

## 7. Domain reward

**Convention correctness**: reward when the `<think>` block states Ct with the sign
convention (E +, W −) and the intermediate Ct equals dm + Δ. User value: the exam penalises
exactly the sign error. Hack: always write "Ct = dm + Δ" boilerplate. Mitigation: check the
*numeric* Ct against the reference, not the words.

## 8. Risks

| Risk | L | I | Mitigation |
|---|---|---|---|
| **Task too easy**: T1/T2 are one addition + mod 360 → base may already solve it | H | H | Measured in §2; hardness has to come from chaining and word problems |
| Most exam content is MCQ recall (RIPA, buoyage), not verifiable reasoning | H | M | Mined MCQ as eval, generator for RL |
| Buoyage/lights are images; chart questions need coordinates | H | M | Gazetteer + hand-written chunks; declare scope |
| API loosely tied to the task; Open-Meteo overloaded once | M | M | Fixtures; NOAA key via env |
| IALA copyright; older DGMM PDFs scanned | M | L | Link, don't redistribute; OCR only what's needed |
| Nobody in the team sails (ASSUMPTION) | M | M | Motivation risk in the defence ("¿por qué este tema?") |

## 9. Closest professor example

**"Tutor de química"** (education, generator by families, "SFT memoriza, RL generaliza").
Quote:

> "Aquí es donde más sentido tiene el reto de 'SFT memoriza, RL generaliza': entrenad con
> unas familias de reacciones y evaluad con otras. En la fase 4 valoraría un agente que da
> pistas antes que la solución […]"

Difference: a real official exam with ~4,000 published answer-keyed questions (a mining
source the chemistry example lacks); OOD is a chained family.

## 10. Scorecard

<!-- scorecard -->
