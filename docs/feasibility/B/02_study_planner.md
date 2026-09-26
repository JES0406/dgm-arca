# 02 — Study planner over MIA course material (candidate given by the human)

**One sentence (proposal format).** Un agente que planifica y replanifica las sesiones de
estudio de un alumno del Máster en IA a partir del material real de cada asignatura
(diapositivas, exámenes, prácticas y guías docentes), y que sabe responder con cuentas
verificables si todavía llega al examen.

Design decisions carried over from the human conversation earlier today (2026-09-26):
phase-1 task = *capacity arithmetic* (approach 1: the model counts, a solver tool packs);
calendar = `.ics` as source of truth + optional Google Calendar sync behind a flag; corpus =
slides, assignments, exams (+ guías docentes), **no books** in the ARCA version; dynamic
replanning when the student deviates from the plan.

---

## 1. Verifiable task (phase 1)

Prototype: [`planner/generator.py`](planner/generator.py) — `PlannerGenerator` subclasses
`rlm.generate_problems.ProblemGenerator` (`sample_params` / `solve` / `render`); `solve` is
the verifier. Four types, round-robin so each set is balanced:

| Type | Question (Spanish statement) | Answer | Branches tracked |
|---|---|---|---|
| T1 `log_update` | hours left on a topic after 1–3 logged sessions given as clock times, relative days ("ayer", "anteayer", dated), and deviations ("tocaba X pero estudié Y") | hours, e.g. `4.25` | asked topic studied?, trap *planned-but-not-studied*, clamp at 0, n sessions |
| T2 `margin` | available hours from today (incl.) to the day before the exam minus required hours, holidays are rest days | signed hours, e.g. `-6.5` | feasible?, holidays in window (0/1/2+), horizon weeks |
| T3 `rate` | minimum equal hours per study day, ceil to 0.25 | `2.25` | rounded up?, holidays, horizon |
| T4 `finish_date` | date topic k is finished under a fixed order, weekly availability, holidays; hours carry over between topics within a day | `2026-12-03` | holiday skipped?, target is last?, span weeks |

Holidays are **real**: a snapshot of Nager.Date (`planner/nager_ES_2026.json`,
`nager_ES_2027.json`) filtered by region, written into the statement, so training needs no
network and the answer is deterministic.

Commands run and real output (abridged; full JSON printed by the script):

```
$ uv run python docs/feasibility/B/planner/generator.py --n 20 --split test
 "n_problems": 20, "n_templates_used": 14, "unique_param_hashes": 20,
 "answer_leaked_in_statement": 4,
 "type": {"log_update": 5, "margin": 5, "rate": 5, "finish_date": 5}

$ uv run python .../generator.py --n 2000 --split train --out $TMP/planner_train.jsonl
 n_problems 2000, n_templates_used 16, unique_param_hashes 2000, answer_leaked 209
 feasible        {False: 206, True: 294}
 clamped_at_zero {False: 419, True: 81}
 trap_planned_not_studied {False: 368, True: 132}
 rounded_up      {True: 440, False: 60}
 holiday_skipped {False: 308, True: 192}
 holidays_in_window {0: 469, 1: 165, 2+: 366}   horizon_weeks 0..5 all populated

$ uv run python .../generator.py --n 100 --split ood
 region {ES-CT: 40, ES-GA: 31, ES-AN: 29}, n_topics {5: 47, 6: 53}, horizon_weeks {6: 50}
 feasible {False: 19, True: 6}

$ uv run python docs/feasibility/B/common/overlap.py planner_train.jsonl problems_test.jsonl problems_ood.jsonl
planner_train.jsonl (2000) ∩ problems_test.jsonl (20) = 0
planner_train.jsonl (2000) ∩ problems_ood.jsonl (100) = 0
problems_test.jsonl (20) ∩ problems_ood.jsonl (100) = 0
```

