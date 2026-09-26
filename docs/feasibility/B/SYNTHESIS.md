# SYNTHESIS — ARCA topic feasibility study, Agent B (for agents and the team)

> **Read this first.** Self-contained summary of feasibility study B (2026-09-26) for the
> ARCA practice (MGP, MIA ICAI 2026-27). Goal of the reader: help the team decide **which
> topic to present to colleagues / propose to the professor**. Everything below is backed by
> files in this folder; paths are relative to `docs/feasibility/B/`. Claims marked
> ASSUMPTION or ESTIMATE are unverified. Work was **stopped on request** before the model
> baselines finished: see §2.

---

## 1. The assignment in five lines

Teams of 3 build one agent on a free topic, in 4 graded phases, each a FastAPI endpoint the
professor calls: (1) `/reasoning` small model Qwen3-0.6B/1.7B trained with SFT + GRPO on a
**verifiable task** (≥3 rewards, one domain-specific); (2) `/tools` three real tools
(external HTTP API, compute, observable sandboxed action); (3) `/rag` real licensed corpus,
3 retrievers, 50-question gold set; (4) `/agent` hand-written ReAct loop, 20 chained tasks.
Phase 0 = one-page proposal (`docs/00_propuesta.md`), must be approved first. Professor's
filter: *"que la tarea verificable exista y el corpus sea accesible"*. Full constraints:
`docs/topic_debate_brief.md` (branch `worktree-topic-debate-brief`).

## 2. Status: what is done, what is not

| Item | State |
|---|---|
| Longlist (14 candidates, 9 domains, A–D desk scores) | done — `01_longlist.md` |
| Research per shortlisted topic (rules, live API calls, corpus + licence, gold Qs) | done — `<topic>/research.md` |
| Working generator per topic (`sample_params`/`solve`/`render`, verifier + edge cases, branch table, OOD split, hash dedup) | done — `<topic>/generator.py` |
| Per-topic report (tools, corpus, 5 agent tasks, domain reward, risks, closest example) | done — `02_<topic>.md` |
| Red team (10 questions) for PVPC, planner, Nutri-Score | done — `03_redteam.md` |
| Spanish proposal draft (for PVPC) | done — `propuesta_pvpc_borrador.md` |
| **Model baselines (scorecard row C: difficulty)** | **only 1 of 10 runs finished**: planner, Qwen3-0.6B. Teacher (Qwen3-4B) runs were killed. `<!-- difficulty -->` and `<!-- scorecard -->` markers in `02_*.md` are unfilled. |
| `03_decision.md` | **not written** — this synthesis replaces it for now |
| `uv run pytest` | 39 passed, 6 xfailed (template placeholders) — nothing broken |

Hardware used: laptop RTX 3050 4 GB (thermal throttling at 86–87 °C; one PC crash). Qwen3-4B
only fits as NF4 4-bit; ~40 min per 20 problems. The DGX (16 GB) is the place to finish.

## 3. The five shortlisted topics at a glance

| | **PVPC electricity bill** | **Study planner (MIA)** | **Nutri-Score 2023** | **FAO-56 irrigation** | **PER boating exam** |
|---|---|---|---|---|---|
| One line | Explain/check the regulated electricity bill (2.0TD), cost per appliance, schedule appliances in cheap hours | Plan and re-plan study sessions from real course material; verifiable capacity arithmetic | Compute updated Nutri-Score from a nutrition table; labelling-law Q&A; label report | Weekly irrigation depth/drip minutes from real ETo; guides Q&A; irrigation calendar | Tutor for the PER exam: course conversions, declination, ETA; RIPA Q&A; passage plan |
| Phase-1 task (answer) | period label; € to the cent; cheapest-window hour | hours left after log; signed margin; h/day (ceil 0.25); finish date | score (int) or letter | Kc; mm; minutes; RAW mm | course 000–359; dm (0.5°); HH:MM |
| Dataset | generator + **real ESIOS prices since 2021** | generator (real holidays snapshot) | generator + OFF mining | generator | generator + **≈3,500–4,000 official past MCQ with keys** (ESTIMATE) |
| External API (verified live) | REData, no key; ESIOS archive tokenless | Nager.Date holidays, no key (thin) | Open Food Facts, no key, **flaky search** | Open-Meteo ETo, no key (non-commercial) | Open-Meteo marine (overloaded once); NOAA needs key |
| Action | `.ics` + CSV appliance schedule | `.ics` calendar (+ optional Google sync) | HTML/PDF label report | `.ics` + CSV irrigation schedule | GPX + passage plan |
| Corpus & licence | BOE/CNMC/IDAE, 25–40 docs; **reusable (BOE licence, art. 13 LPI)** | 144 slide decks (5,386 pp) + 21 exams + 18 labs + 9 guías; **© staff, needs permission**; **a GCP private key found in an IM lab PDF** | SPF (licence unverified) + EUR-Lex (reusable) + AESAN | **FAO-56 "All rights reserved"**, noisy Spanish PDFs (OCR, image tables) | BOE (reusable); IALA copyrighted; buoyage = images |
| Measured difficulty | not measured | **Qwen3-0.6B: 1/20 strict and lenient**, 0 % valid format, 55 % truncated at 1024 tok | not measured | not measured | not measured (ESTIMATE: too easy — one addition) |
| Closest professor example | Tax copilot (finance) | Admin deadlines (dates) / chemistry tutor | Product-sheet writer | Chemistry tutor | Chemistry tutor |
| Biggest risk | rules change every January (and twice in 2026) | **corpus permission** + "toy arithmetic" objection | category ambiguity; weak user/team fit | licence; conventions disagree | task too easy; API loosely tied |

