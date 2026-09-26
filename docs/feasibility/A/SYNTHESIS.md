# SYNTHESIS — ARCA topic feasibility study (Agent A)

> **For an agent or a teammate reading this cold.** This file is the entry point to
> `docs/feasibility/A/` on branch `feasibility-A`. It states what was studied, what was
> *measured* versus *estimated*, the current recommendation, and what is still open. The team
> decides what to present; this document does not decide for them. Every number below links
> to the file that produced it. Anything not measured is labelled ESTIMATE or UNVERIFIED.
>
> Status: **stopped by the user on 2026-09-26** before the pass@1 measurements finished and
> before `03_decision.md` was written. Working notes: English. The proposal draft: Spanish.
> The rubric penalises leftover scaffolding, so delete `docs/feasibility/` before the final
> submission.

## 1. Context in five lines

- ARCA practice (MGP, MIA ICAI 2026-27): a team of 3 picks one topic and builds 4 stacked phases (a GRPO reasoning model, 3 real tools, RAG, a ReAct agent), graded through a FastAPI.
- The topic must have (1) an automatically verifiable task, (2) a real external HTTP API, a compute tool and a sandboxed action tool, and (3) a licensed corpus. Sources: `docs/enunciado.tex`, `docs/topic_debate_brief.md` §2.
- Compute: a 16 GB MIG slice, Qwen3-0.6B/1.7B students, Qwen3-4B teacher.
- The proposal (`docs/00_propuesta.md` format) must be approved before phase 1.
- The user's candidate was **captcha solving**. Agent A added 4 high-feasibility topics for contrast. A parallel Agent B runs the same study in `docs/feasibility/B/`.

## 2. Bottom line