**Two distribution bugs the branch table caught (and were fixed before the numbers above):**
the first OOD run had `feasible: True` in 24/25 margin problems (horizons 2–3× longer but the
same hours → easy branch), and T1 clamped at zero in only 5/500. Fix: OOD hours scale ×2.5
with the horizon; 25 % of T1 problems sample small remaining hours. This is exactly the
"todo el peso en la rama fácil" error of `docs/datasets.md`.

**Answer leakage.** A plain substring check flagged "8" inside "2026-10-08"; the harness
now matches whole number tokens in dot and comma spelling (`common/harness.py::leaks`).
With it, 209/2000 leak: **105 are by design** (T1 asks about a topic that was *not* studied,
so the answer equals the hours in the statement — that trap is the point) and **104 are
coincidental** (≈5 %: the margin or rate happens to equal another number in the text);
T4 has 0. Fix for the real set: reject coincidental leaks at sampling time, cap the
by-design trap at ~5 % and report it separately in `EXPERIMENTS.md`.

**OOD split.** Regions never in train (Cataluña, Andalucía, Galicia: different regional
holidays), horizons 45–90 days (train 5–40), 5–6 topics (train 2–4). Supports the
"SFT memoriza, RL generaliza" experiment along three independent axes.

**Verifier edge cases** (`EDGE_CASES` in the generator, asserted on every run; they become
`tests/test_verifier.py`): `4,25` = `4.25` (Spanish decimal comma — note the repo's
`normalize_number` strips commas and would read `4,25` as `425`), `4,25 h`, `**2.5**`,
Unicode minus `−6,5`, sign matters (`6.5` ≠ `-6.5`), `-0` = `0`, multi-answer `3 o 4`
rejected, ISO date and `dd/mm/yyyy` accepted, `mm/dd/yyyy` rejected, impossible date
`2026-02-30` rejected, weekday prose `martes 3 de noviembre` rejected (no year).

**Dataset strategy (datasets.md).** Strategy 1 (generator) for 100 %: SFT 500 problems,
GRPO 1500, test 200 (50 hand-audited), OOD 100. Optional 30 % GSM8K control group.

## 2. Difficulty

See §2 results table below (filled from real runs).

<!-- difficulty -->

## 3. External API

**Nager.Date** — <https://date.nager.at/Api> (public holidays by country, with regional
`counties` codes).

```
$ curl -s -D - https://date.nager.at/api/v3/PublicHolidays/2026/ES
HTTP/2 200
content-type: application/json; charset=utf-8
cache-control: public,max-age=604800
cf-cache-status: HIT
→ 32 holidays for 2026; 12 apply to ES-MD:
  2026-01-01 01-06 04-02 04-03 05-01 05-02 08-15 10-12 11-01 12-06 12-08 12-25
```

No key, no rate-limit headers, served through Cloudflare with a 7-day cache: stable
enough for a grader. **Gotcha:** municipal holidays (Madrid city: San Isidro 15 May,
Almudena 9 Nov) are *not* in Nager.Date; they must come from config or the corpus — a nice
"the API is incomplete, the agent must say so" case. Also missing: the university's own
non-teaching days (they are in the academic calendar, a candidate corpus document).

Optional second action target: Google Calendar API v3 (OAuth, test calendar only, behind a
flag; token never in the repo). ASSUMPTION: the grader will not be given calendar access,
so the `.ics` is what gets graded.

## 4. Compute tool and action tool

- **Compute — `plan(state)`**: packs remaining hours into free slots respecting weekly
  availability, holidays, exam dates and prerequisite order (greedy earliest-deadline-first,
  or OR-Tools CP-SAT if ties matter). Why not in the model's head: it is a bin-packing /
  scheduling problem over dozens of slots; the 0.6B model cannot do search reliably in
  384 tokens. Plus `estimate_hours(topic)`: deterministic formula over corpus metadata
  (slide pages, exam presence) and the guía's *estudio personal* hours (e.g. GI: 25 h
  of personal study out of 135 h, `master_kb/courses/GI/guide.md` l.159–160).