## 4. Provisional scorecard (rows of the brief §6, 0–3)

**Row C (difficulty) is unmeasured except planner base = 1/20; totals exclude C.** Row N
(team fit) is an ASSUMPTION: the planner is the human's own idea; team domain knowledge
for the others is unknown.

| Row | PVPC | Planner | Nutri-Score | Irrigation | PER |
|---|---|---|---|---|---|
| A verifiable task | 3 | 3 | 3 | 3 | 3 |
| B dataset w/o hand labels | 3 | 3 | 3 | 3 | 3 |
| C difficulty | ? | ? (base 5 %, teacher unknown) | ? | ? | ? (likely too easy) |
| D real free API | 3 | 2 | 2 | 3 | 1 |
| E compute tool | 3 | 3 | 3 | 3 | 2 |
| F action tool | 3 | 3 | 2 | 3 | 2 |
| G corpus available/licensed | 3 | **1** | 2 | **1** | 2 |
| H gold set meaningful | 3 | 3 | 3 | 2 | 3 |
| I agent tasks checkable | 3 | 3 | 2 | 3 | 2 |
| J domain reward natural | 3 | 2 | 2 | 2 | 2 |
| K interpretation material | 3 | 3 | 3 | 2 | 2 |
| L real user / portfolio | 3 | 3 | 2 | 2 | 2 |
| M risk/safety overhead | 3 | 2 | 2 | 3 | 3 |
| N team fit (ASSUMPTION) | 2 | 3 | 1 | 1 | 1 |
| O differentiation | 3 | 3 | 3 | 3 | 2 |
| **Total (excl. C)** | **41** | **37** | **33** | **34** | **30** |

## 5. Provisional decision and what would flip it

- **Winner (provisional): PVPC** — no kill risk on any row: strongest API, reusable corpus,
  real data that reproduces the published peajes+cargos to the cent, genuine traps (Good
  Friday is *not* valle; 2026 VAT/tax toggles; DST days), professor's own suggested third
  reward (bill breakdown). Verdict **GO**, pending the difficulty measurement.
