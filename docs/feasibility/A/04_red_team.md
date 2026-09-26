# 04 — Red team: the ten hardest professor questions per top topic

The format for each question: the **objection** (as the professor would put it), then the **rebuttal**
with evidence from this study, then a **verdict**: holds / holds with a fix / damaging.
A topic is downgraded if more than two answers are "damaging".

For comparison, a short red team for the user's own candidate (captcha) is at the end, even though it
is not in the top 3.

---

## A. Factura de la luz 2.0TD

1. **"Esto es aritmética con una hoja de reglas. ¿Dónde está el razonamiento?"**
   - **Rebuttal:** 7 rounded concepts and 3 decisions before calculating: whether the bono cap binds (35/65 % of bono cases), the territory tax (3 regimes) and the OOD price change.
   - The domain reward checks the breakdown, concept by concept.
   - pass@1 of the 0.6B base is measured in `02_luz.md` §2, and it's low.
   - **Verdict: holds.**
2. **"Vuestro verificador numérico del repo convierte 79,90 en 7990."**
   - **Rebuttal:** found in this study. We ship a comma-aware parser with tests (`common/pass_at_1.py::parse_number`) and will add `tests/test_verifier.py` cases for "79,90", "1.234,56" and "79.9".
   - **Verdict: holds** (and it's a point in our favour at the defence).
3. **"La rama del mínimo del impuesto eléctrico no sale nunca en vuestro dataset."**
   - **Rebuttal:** correct: 0/120 in the prototype, because realistic prices make 5.11 % ≫ 1 €/MWh. We report it as a dead branch and add 5–10 synthetic near-zero-price cases to test, so the verifier tests cover it.
   - **Verdict: holds with a fix.**
4. **"Los valores regulados cambian (bono social 35/50 % vs 42,5/57,5 %). ¿Cuál es la verdad?"**
   - **Rebuttal:** phase 1 grades against a dated rule sheet printed in the prompt (self-consistent). RD 897/2017 art. 6.3 says 35/50 %, and the temporary RDL values are UNVERIFIED for 2026. The RAG corpus holds both, and the agent cites the version.
   - That's an interpretation opportunity: "el modelo sigue la hoja, no su memoria".
   - **Verdict: holds.**
5. **"¿El prompt con la hoja de reglas cabe en GRPO con 384 tokens de completion?"**
   - **Rebuttal:** the prompt is ≈ 800 tokens, which isn't limited. The *completion* is the risk: see the measured mean tokens and the truncation rate in §2.
   - Plan: max_completion 768 on the 16 GB slice (0.6B, G=8 fits), or an ablation that drops the sheet after SFT.
   - **Verdict: holds with a fix.**
6. **"Esto se parece a mi copiloto fiscal."**
   - **Rebuttal:** a different base (energy regulation, not VAT/IRPF), a live API (REData), and an action that optimises the future rather than filing a form. The "decide before you calculate" analogue is the bono cap and the territory.
   - **Verdict: holds.**
7. **"¿La API de REE tiene límite? ¿Y si se cae el día de la corrección?"**
   - **Rebuttal:** verified keyless on 2026-09-26 (24 PVPC values for 2026-09-20). It has been stable since at least 2020 (ASSUMPTION from its long-lived URL scheme). The tool caches responses per date, and ESIOS is the fallback.
   - **Verdict: holds.**
8. **"El corpus del BOE son tablas. ¿Cómo lo vais a trocear?"**
   - **Rebuttal:** measured 16.9 % table-like lines in the tolls PDF. We'll use the BOE HTML (`<table>` rows) and chunk by table row with the header repeated. The gold questions include exact toll values (P1 transport 3,233054 €/kW·año) that need that chunking.
   - **Verdict: holds.**
9. **"¿Cómo compruebo la acción?"**
   - **Rebuttal:** an `.ics` file in `outputs/calendar/`. The grader parses DTSTART and compares it with the argmin window recomputed from the same REData prices.
   - **Verdict: holds.**
10. **"¿Quién es el usuario de verdad?"**
    - **Rebuttal:** any household on PVPC or a fixed-price contract. Among CNMC's own consumer complaints, billing is a top category (ASSUMPTION; not checked in this study). The team members themselves pay these bills.
    - **Verdict: holds, but weakly evidenced.**

**Damaging: 0.** Survives.

---

## B. Triaje CVSS v3.1

1. **"Aplicar una fórmula publicada no es razonar."**
   - **Rebuttal:** the hard part is prose → 8 metrics, with Scope changing the PR weights, plus Roundup (in ~50 % of problems naive rounding is wrong, measured via `roundup_beats_round`).
   - The per-metric domain reward shows *which* metric the model misreads, and there's the Scope-Changed OOD.
   - **Verdict: holds.**
2. **"Vuestro dataset son 3 frases por métrica. El modelo memoriza las frases."**
   - **Rebuttal:** true for the generator.
   - Mitigations: (a) a teacher paraphrase pass; (b) a **mined NVD test set of real descriptions** (30,030 v3.1-scored CVEs in the 2023 feed alone, 25,704 NVD-primary). The template→real drop is the key interpretation result.
   - **Verdict: holds with a fix** (this is the main risk).
3. **"Las etiquetas de NVD son ruidosas y en 2025 casi no hay puntuaciones de NVD."**
   - **Rebuttal:** measured: 13,785 of 45,314 CVEs from 2025 are NVD-primary. We mine only NVD-primary 2021–2023 and report the CNA-vs-NVD disagreement rate as a finding.
   - **Verdict: holds.**
4. **"¿Por qué no CVSS 4.0?"**
   - **Rebuttal:** v3.1 remains the vector NVD serves for the vast majority of records (the Log4Shell response carries `cvssMetricV31`). v4.0 uses a lookup of macro-vectors rather than a formula; it's an extension ("ir más allá").
   - **Verdict: holds.**
5. **"El corpus está en inglés y la práctica pide español."**
   - **Rebuttal:** the answers are in Spanish and the citations point to English chunks. INCIBE documents add Spanish. It's a known limitation, stated in the proposal.
   - **Verdict: partially damaging** (row G).
6. **"¿Qué pasa si NVD os limita durante la corrección?"**
   - **Rebuttal:** OSV.dev is keyless (18 advisories returned for jinja2 2.4.1), and there's a local cache plus backoff. An NVD key in `.env` raises the limit.
   - **Verdict: holds.**
7. **"El agente de seguridad puede usarse para atacar."**
   - **Rebuttal:** scoring and patch-ticket tools only. There's no exploit generation, no scanning tool, and the impossible task is "parchea producción".
   - **Verdict: holds.**
8. **"Enséñame reward hacking en vuestro dominio."**
   - **Rebuttal:** the `metric_trace_reward` hack (a back-fitted vector); with the per-metric partial-credit mitigation it can't be hacked without learning. There's also "always answer 5.x", the median-score strategy: measure the constant baseline (the most common score is ≈ 1/40 of the test set, so ≤ 3 %).
   - **Verdict: holds.**
9. **"¿Cuánto tarda cada completion?"**
   - **Rebuttal:** prompts ≈ 180 tokens and the measured completion lengths are in §2. This is the most compact of the five topics.
   - **Verdict: holds.**
10. **"¿Quién es el usuario?"**
    - **Rebuttal:** a 1–3 person IT/security team at a pyme that receives vendor advisories and must prioritise. There's strong portfolio value for security or ML-ops roles.
    - **Verdict: holds.**

**Damaging: 0.5.** Survives.

---

## C. Pasajero aéreo (Reglamento 261/2004)

1. **"Si el 45 % de las respuestas es 0, un modelo que siempre dice 0 saca 45 %."**
   - **Rebuttal:** measured, and reported as the majority baseline. We evaluate on a balanced test subset too, and the branch table goes in `EXPERIMENTS.md`.
   - **Verdict: holds with a fix.**
2. **"¿Qué API de vuelos usáis? OpenSky os da 403."**
   - **Rebuttal:** confirmed (HTTP 403 "You cannot access historical flights" anonymously). A free OpenSky account token in `.env`, or live status only.
   - **Verdict: damaging** (row D is the weakest link).
3. **"La jurisprudencia es más rica que vuestra hoja de reglas."**
   - **Rebuttal:** yes. The agent must say "caso dudoso" and cite the 2024 guidelines when the sheet doesn't cover a case, which becomes an explicit agent task.
   - **Verdict: holds.**
4. **"Las distancias ortodrómicas las inventa el modelo."**
   - **Rebuttal:** no. In phase 1 they come in the statement (real OurAirports coordinates with haversine), and in phases 2 and 4 from the compute tool.
   - **Verdict: holds.**
5. **"¿Zúrich es UE?"**
   - **Rebuttal:** caught in this study. Switzerland (and Norway/Iceland) apply 261/2004 by agreement, so they're excluded from the label set to keep the labels unambiguous; they're a candidate "caso dudoso" family.
   - **Verdict: holds.**
6. **"EUR-Lex bloquea descargas automáticas."**
   - **Rebuttal:** seen (empty HTML for 3 judgments). CURIA PDFs plus manual download of ~25 documents.
   - **Verdict: holds with a fix.**
7. **"¿Es tema legal? Aviso obligatorio."**
   - **Rebuttal:** yes, a fixed footer.
   - **Verdict: holds.**
8. **"¿Qué recompensa de dominio?"**
   - **Rebuttal:** the decisive article, with a penalty for listing extra articles.
   - **Verdict: holds.**
9. **"Test OOD: ¿qué aprende RL que SFT no?"**
   - **Rebuttal:** the connecting-flight rule (origin → final destination) is never seen in train. It's a clean probe.
   - **Verdict: holds.**
10. **"¿Qué acción observable?"**
    - **Rebuttal:** a claim-letter PDF in `outputs/claims/`.
    - **Verdict: holds.**

**Damaging: 1.** Survives, but row D stays the weak point.

---

## D. (User's candidate) Laboratorio de captchas: short red team

1. **"`/reasoning` recibe texto. ¿Cómo me mandáis una imagen?"**
   - **Rebuttal:** an optional `image_b64` field, which needs your approval.
   - **Verdict: damaging until approved.** It's a contract change the grading script doesn't expect.
2. **"Elegir entre 11 operaciones es clasificación, no razonamiento."**
   - **Rebuttal:** the headroom data (oracle 71 % vs best fixed 50 %) shows the choice must be per image, and the traces must cite image evidence.
   - **Verdict: partially damaging.**
3. **"Un portfolio con 'rompo captchas'…"**
   - **Rebuttal:** the robustness-lab framing, with own captchas only.
   - **Verdict: holds, but needs care in every sentence.**
4. **"¿La API externa aporta algo al usuario?"**
   - **Rebuttal:** HF datasets-server for public benchmarks.
   - **Verdict: partially damaging.**
5. **"¿El corpus en inglés y genérico ayuda al modelo?"**
   - **Rebuttal:** only paper-specific numbers.
   - **Verdict: partially damaging.**

**Damaging: ≥ 2.5** → the captcha lab is **downgraded**: GO-IF-FIXED at best (a fix that needs the professor's approval of image input).
