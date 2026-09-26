# 03a — Red team: the 10 hardest professor questions for the top 3

Protocol: professor's objection → best rebuttal backed by evidence in this folder → verdict
(**holds** / **dented** / **breaks**). Course theory is cited from the MGP slides via the
imat-rag index, as the user's rules require.

---

## Study planner over MIA course material

1. **"Esto es aritmética de calendario. ¿Qué aprende el modelo que no haga un script?"**
   Rebuttal: the script *is* the tool (`plan`); the model learns to *audit* capacity in
   natural language — the log with clock times, deviations ("tocaba X pero estudié Y"),
   relative days and holiday lists. Qwen3-0.6B gets 1/20 (strict and lenient), so there is
   something to learn; the question is whether it transfers (OOD regions/horizons).
   Verdict: **dented** — defensible, but it is the first thing he will ask.
2. **"¿Con qué licencia servís por ngrok las diapositivas de mis compañeros?"**
   Rebuttal: none yet; slides/exams are © staff. Ask permission in the proposal; fallback
   corpus = guías docentes (public) + openly licensed books. Verdict: **breaks without
   written permission** (GO-IF-FIXED).
3. **"En vuestro corpus hay una clave privada de GCP. ¿Qué más hay?"** Rebuttal: verified
   in IM Práctica Kubernetes 1 pp. 5–8; secret scan + redaction before indexing, with a test.
   Verdict: **holds if done**; showing it proactively is a plus.
4. **"¿La API externa es solo una lista de festivos? Eso no es una herramienta."**
   Rebuttal: Nager.Date is real and needed (regional holidays change capacity), but thin.
   Stronger: add the university's published academic calendar and exam timetable as a
   scraped source, or Google Calendar read for busy slots. Verdict: **dented**.
5. **"¿Cuál es vuestro 30 % de control general?"** GSM8K, as in the smoke test. **holds**.
6. **"Si todas las respuestas de un grupo aciertan o todas fallan, GRPO no aprende. ¿Pasa
   aquí?"** Theory: A_i = r_i − mean(r) (÷ std) — MGP *Reasoning language models* handout
   pp. 62–72 — so identical rewards give zero advantage. At 1/20 base, most groups of 8 are
   all-zero → SFT warm-up first (the R1 recipe: "a few thousand" cold-start examples, same
   handout pp. 107–120) and a curriculum starting at T1/T3. Verdict: **holds** with SFT.
7. **"¿Cómo evaluáis el agente sin datos reales de alumnos?"** Synthetic student states
   with a reference solver; checks read the `.ics`. **holds**.
8. **"¿Por qué no dejar que el modelo haga el plan entero?"** Plans are hundreds of tokens
   and bin-packing; a 0.6B model at 1/20 on single counts cannot. Tool = right design.
   **holds**.
9. **"¿Qué pasa cuando el alumno dice 'mañana no puedo'?"** Agent task 1 pattern:
   `log/availability` update → `plan` → `write_calendar`; memory keeps the state. **holds**.
10. **"Demo de 3 minutos."** Log a deviation live, watch the calendar re-flow and the
    margin change, ask a cited question about MGP T2. Strong: the grader's own course.
    **holds**.

Survives: yes, **conditional on corpus permission** (Q2).

## PVPC electricity bill & load shifting

1. **"¿Por qué el modelo tiene que saber que Viernes Santo no es valle?"** Because the
   Circular excludes non-fixed-date holidays (art. 7.3); it is the classic trap and the kind
   of "festivo local" case he asked for in the legal example. **holds**.
2. **"Las reglas cambian cada enero y en 2026 el IVA cambió dos veces. ¿Vuestro
   verificador está congelado?"** Date-indexed constants; rule sheet in the statement; gold
   questions pinned to dates; the change is itself a RAG test. **holds**.
3. **"¿El 1 €/MWh del impuesto no lo usáis?"** Shown to be unreachable for households
   (needs < 0.0196 €/kWh); removed from the generator, kept as a gold question. **holds** —
   evidence of looking at the branch table.
4. **"El argmin de 10 precios lo hace cualquiera."** Measured baseline decides; if base
   > 50 % on T4 it moves to OOD/longer lists. **pending numbers** (see 02_pvpc §2).
5. **"¿Qué API?"** REData (no key) + ESIOS archive (tokenless) with real hourly prices
   since 2021. **holds** — strongest API of the five.
6. **"¿Cómo sé que vuestra factura coincide con una real?"** Peajes+cargos reproduce the
   TEU that ESIOS publishes exactly (97.55/29.27/3.29 €/MWh on 2026-09-25); hand-computed
   example within 1 cent (rounding convention documented). **holds**.
7. **"¿Qué hace la acción?"** `.ics` of appliance windows; grader checks DTSTART equals
   `cheapest_window` on that day's real prices. **holds**.
8. **"¿Tercera recompensa?"** Line-by-line breakdown, the professor's own suggestion for
   finance, with numeric check per line to avoid keyword hacking. **holds**.
9. **"¿Interesa a alguien?"** Every household on PVPC; the team pays bills. Motivation is
   real but not personal. **dented** (row N).
10. **"Demo."** "¿Cuándo pongo la lavadora mañana?" with real prices, then the bill check
    with the March–May 2026 tax cut. **holds**.

Survives: **yes**.

## Nutri-Score 2023

1. **"El modelo lee la tabla de umbrales del enunciado y cuenta. ¿Dónde está el
   razonamiento?"** Category logic (N ≥ 11 protein rule, red-meat cap, beverage tables) is
   where it fails; OOD category (fats) tests transfer. **dented** until measured.
2. **"¿Letras A–E y puntuación de −15 a 55: no adivina el 20 % con la letra?"** Yes for
   letters — report score and letter separately; RL on scores only. **holds**.
3. **"Open Food Facts se cae."** Seen twice in research; frozen snapshots are the graded
   path. **holds**.
4. **"¿Quién es el usuario?"** Small producers after the 1 Jan 2026 switch to the new
   algorithm (AESAN). Plausible but the team has no food-industry contact (ASSUMPTION).
   **dented**.
5. **"¿Por qué no usar la calculadora oficial de SPF?"** It *is* our oracle; the agent adds
   OFF comparison, what-if recipe changes and cited regulation. **holds**.
6. **"¿Licencia de los documentos de SPF?"** Unverified; EUR-Lex is explicitly reusable.
   **dented**.
7. **"¿Reward hacking?"** Component-consistency reward parses per-component values; one
   value per component. **holds**.
8. **"¿Tablas en imagen?"** Letter table and diagrams: hand-written chunk. **holds**.
9. **"¿Categoría ambigua en la fase 4?"** Agent asks; gold questions on pp. 16–19. **holds**.
10. **"Demo."** Photo-free: paste a label, get letter + what to change to reach C. **holds**.

Survives: **yes**, weaker on user and licence.