- **Fallback / co-favourite: Study planner** — highest motivation (the human's idea, the
  grader's own course for the demo) but **GO-IF-FIXED**: needs (1) written permission to
  serve slides/exams through the API, (2) secret-scan + redaction of the corpus, (3) a
  thicker external API (academic calendar / exam timetable). Measured base 1/20 shows there
  is something to learn; teacher rate unknown.
- **Deciding criterion:** the professor's filter "corpus accesible" (row G) and API depth
  (row D).
- **Flips to the planner if:** the professors give written permission to use the course
  material **and** Qwen3-4B solves ≥50 % of planner problems (distillation viable).
- **Flips away from PVPC if:** Qwen3-0.6B base already solves >50 % (GRPO would see
  zero-advantage groups — MGP *Reasoning language models* handout pp. 62–72:
  A_i = r_i − mean(r), identical rewards ⇒ zero advantage), or the team has no motivation
  for energy.
- Nutri-Score is a solid third; irrigation is blocked by licence; PER is likely too easy
  and its API is weak.

## 6. Design already agreed with the human for the study planner

(From the brainstorming conversation before the autonomous study.)
- Phase-1 task = *capacity arithmetic* (model counts, solver packs): the optimisation is a
  **tool** (`plan`), not the model's job.
- Calendar: `.ics` as source of truth + optional Google Calendar sync behind a flag.
- Corpus: slides, assignments, exams (+ guías docentes); books excluded (kept for a personal
  version).
- Dynamic replanning: when the student deviates (studies topology instead of probability),
  the agent updates state → re-plans → rewrites calendar and dashboard.
- Proposed third reward: asymmetric safety (optimistic errors penalised 2×).

## 7. Cross-cutting findings worth presenting (useful whatever topic wins)

1. **Branch tables catch real bugs.** Nutri-Score: 57 % E / 0.6 % A before stratifying;
   planner OOD 24/25 "feasible"; PER wrap-around and midnight at 1 %; PVPC tax-floor branch
   unreachable. All fixed or declared.
2. **Leakage happens with small parameter spaces.** Irrigation had train∩test = 8/20; fix =
   hash-partitioned splits (`sha1(params) % 10 == 0` ⇒ test). Recommend for any generator.
3. **The repo's `normalize_number` strips commas**: Spanish `4,25` becomes `425`. Every
   Spanish-domain verifier must handle decimal commas (edge cases written in each generator).
4. **Substring leak check is noisy** (flags "8" inside "2026-10-08"); `common/harness.py`
   uses whole-number-token matching; for label/choice answers leakage is structural, report
   per type.
5. **Qwen3-0.6B with the R1-Zero prompt produced 0 % valid `<answer>` format** on the
   planner: the format reward and SFT warm-up matter from day one.
6. **Laptop GPUs are not enough** for teacher runs; plan baselines on the DGX.

## 8. Open questions for the team (not asked yet)

1. Who is on the team, and which domain does each member care about or know?
2. Do we ask the MGP professors for permission to use course slides/exams (planner)? Who asks?
3. Is anyone motivated by energy (PVPC) — would we show it in an interview?
4. Should the chosen topic keep the human's dynamic-calendar idea (it transfers to PVPC as
   dynamic appliance scheduling)?
5. Finish the baselines on the DGX before submitting the proposal? (Recommended: 1 session.)

## 9. How to continue (commands)

```bash
# generators (CPU, seconds)
uv run python docs/feasibility/B/<topic>/generator.py --n 20 --split test
uv run python docs/feasibility/B/<topic>/generator.py --n 2000 --split train --out /tmp/train.jsonl
uv run python docs/feasibility/B/common/overlap.py /tmp/train.jsonl docs/feasibility/B/<topic>/problems_test.jsonl
# baselines (GPU; on the DGX drop --four-bit)
uv run python docs/feasibility/B/common/harness.py --problems docs/feasibility/B/<topic>/problems_test.jsonl \
  --verifier docs/feasibility/B/<topic>/generator.py --model Qwen/Qwen3-0.6B --max-new-tokens 1024 \
  --out docs/feasibility/B/<topic>/baseline_qwen3-0.6b.json
bash docs/feasibility/B/common/run_all_baselines.sh   # queue for all topics
uv run python docs/feasibility/B/common/lenient.py <baseline.json> <generator.py>
```
Topics: `planner`, `pvpc`, `nutriscore`, `riego`, `per`.

## 10. File map

```
docs/feasibility/B/
  SYNTHESIS.md               ← this file
  01_longlist.md             14 candidates, A–D scores, shortlist rationale
  02_study_planner.md        02_pvpc.md  02_nutriscore.md  02_riego.md  02_per.md
  03_redteam.md              10 hard questions × top 3, with verdicts
  propuesta_pvpc_borrador.md Spanish proposal draft following docs/00_propuesta.md
  common/                    harness.py (report + baseline runner), overlap.py, summarize.py,
                             lenient.py, run_all_baselines.sh
  <topic>/generator.py       prototype generator + verifier + EDGE_CASES
  <topic>/research.md        sources, API calls, corpus/licence, gold questions
  <topic>/problems_*.jsonl   20 test + 100 OOD sample problems
  planner/baseline_qwen3-0.6b.json   the only finished model run
  planner/nager_ES_2026.json, nager_ES_2027.json   holiday snapshots (API evidence)
```

Note for the final submission: this folder is internal working material; the rubric
penalises leftover scaffolding, so move it out of the delivered repo.
