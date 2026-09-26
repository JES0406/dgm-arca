# Topic debate brief — ARCA practice (MGP, MIA ICAI 2026-27)

> **For Claude Code sessions.** Read this whole file before replying. Your job is to
> **debate the user on candidate topics** for the ARCA practice, not to pick one for them
> and not to write code. Be adversarial: attack each topic where the professor will attack
> it. Concede only when the user gives a concrete answer (a data source, a verifier
> function, an API URL). End each topic with a scorecard (section 6).
>
> Internal working file. Delete it (or move it out) before the final submission: the
> rubric penalises leftover scaffolding, and human-facing text must be in Spanish.

Written 2026-09-26 from a full read of the repo at commit `11dce57`. If files have changed
since, trust the files.

---

## 1. What the assignment is (one paragraph)

Teams of **three** build ARCA ("Agente con Razonamiento, Conocimiento y Acción") on a
**free topic of their choice**, in four phases that stack on each other, each exposed as a
FastAPI endpoint that the professor grades **by calling the API** (via ngrok, from
`docker compose up api`). Phase 1 trains a small reasoning model (distillation → SFT with
LoRA → GRPO with verifiable rewards). Phase 2 adds three real tools with a hand-written
tool-use loop. Phase 3 builds a RAG over a real corpus with three retrievers. Phase 4 wires
everything into a hand-written ReAct agent. Phase 0 is a one-page **topic proposal** that
must be approved before phase 1 starts ("hasta que os diga que está aprobada, no empecéis
la fase 1"). Phase 1 kicked off **Monday 21 Sept 2026**, so the proposal is urgent.

Source: `docs/enunciado.tex` §1–§2 (PDF is the same, 5 pages), `README.md`.

## 2. The three hard conditions on the topic

From `docs/enunciado.tex` §1 (box "Tres condiciones") and `README.md` "La idea":

1. **A task with an automatically checkable answer** — number, date, code passing tests,
   query result, label. No verifier → no reward → no RL. *This is the #1 filter.*
2. **Tools that make sense in the domain** — something to look up (a **real external HTTP
   API**, not mocked), something to compute/execute, something that **acts** with an
   observable side effect (write file, calendar event, test webhook; sandboxed, never a
   real system).
3. **Real documentation you can collect** — a corpus with a documented license. No corpus
   → no RAG.

Plus the soft condition: *"que resuelva un problema a alguien de verdad, aunque ese
alguien seáis vosotros"* and *"si al terminar podéis enseñar el repositorio en una
entrevista de trabajo"* → portfolio value matters.

Professor's own filter (`docs/temas_ejemplo.md` intro): *"Lo que marca la diferencia entre
un tema difícil y uno imposible es que la tarea verificable exista y el corpus sea
accesible. Comprobad eso antes de enamoraros de una idea."* And (`docs/00_propuesta.md`):
*"si la sección de la tarea verificable se escribe sola, tenéis tema."*

## 3. What each phase demands of the topic

Minimums from `docs/enunciado.tex` §3–§6 and each folder README. The column on the right
is what the topic must supply — use it to stress-test.

| Phase | Minimums (graded) | What the topic must supply |
|---|---|---|
| **1 Reasoning** `rlm/` → `POST /reasoning` | Own verifiable dataset (hundreds of problems; thousands if generated) + deterministic `verifier.py` with edge-case tests; distillation with a teacher (default `Qwen/Qwen3-4B`), report acceptance rate; SFT LoRA; GRPO with ≥3 rewards: format, accuracy, **domain reward (justified)**; hand-written GRPO step (advantages, ratio, clip, KL) with tests; pass@1 base/SFT/GRPO, reward & length curves, 5 failure analyses | A problem family with (question, answer) pairs obtainable **without hand annotation** (6 strategies in `docs/datasets.md`), solvable-ish by a **0.6B–1.7B** model in a few hundred tokens, with an OOD split, and a meaningful 3rd reward |
| **2 Tools** `tool_use/` → `POST /tools` | 3 real tools: external HTTP API, compute/execute, action with side effect (`requires_confirmation=True`); JSON Schema from Pydantic, validation errors fed back; own 5-step loop, multi-step + parallel calls, **no smolagents**; 30-case bench incl. no-tool cases; selection & argument accuracy; with vs without tools | A **free, reliable, public API** (rate limits! keys!), a computation the model shouldn't do in its head, a harmless observable action |
| **3 Knowledge** `rag/` → `POST /rag` | Real corpus (tens of docs / hundreds of chunks), reproducible ingest, license; recursive vs semantic chunking compared with numbers; Qwen3-Embedding w/ instruction, dense store, BM25, hybrid with λ tuned on data; **50-question gold set** annotated with the answering chunk; Recall@k & MRR ×3 retrievers; cited answers + automatic citation-existence check; say "no lo sé" when corpus lacks the answer | Documents that are **downloadable, licensed, parseable** (PDF tables = pain), and contain facts the base model doesn't know, so gold questions are meaningful |
| **4 Agent** `agent/` → `POST /agent` | Own ReAct loop with `final_answer`, step limit, per-tool timeouts, error recovery; KB as `search_knowledge_base` tool; 3 brains compared (base `Qwen3-0.6B`, own phase-1 model, thinking `Qwen3-1.7B`); multi-turn memory with auto-summary; **20 tasks chaining ≥2 tools** with automatic success check; JSON agent vs smolagents `CodeAgent`; visible trace UI | Realistic multi-step user tasks that genuinely need search + compute + act, with checkable final answers; a sensible "impossible task" behaviour |

Professor adds per-topic requirements after approving the proposal (`docs/temas_ejemplo.md`
last section): size minimums scale with what the topic allows; the professor proposes the
3rd reward; hard test cases are agreed together; side-effect tools hit sandboxes only;
health/legal/finance/social topics need a disclaimer in **every** answer; any personal
data must be synthetic; phase 4 is graded with **5 unseen tasks + 1 impossible task**.

## 4. How it is graded (why the topic matters for the grade)

Each phase weighs the same; within each phase (`docs/rubrica.md`, `docs/enunciado.tex` §8):

| Criterion | Weight | Topic implication |
|---|---|---|
| Implementación correcta | 30 % | Professor's script sends requests **similar to your benches and unseen ones**. A topic where the small model gets ~0 % on unseen cases hurts here. |
| Completitud | 30 % | Every minimum present. A topic lacking a real API or a licensed corpus loses a whole piece. |
| Interpretación y explicación | 30 % | Where excellent vs correct is decided: curves explained, ablations, failure analysis, honest `EXPERIMENTS.md`, **oral defence**. Topics with interesting failure modes (reward hacking, OOD, unit errors, ambiguous chunks) give material to interpret. |
| Limpieza y calidad | 10 % | Reproducibility, tests, Docker, portfolio README, code in English / prose in Spanish, no secrets. |

Oral defence: 10 min per team, 3 min live demo, rest questions to **any** member about
**any** part. A topic where the demo is visually compelling in 3 minutes is a plus.

## 5. Practical constraints the topic must survive

- **Compute**: one MIG slice of an H200 = **16 GB**, sessions ≤ **24 h**, no SSH, no
  Docker inside the DGX, no backups (`docs/dgx.md`). Realistic models: Qwen3-0.6B / 1.7B
  with LoRA in bf16; teacher Qwen3-4B; embeddings Qwen3-Embedding-0.6B. Smoke test uses
  384 max completion tokens, 8 generations per prompt.
  → Tasks needing long inputs (whole contracts, long CSVs) or long reasoning are risky for
  GRPO at this scale. Short prompt + short checkable answer is the sweet spot.
- **Teacher acceptance rate**: if Qwen3-4B can't solve the task, distillation yields almost
  no traces. If Qwen3-0.6B already solves it ~100 %, GRPO has nothing to learn (zero
  advantage in every group). Ideal: base model 10–50 %, teacher 50–90 %.
- **Dataset sizes** (`docs/datasets.md`): SFT 300–800 problems, GRPO 500–2000, test
  100–200 (≈50 hand-audited), OOD test 50–100. Train/test **dedup by parameter hash**.
- **Four errors the professor hunts** (`docs/datasets.md`): train/test leakage; zero
  lexical diversity (one template); all weight on the easy branch (show branch table in
  `EXPERIMENTS.md`); answer leaked in the statement.
- **Phase-1 generator pattern** (`rlm/generate_problems.py`): `sample_params` / `solve` /
  `render`, where `solve` is also the verifier. Preferred default. Mixing ~30 % public
  benchmark as a control group is recommended but the domain set is mandatory.
- **Contamination**: problems reverse-built from corpus chunks must not go into the test
  set if the same chunk is in the RAG corpus.
- **External API**: must be real HTTP, free, reachable from the grader's run through your
  ngrok'd API; handle rate limits and errors.
- **Language**: people-facing text in Spanish; code in English. A Spanish-language domain
  (BOE, AEAT, AEMPS…) fits naturally and is under-represented in the model's knowledge →
  RAG actually helps.
- **Team of 3**, one repo, anyone answers about anything.

## 6. Scorecard — fill one per candidate topic

Score 0–3 each. Any **0 in rows A–D is a kill** unless the user fixes it in the debate.

| # | Criterion | Kill question to ask | 0 | 3 |
|---|---|---|---|---|
| A | **Verifiable task exists** | "Write the signature of `solve(params)` right now. What does it return?" | Answer needs human judgement | Deterministic number/date/label/test result |
| B | **Dataset without hand labels** | "Which of the 6 strategies? Name the params you sample / the source and one row." | "We'll write them" | Generator with thousands + OOD region, or mined real data |
| C | **Right difficulty for 0.6B–1.7B** | "What pass@1 do you expect from Qwen3-0.6B base? From Qwen3-4B?" | 0 % or ~100 % | Base low, teacher decent, GRPO has room |
| D | **Real, free external API** | "URL of the docs? Key needed? Rate limit?" | None / paid / scraped | Stable open-data API, no or free key |
| E | **Meaningful compute tool** | "Why must this not be done in the model's head?" | Trivial | Real calc/exec the model gets wrong |
| F | **Action tool, sandboxed, observable** | "How does the grader see the effect?" | None | File/PDF/ICS/webhook, clearly checkable |
| G | **Corpus: available, licensed, parseable** | "Link + license + format + how many pages?" | Paywalled / scanned images | Tens of docs, open license, text or clean HTML/PDF |
| H | **Gold set writable & meaningful** | "Give me 2 questions only answerable by reading the corpus." | Model already knows | Specific facts the model lacks |
| I | **Agent tasks chain ≥2 tools, auto-checkable** | "Give me one of the 20 tasks and how you check its final answer." | Open-ended prose | Concrete, checkable, uses KB + tool |
| J | **Domain reward is natural** | "What is your 3rd GRPO reward and why does the user care?" | Arbitrary | Units / source / breakdown / schema, justified |
| K | **Interpretation material** | "What will go wrong that you can analyse? Reward hacking? OOD?" | Nothing interesting | Clear failure modes, OOD split, ablations |
| L | **Real user & portfolio value** | "Who uses this tomorrow? Would you show it in an interview?" | Toy | Real user (or you), demo-able |
| M | **Risk / safety overhead** | "Disclaimers, synthetic data, legal exposure?" | Heavy, unmanaged | Light or well handled |
| N | **Team fit & motivation** | "Does anyone know the domain? Will you still care in January?" | No one | Domain knowledge in team |
| O | **Differentiation** | "How is this not just one of the 13 examples copied?" | Verbatim example | Own twist or new domain |

Output per topic: table filled + **top 3 risks with mitigations** + **verdict**
(go / go-if-fixed / kill) + one-sentence topic statement in the proposal's format ("Qué
hace el agente y para quién").

## 7. The 13 professor's example topics (for comparison and borrowing)

From `docs/temas_ejemplo.md`. Each has a "Cómo lo corregiría" section: when a user's topic
resembles one, **read that section to them** — it is the grader telling you what he'll look
for.

| Area | Topic | Verifiable task | Professor's warning |
|---|---|---|---|
| Pharmacy | Interactions & dosing for community pharmacy | Paediatric / renal dose, numeric + units | Unit verifier (mg/kg/day vs mg/dose); neonates, obesity, dialysis; PDF tables chunking |
| Pharmacy | Pharmacovigilance copilot | MedDRA coding (exact label) + Naranjo score | Phase 1 hard: thousands of labels, small model suffers; restrict dictionary |
| Legal | Administrative deadlines & appeals | Deadline date (Ley 39/2015, business days, holidays) | Calendar edge cases; article-level chunking; cite, don't invent |
| Legal | Rental contract review vs housing law | Per-clause label valid/null/doubtful | Clause dataset quality; memorisation; OOD split |
| Finance | Tax copilot for freelancers (IVA 303, IRPF 130) | Exact-to-cent amounts | Deductibility decisions, not just sums; CSV validation; detect inconsistencies |
| Finance | Consumer credit risk (educational) | TAE, French amortisation, DTI | TAE is implicit equation — delegate to tool vs approximate |
| Software | Bug triage & reproduction | Write failing-then-passing test | Best verifier, worst reward hacking; sandbox security graded |
| Software | Library migration assistant | Migrated code passes tests on new version | Silent semantic changes; retriever must separate v1/v2 docs |
| Social | Benefits & social aid navigator | Eligibility yes/no + amount (rule engine) | Plain language reward; ask missing info; cite failing requirement |
| Social | Local public-claims fact checker | True/false/imprecise + correct figure (INE) | Right series/period/scope; honesty when unverifiable |
| Marketing | Campaign analyst with verifiable reports | CAC, ROAS, A/B significance | No stats in the head; trap datasets |
| Marketing | Product sheet writer checked vs catalogue | Strict JSON extraction | JSON-validity curve during GRPO |
| Science | Chemistry tutor | Balancing + stoichiometry | "SFT memorises, RL generalises" with reaction families |

Taking one as inspiration is allowed ("cambiadlo hasta que sea vuestro"); own topics are
preferred ("Si tenéis otro, mejor").

## 8. Reading list for the user (in this order)

1. `docs/enunciado.pdf` (or `.tex`) — the 5-page official summary. **Must read.**
2. `docs/00_propuesta.md` — the template to fill; the output of this debate.
3. `docs/datasets.md` — the 6 dataset strategies, sizes, 4 errors. **Critical for topic
   choice** (the proposal section he'll "squeeze" hardest).
4. `docs/temas_ejemplo.md` — 13 worked examples + how topics become concrete requirements.
5. `docs/rubrica.md` — grading detail.
6. `rlm/README.md` then `rlm/generate_problems.py` — the generator pattern your `solve`
   must follow.
7. `tool_use/README.md`, `rag/README.md`, `agent/README.md` — phase demands (skim now,
   read fully at each phase).
8. `docs/dgx.md` + `smoke/README.md` — compute limits; run `uv run arca-smoke` early.
9. Later: `api/README.md` + `api/schemas.py` (contracts), `docs/EXPERIMENTS_plantilla.md`,
   `docs/informe_plantilla.md`, `docs/github.md`.

## 9. Candidate topics under debate

> **Fill this in.** If it is empty when you (a Claude session) start, ask the user to list
> their candidate topics before anything else — one line each is enough.

| # | Working title | One-line idea | Notes from earlier debates |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |

## 10. Debate protocol for the Claude session

1. Ask for / read the candidate list (§9). Ask who is on the team and what domain
   knowledge each has.
2. For **each** topic, go through the scorecard rows **A → D first** (the kill rows). Ask
   one sharp question at a time; wait for the answer; push back on vagueness ("some API"
   is not an answer, a URL is). Verify claims where possible: fetch the API docs, check the
   corpus license, sketch `solve(params)` together.
3. Then E → O more quickly.
4. Map the topic to the closest example in §7 and quote the professor's "Cómo lo
   corregiría" warning for it.
5. Produce the scorecard, top-3 risks, verdict.
6. After all topics: rank them, name a winner and a fallback, and explain the deciding
   criterion. Do not let the user pick on enthusiasm alone; do not overrule a clear
   motivation preference either ("Porque me interesa" is a valid reason per the template).
7. Offer to draft `docs/propuesta.md` (Spanish, following `docs/00_propuesta.md`)
   for the winner — starting with the verifiable-task section, including two examples with
   answers, the dataset strategy and expected problem counts.
8. Append a dated summary of the debate to §9 "Notes" so the next session continues
   instead of restarting.

Style: direct, concrete, a little ruthless. Challenge; don't lecture. Numbers over
adjectives.

**Course-theory note:** if the debate drifts into MGP course content (how GRPO clipping
works, instruction-aware embeddings, R1 recipe…), the user's global rule applies: answer
only from the `imat-rag` MCP (`search` with `course="MGP"`, cite book/section/page); if it
isn't loaded, say so. Questions about *this repo and assignment* are answered from the
repo files above.