| Rank | Topic | Score (without row C) | Verdict | One-line why |
|---|---|---|---|---|
| 1 | **Factura de la luz 2.0TD** | 38/42 | GO | Spanish legal corpus the model lacks, keyless live API (REData), `.ics` action, clean generator |
| 2 | **Triaje CVSS v3.1** | 37/42 | GO | The best APIs (NVD + OSV + KEV, keyless), a closed-form verifier, 30k mineable real pairs; English corpus |
| 3 | Pasajero aéreo (Reg. 261/2004) | 35/42 | GO-IF-FIXED | A strong legal rule tree, but the flight API is weak (OpenSky historical = HTTP 403 anonymous) |
| 4 | Nutri-Score 2023 | 31/42 | GO-IF-FIXED | A great OFF oracle; corpus licence unclear and in EN/FR |
| 5 | **Laboratorio de captchas** (user's idea) | 28/42 (30/45 with C=2) | GO-IF-FIXED, else KILL | Learnable (measured), but needs image input to `/reasoning`, has a weak API and user, and ethics framing |

- **Recommended:** winner = luz, fallback = CVSS.
- **Deciding criterion between the top two:** row G/H. A Spanish, post-cutoff, licensed corpus where RAG demonstrably adds knowledge (the brief's explicit preference) beats the stronger API set of CVSS.
- **What would flip it:**
  - (a) Luz completions don't fit the GRPO budget (> 768 tokens) while CVSS's do.
  - (b) The team has security interest or experience (row N was scored 2 for all, since the team is unknown).
  - (c) The professor considers luz too close to his "copiloto fiscal" example (row O).

Full table with every row: [`ranking_table.md`](ranking_table.md). Per-row justifications are at the end of each `02_*.md`.

## 3. What was measured (evidence you can rerun)

| Evidence | Result | File |
|---|---|---|
| Generators (all 5), `sample_params / solve / render` pattern of `rlm/generate_problems.py` | 40–200 problems/split, **0 answer leaks** (after fixes), **0 param-hash overlap** train/test/OOD, 4 templates each | `*/generator.py`, `*/generator_output.txt`, `*/data/*.jsonl` |
| Branch balance fixes | EU261 bands 16/18/6 → 70/64/66 (n=200), zero-answers 75 % → 45 %. Luz bono-cap branch 21:2 → 15:4. Nutri-Score grades E-dominated → A..E 17/20/63/57/43 | same |
| Formula self-checks | CVSS: Log4Shell vector = 10.0 (matches the live NVD API), 9.8, XSS 6.1. Nutri-Score: OFF's live 2023 breakdown for barcode 8480000160164 reproduced (score 1, B) | asserts in `cvss/generator.py`, `nutriscore/generator.py` |
| Captcha learnability (144-pipeline grid, RapidOCR, n=100) | test: raw 41 %, random 32 %, best fixed 50 %, **oracle 71 %** (headroom +21 pts); OOD: 49 / 42 / 57 / 83 % | `captcha/headroom_test.json`, `headroom_ood.json`, `02_captcha.md` §2 |
| Live APIs | REData 200 keyless (24 PVPC values); NVD 200 keyless; OSV 18 advisories; KEV 1,726 entries; OFF per-component points; HF datasets-server rows; OpenSky `/states/all` 200 but `/flights/*` **403** | each `02_*.md` §3 |
| Corpus parsing with the repo's `rag.ingest.read_document` | 11 sample docs parse cleanly. BOE tolls PDF has **16.9 % table-like lines** (needs table-aware chunking); the rest < 3.5 % | `common/parse_check.py`, each `02_*.md` §5 |
| Primary-source facts | IEE 5.11269632 % (Ley 38/1992 art. 99); bono social 35/50 % in RD 897/2017 (temporary 42.5/57.5 % UNVERIFIED for 2026); 2026 2.0TD tolls P1 3,233054 €/kW·año transport; Reg. 261/2004 Art. 7 quoted; NVD 2025 backlog (13,785 of 45,314 NVD-primary) | `02_luz.md`, `02_eu261.md`, `02_cvss.md` |
| Model availability | Qwen3-VL-2B/4B Instruct + Thinking exist (Apache-2.0); installed TRL 1.13 `GRPOTrainer` handles processors/images | `02_captcha.md` |

## 4. What was NOT measured (open, be careful citing)

- **pass@1 for Qwen3-0.6B / Qwen3-4B on the four text topics (row C).**
  - The harness is ready (`common/pass_at_1.py`, supports `--device cpu` and `--load-4bit`).
  - The runs were stopped by the user. The laptop GPU (RTX 3050 4 GB) was occupied by Agent B, and CPU fp32 needs about 1 h per topic.
  - All difficulty statements for those topics are ESTIMATE.
- VLM pass@1 for captcha (a 2B VLM doesn't fit in 4 GB). Only the OCR headroom proxy was measured.
- Distillation acceptance rates: ESTIMATE only.
- Licences marked UNVERIFIED: the CNMC/IDAE web content, the Santé publique France documents, the AESA pages and the FIRST CVSS docs.

## 5. Findings worth telling colleagues regardless of topic

1. **Repo bug:** `rlm/rewards.normalize_number("79,90")` returns `"7990"` (it strips commas). Any euro/Spanish-decimal topic needs its own verifier. A comma-aware parser is in `common/pass_at_1.py::parse_number`.
2. **The "always answer the majority label" baseline** can be large: 45 % zeros in EU261. Report it next to pass@1.
3. **Hidden label traps** found by generating data:
   - Switzerland and Norway apply Reg. 261/2004 by agreement, so they're not "non-EU".
   - "Swiss" is a Community carrier.
   - Realistic prices never trigger the electricity-tax floor, so that branch is dead in the real world and has to be forced in test.
4. **An OOD split can be easier than test**: the captcha OOD with a new font scored higher. Check the OOD difficulty, don't assume it.
5. **A shared laptop GPU across parallel agents** caused one PC crash and blocked measurements. Run pass@1 on the DGX slice or sequentially.

## 6. The user's captcha idea: decisions already made in the grilling session

- **Framing:** a robustness lab on self-generated captchas plus public datasets, never live third-party sites.
- **Phase-1 answer:** a JSON preprocessing pipeline (11 whitelisted OpenCV ops). A soft RL length penalty, plus a hard executor cap of 20 ops.
- **Brain:** a VLM (Qwen3-VL-2B) with screenshot input. **This requires the professor to approve** adding `image_b64` to `ReasoningRequest` (currently `question: str` only).
- **Fallback:** a text model fed extracted image features.
- **Scope:** distorted text + math captchas. Slider dropped; image grids are a stretch goal.
- **Red team:** ≥ 2.5 damaging answers (the API contract, "classification not reasoning", weak API/user). So it's downgraded to GO-IF-FIXED, conditional on that approval.

## 7. Files (read in this order)

| File | What |
|---|---|
| `SYNTHESIS.md` | this file |
| `ranking_table.md` | 15-row scores for all 5 topics |
| `01_longlist.md` | 11 candidates, A–D desk scores, why each was cut or kept |
| `02_luz.md`, `02_cvss.md`, `02_eu261.md`, `02_nutriscore.md`, `02_captcha.md` | deep dives: task, verifier edge cases, API, tools, corpus, 5 gold questions, 5 agent tasks + impossible task, domain reward and its hack, risks, closest professor example (quoted), scorecard |
| `04_red_team.md` | 10 hardest professor questions × top 3 (+5 for captcha), with rebuttals and verdicts |
| `propuesta_borrador_luz.md` | **Spanish** proposal draft for the winner, in the `docs/00_propuesta.md` format (team placeholders) |
| `plan_y_reparto_borrador.md` | Spanish phase plan + split of work across 3 people |
| `common/` | `report.py` (stats/leak/dedup), `pass_at_1.py` (eval harness), `parse_check.py`, `scorecards.py` (source of the scores) |

Missing: `03_decision.md`. Its content is sections 2–6 of this file plus the two Spanish drafts.

## 8. Next actions (for whoever continues)

1. The team picks the topic(s) to present, using §2 and the per-topic scorecards.
2. Measure row C for the chosen topic on a free GPU: `uv run python docs/feasibility/A/common/pass_at_1.py --data docs/feasibility/A/<topic>/data/test.jsonl --n 20 --verifier numeric --tol <0.01 luz | 0 others>`. Add `--model Qwen/Qwen3-4B` for the teacher.
3. If captcha is kept: email the professor this week about image input to `/reasoning`, before any phase-1 work.
4. Adapt `propuesta_borrador_luz.md` (or write the equivalent for the chosen topic), fill the team names, and save it as `docs/propuesta.md`.
5. Compare with Agent B's study (`feasibility-B` branch) before deciding.
