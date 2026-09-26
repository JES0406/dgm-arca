# 01 — Longlist (Agent B)

Date: 2026-09-26. Author: feasibility agent B. Bias requested: niche / unusual domains,
Spanish context, while still covering broadly.

Scores are rows **A–D** of the scorecard in `docs/topic_debate_brief.md` §6, 0–3 each,
**from desk knowledge only** (verified later, in `02_*.md`, for the shortlist):

- **A** verifiable task exists (deterministic `solve(params)`),
- **B** dataset without hand labels,
- **C** right difficulty for Qwen3-0.6B/1.7B (base low, teacher decent),
- **D** real, free external HTTP API.

Any 0 in A–D is a kill unless fixed. Candidate 1 was given by the human (CANDIDATE_TOPICS);
2–14 are Agent B's own.

| # | Candidate | Domain | Verifiable task (one line) | A | B | C | D | Sum | Decision | Reason |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Study planner over MIA course material** | Education | Capacity arithmetic: hours left after a study log, feasibility + shortfall, required h/day, finish date under a fixed order with holidays | 3 | 3 | 2 | 3 | **11** | **KEEP** | Given topic. Generator trivial; Nager.Date holidays API already called live (32 ES holidays 2027). Risk: corpus licence (course slides) and "is it too easy?" |
| 2 | **PVPC electricity bill & load shifting (2.0TD)** | Energy / consumer | Bill amount to the cent from hourly consumption + periods P1/P2/P3 + taxes; cheapest k-hour window | 3 | 3 | 2 | 3 | **11** | **KEEP** | Spanish-specific rules (periods, electricity tax, IVA changes) the model does not know; REData API (REE) is public. Not among the 13 examples. |
| 3 | **Nutri-Score (2023 algorithm) & food-labelling assistant** | Food / consumer | Nutri-Score points and letter from a nutrition table | 3 | 3 | 2 | 3 | **11** | **KEEP** | Published point tables = rule engine; updated 2023 algorithm is barely in model knowledge; Open Food Facts API free; EU/AESAN corpus. |
| 4 | **PER boating-licence navigation tutor** | Nautical / education | True course from compass course (declination + deviation), ETA, tide by rule of twelfths | 3 | 3 | 2 | 2 | **10** | **KEEP** | Niche; exam formulas are deterministic; official exam banks may exist (mining). API is weakly linked (Open-Meteo marine). |
| 5 | **FAO-56 irrigation scheduler for small farms** | Agriculture | Weekly irrigation depth / drip run-time from ET0, Kc stage, rain, efficiency | 3 | 3 | 2 | 3 | **11** | **KEEP** | Open-Meteo returns ET0 with no key; FAO-56 tables + Spanish regional guides; model knows the idea but not the tables. |
| 6 | CTE DB-SI evacuation checker (building fire code) | Architecture | Occupancy from m²/person densities → required exit width | 3 | 3 | 2 | 1 | 9 | cut | Good rules, weak API (Catastro OVC gives use/area but not what the checker needs); overlaps legal-rules pattern. Fallback candidate. |
| 7 | MIDE hiking-time & route planner | Outdoors | MIDE time from horizontal distance and ascent/descent | 3 | 3 | 2 | 3 | 11 | cut | Formula is one line (easy branch dominates, C risk), corpus thin (MIDE manual + park rules, tens of pages). |
| 8 | Cercanías/Renfe GTFS connection planner | Transport | Earliest arrival with transfers | 3 | 2 | 1 | 2 | 8 | cut | Needs graph search the 0.6B model cannot do in-head in 384 tokens; GTFS is a file, not a query API. |
| 9 | LER waste-code classifier (Decisión 2014/955/UE) | Environment | 6-digit LER code for a waste description | 2 | 1 | 0 | 1 | 4 | **kill** | ~840 labels, same trap as the MedDRA example; no labelled source without hand work. |
| 10 | DGT fines & licence points | Legal | Fine amount with 50 % prompt-payment reduction, points lost | 3 | 3 | 2 | 1 | 9 | cut | Too close to the professor's "plazos administrativos" example; no DGT open API. |
| 11 | Plusvalía municipal (IIVTNU) calculator | Tax | Tax from the two methods (objective coefficients vs real gain), minimum wins | 3 | 3 | 2 | 1 | 9 | cut | Close to the tax-copilot example; Catastro does not expose cadastral value. |
| 12 | Pool water chemistry (Langelier index, RD 742/2013) | Health / facilities | LSI from pH, temperature, hardness, alkalinity, TDS | 3 | 3 | 1 | 0 | 7 | **kill** | Log/temperature factors hard for 0.6B; no public API. |
| 13 | Amateur astronomy observation planner | Science | Altitude/azimuth of an object at a time and place | 3 | 3 | 0 | 3 | 9 | **kill** | Spherical trig in-head: base and teacher both ~0 %. |
| 14 | Home PV self-consumption sizing (PVGIS) | Energy | Annual kWh and payback from PVGIS output | 3 | 2 | 1 | 3 | 9 | cut | Answer depends on API numbers, so the generator must embed them; overlaps #2 — kept as a possible extension of #2. |

## Shortlist for the deep phase (5)

1. Study planner over MIA course material (given)
2. PVPC electricity bill & load shifting
3. Nutri-Score & food labelling
4. PER boating-licence navigation tutor
5. FAO-56 irrigation scheduler

Why 5 and not 6: #6 (CTE) and #7 (MIDE) tie on A–D with #4/#5 but each has a structural
weakness (API or corpus) that the deep phase would only confirm; depth on 5 beats breadth
on 6.

Coverage check: 9 domains in the longlist (education, energy, food, nautical, agriculture,
architecture, outdoors, transport, environment, legal, tax, health, science); 12 of 14 are
not close to any of the professor's 13 examples.