- **Action — `write_calendar(student_id, plan)`** (`requires_confirmation=True`): writes
  `data/students/<id>.ics` + `<id>.json` and exposes them at `GET /calendar/<id>.ics`.
  The grader observes the effect by downloading the file (or its SHA-256 before/after) and
  parsing the VEVENTs; sandboxed because it only writes under `data/students/` for
  synthetic student ids. Google sync is an optional second sink, off by default.

## 5. Corpus

Source: the team's private knowledge base `master_kb` (built by the iMAT-RAG project), the
lecture material of the nine first-year MIA courses. Counted from
`master_kb/intake.json` (219 files):

| Kind | Files | Pages | Notes |
|---|---|---|---|
| slides | 144 | 5,386 | 16 IAG decks are **scanned** (OCR'd by the existing pipeline) |
| exams (quizzes, past papers, solutions) | 21 | 162 | MGP T2–T4 quizzes, GI problem sheets + solutions |
| assignments | 18 | 139 | IM labs dominate (15) |
| notes | 10 | 128 | 7 are *student-written* → need the authors' OK |
| guías docentes | 9 | ~9×6 | ECTS hours per activity, evaluation weights, exam rules |
| (books) | — | — | **excluded** from ARCA by the human's decision; kept for the personal version |

Format: PDF (already extracted to Markdown by the iMAT-RAG pipeline: mineru + OCR).

**Licence: the weakest point of this topic.** Slides, exams and assignments are © the
teaching staff / Universidad Pontificia Comillas, distributed to enrolled students; there
is no open licence. `rag/README.md` allows a non-redistributable corpus ("dejad el script
que lo descarga y decid de dónde sale y con qué licencia"), but the professor will call
`/rag` through a public ngrok URL, which serves passages to whoever has the URL. Needed:
written permission from the professors (at minimum the MGP team, who are the graders), the
corpus kept out of git, and a download script that needs the team's HF token. Guías
docentes are published on comillas.edu (ASSUMPTION: public web pages; verify URL).

**Secret found in the corpus (verified):** the IM assignment "Práctica Kubernetes 1"
(pp. 5–8) contains a screenshot/text dump of a GCP service-account JSON including a
`private_key` field. Serving it through `/rag` would republish a credential. Mitigation:
secret-scan the extracted Markdown (e.g. `detect-secrets` / regex for `BEGIN PRIVATE KEY`)
and redact before indexing; add a test.

**Five gold questions only answerable from the corpus** (sources verified via the imat-rag
MCP or by reading the file):

1. "En el DDPM de clase, ¿qué λ usa la pérdida híbrida?" → λ = 0,001. *MGP · T2 Parte 1
   DDPM slides, pp. 23–28* (chunk `5fda83680b84e969`).
2. "¿Cuántos pasos requiere el muestreo ancestral de DDPM según las transparencias?" → del
   orden de T = 1000. *Same deck, pp. 23–28.*
3. "En la práctica 1 de Kubernetes de IM, ¿con cuántos nodos y en qué zona se crea el
   clúster?" → 2 nodos, `us-central1-a`, nombre `mlops-gke-cluster`. *IM · Tema 4 · 15
   Unit 4 Práctica Kubernetes 1, pp. 5–8* (chunk `4eca800a3864c283`).
4. "¿Cuánto pesa la intercuatrimestral en Geometría de la Información y libera materia?" →
   30 %; no libera materia. *Guía docente GI, `master_kb/courses/GI/guide.md` l.168–212.*
5. "¿Puedo llevar algo al examen final de GI?" → una hoja resumen A4 por ambas caras, de
   color no blanco, sin problemas resueltos. *Guía docente GI, l.212.*

A generic model cannot know any of these: they are course-specific numbers and rules.

## 6. Agent (phase 4) — 5 tasks chaining ≥2 tools, with automatic checks

State is a synthetic student JSON; each check reads files the tools wrote.

| # | User message | Tools | Automatic success check |
|---|---|---|---|
| 1 | "Ayer estudié topología de 16:00 a 18:30 en vez de probabilidad. Actualiza mi calendario." | `log_session` → `plan` → `write_calendar` | state hours: topología −2.5; new `.ics` has no event before *now*; `plan` output == reference solver on the new state |
| 2 | "¿Me da tiempo a preparar GI antes del examen si el 12 de octubre no estudio?" | `get_holidays` (API) → `estimate_hours` (KB) → `plan` | final answer contains the signed margin equal to `solve()` ± 0 |
| 3 | "¿Qué entra en la intercuatrimestral de GI y cuántas horas le debo dedicar?" | `search_knowledge_base` → `estimate_hours` | cites the guía chunk id; hours == formula output |
| 4 | "Mueve todo lo de MGP T3 a después de T2 y dime cuándo acabo." | `plan` (with prereq constraint) → `write_calendar` | T3 events all after last T2 event in the `.ics`; stated date == T4 `solve()` |
| 5 | "Hazme un plan de repaso con los quizzes de MGP T2–T4 la semana antes del examen." | `search_knowledge_base` (exams) → `plan` → `write_calendar` | ≥3 VEVENTs whose DESCRIPTION cites quiz chunk ids that exist |

**Impossible task:** "Planifícame el examen de Visión por Computador del segundo curso." →
`coverage`-style tool shows no such course in the corpus; the agent must say it has no
material for it and **not** write any calendar event (check: `.ics` unchanged, SHA-256
equal).

## 7. Domain reward (3rd GRPO reward)

**Asymmetric safety.** Accuracy is binary; the domain reward grades *wrong* answers by the
direction of the error: an optimistic error (margin too high, rate too low, finish date too
early, hours left too low) scores −1, a pessimistic one −0.5, correct +1. Why the user
cares: a student told "you'll make it" when they won't is hurt more than one told to study
15 min more.

Reward hack: the model learns to always err pessimistic (e.g. subtract a safety constant),
collecting −0.5 instead of −1 when unsure. Mitigation: the accuracy reward dominates (weight
1.0 vs 0.3); monitor the signed-error histogram per step; the verifier stays exact.

## 8. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Corpus licence refused (slides/exams © professors, served via public ngrok) | M | **H** | Ask in the proposal; fallback corpus = guías docentes (public) + openly licensed books (Sutton & Barto, Prince UDL, Murphy PML — verify licences) + own notes with authors' consent |
| Phase-1 task judged "too easy / toy arithmetic" | M | H | Show base pass@1 (§2); hard branches (holidays, clamp, deviation traps, ceil rounding); OOD regions/horizons |
| Secrets / personal data in corpus (verified: GCP private key in an IM lab) | H | M | Secret scan + redaction before indexing; test; student names in notes → strip |
| 16 GB, 24 h sessions, ~384-token completions | M | M | T4 on long horizons needs day-by-day summation → long traces; cap horizon in train, keep long ones for OOD; measure truncation rate |
| Nager.Date lacks municipal/university holidays | H | L | Config file per city + academic calendar in corpus; agent states the limitation |
| Team members study different courses; demo relies on real material | L | M | Synthetic students; demo with MGP (the grader's own course: strongest demo) |
| Safety/disclaimer overhead | L | L | Education: no mandatory disclaimer category |

## 9. Closest professor example

Closest: **"Tutor de química"** (education + generator) and, for the date arithmetic,
**"Asistente de plazos y recursos administrativos"**. Quote (docs/temas_ejemplo.md):

> "En la fase 1 el interés está en los casos difíciles del calendario: notificación en
> viernes por la tarde, festivo local, agosto, notificación electrónica no abierta. El
> conjunto de test los tiene que tener. […] Las fechas se calculan con la herramienta, nunca
> de cabeza: la tercera recompensa de GRPO puede premiar precisamente que el razonamiento
> use el calendario correcto."

How it differs: the date arithmetic is on *study capacity*, not legal deadlines; the corpus
is course material (not law), and the action is a living calendar that is rewritten when
the student deviates. The festivo-local trap is exactly our Nager.Date gap.

## 10. Scorecard

<!-- scorecard -->
