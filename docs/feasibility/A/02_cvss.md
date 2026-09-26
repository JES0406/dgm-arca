# 02 — Triaje de vulnerabilidades con CVSS v3.1

**One sentence.** Un agente para el equipo de seguridad de una pyme que, a partir de un aviso de
vulnerabilidad en lenguaje natural, calcula la puntuación CVSS v3.1, comprueba en NVD/OSV si
afecta a las versiones instaladas y abre un ticket de parcheo priorizado.

## 1. Verifiable task (phase 1)

Prototype: [`cvss/generator.py`](cvss/generator.py). Output: [`cvss/generator_output.txt`](cvss/generator_output.txt).

```
uv run python docs/feasibility/A/cvss/generator.py --n 40
```

- **Answer:** the CVSS v3.1 base score, one decimal. `NumericVerifier(tolerance=0)` on the parsed float.
- **Parameters:**
  - The 8 base metrics (AV, AC, PR, UI, S, C, I, A).
  - Product: 9 types.
  - A phrasing index per metric: 2–3 Spanish paraphrases per metric value, 8 facts shuffled in random order.
- **Templates:** 4.
- **`solve`:** the FIRST v3.1 formula, including Appendix A `Roundup` (integer arithmetic, robust to float error) and the Scope-dependent PR weights.
- **Self-checks** (assert, run every time):
  - CVE-2021-44228 vector gives **10.0**, which matches NVD's live response.
  - AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H gives 9.8.
  - A typical reflected XSS gives 6.1.
  - `roundup(4.02)` = 4.1 and `roundup(4.000001)` = 4.0.
- **Real output** (40/split):
  - 0 leaks and 0 param-hash overlap in all splits.
  - 27–29 distinct scores per 40 problems.
- **Branch table** (train/test/OOD):
  - Severity low 12/7/3, medium 22/25/26, high 6/7/9, critical 0/1/2.
  - **Critical is under-represented.** Fix: over-sample AV:N ∧ PR:N ∧ ≥ 2 High impacts to ~15 %.
  - `roundup_beats_round` True 17/26/22: in ~50 % of problems, naive half-up rounding gives the wrong answer, which is a built-in trap.
- **OOD split:** **Scope Changed** is never seen in train/test. It swaps the PR weights (0.62→0.68, 0.27→0.50), uses a different impact polynomial, and multiplies by 1.08. That is the cleanest "SFT memorises, RL generalises" probe of the five topics.
- **Second data source (strategy 2, mining):** NVD bulk feeds give real (description, vector) pairs.
  - Counted from the downloaded files: `nvdcve-2.0-2023.json.gz` has **30,030 of 31,444** CVEs with a v3.1 metric, 25,704 of them NVD-primary.
  - The 2025 file has 40,583 of 45,314 with v3.1 but only **13,785 NVD-primary**. That's the NVD enrichment backlog: mined labels from 2025 are mostly CNA-assigned, which makes them noisier.
  - Use: an English real-description test set, and a "desk template vs real prose" OOD.
- **Verifier edge cases:**
  1. The answer "9.8 (Critical)": the last number is used, and the category is ignored.
  2. The answer is the vector string instead of the score: no number, so it fails. Or accept `CVSS:3.1/...` and compute its score? Decision: accept a vector and score it, because it is *more* informative, and log it.
  3. "10" vs "10.0": numeric equality holds.
  4. A Spanish comma "6,1" is parsed by our parser. The repo's `normalize_number` would turn it into 61, so the verifier must use the comma-aware parser.
  5. Zero impact (C=I=A=N) is excluded by the generator (not a reportable vulnerability). A test case asserts 0.0.

## 2. Difficulty

PASS1_CVSS

## 3. External API

| API | Docs | Key | Limits | Verified call | Verdict |
|---|---|---|---|---|---|
| **NVD CVE API 2.0** | https://nvd.nist.gov/developers/vulnerabilities | Optional (free); without a key the published limit is 5 req / 30 s (ASSUMPTION from the docs page: the downloaded docs HTML was a 2 kB JS shell) | see left | `GET https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2021-44228` → **HTTP 200**, `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H`, `baseScore 10.0` | Stable US-government API, works without a key. The tool must sleep/retry on 403/503 |
| **OSV.dev** | https://osv.dev/docs/ | None | Generous (no published hard limit) | `POST https://api.osv.dev/v1/query` `{"package":{"name":"jinja2","ecosystem":"PyPI"},"version":"2.4.1"}` → **18 advisories** (GHSA-462w-v97r-4m45, …) | Best "¿me afecta mi versión?" lookup; Google-run, stable |
| CISA KEV feed | https://www.cisa.gov/known-exploited-vulnerabilities-catalog | None | Static JSON | Downloaded: catalogVersion **2026.09.25**, **1,726** entries | Useful "¿se explota activamente?" signal |

Row D is the strongest of the five topics: two keyless, stable APIs, plus a static feed.

## 4. Compute and action tools

- **Compute:** `cvss_calculator(vector)` returns the base score, severity and sub-scores. It is the same code as `solve`. The model must not compute 8.22×0.85×0.77×0.85×0.85 and a 15th power in its head; `roundup_beats_round` shows how often the mental approximation is wrong.
- **Action:** `open_ticket(title, cve, score, priority, body)` writes a Markdown/JSON ticket into a local `outputs/tickets/` folder, or POSTs to a webhook.site test URL. It is registered with `requires_confirmation=True`. The grader observes the returned path or ticket id and file content. It is sandboxed because no real tracker is involved.

## 5. Corpus

| Source | URL | Licence | Format | Size | Parse check (`rag.ingest.read_document`) |
|---|---|---|---|---|---|
| CVSS v3.1 specification | https://www.first.org/cvss/v3.1/specification-document | FIRST: free to use with attribution (ASSUMPTION; terms page not parsed) | HTML | ~25 pp | downloaded 89 kB HTML |
| CVSS v3.1 User Guide | first.org | as above | PDF | ~20 pp | downloaded |
| CVSS v3.1 Examples (worked vectors with rationale) | first.org | as above | PDF | ~50 pp | **87,385 chars, 0.6 % table-like lines, 0 garbage** |
| NIST SP 800-40r4 (patch management) | https://csrc.nist.gov/pubs/sp/800/40/r4/final | US Government work, public domain | PDF | 36 pp | **75,574 chars, 0.9 % table-like, 0 garbage** |
| NIST SP 800-30r1 (risk assessment) | csrc.nist.gov | public domain | PDF | 95 pp | downloaded |
| OWASP Top 10 2021 | owasp.org | CC BY-SA 4.0 | HTML/MD | ~10 pages | not checked |
| INCIBE-CERT guides (Spanish) | incibe.es | ASSUMPTION: reuse with attribution | PDF | 5–10 docs | not checked |

That's 30–50 documents and 500+ pages. **Language caveat:** most sources are in English, and the
enunciado asks for Spanish user-facing text. Answers stay in Spanish while citing English
chunks, which is an honest limitation to report. INCIBE adds Spanish documents.

**Five gold questions only answerable from the corpus:**
1. "Según los ejemplos oficiales de FIRST, ¿qué vector se asigna a la vulnerabilidad de envenenamiento de caché DNS por ataque de cumpleaños?" (Examples doc).
2. "¿Cuándo debe puntuarse Scope como Changed según la guía de usuario 3.1?" (User Guide §3.5).
3. "¿Qué cuatro formas de respuesta al riesgo propone la NIST SP 800-40r4?" (accept, mitigate, transfer, avoid; §2).
4. "¿Qué diferencia hay entre la puntuación base y la temporal en CVSS 3.1?" (Spec §1–§3).
5. "En CVSS 3.1, ¿cómo se redondea la puntuación final y por qué se cambió la función Roundup respecto a 3.0?" (Spec Appendix A).

## 6. Agent tasks

1. "Nos avisan de CVE-2021-44228; ¿cuánto puntúa y abre ticket si es crítica." → `nvd_lookup` + `open_ticket`. Check: score 10.0 and the ticket file has priority P1.
2. "Tenemos jinja2 2.4.1 en producción, ¿estamos afectados y cuál es la peor?" → `osv_query` + `nvd_lookup`/`cvss_calculator`. Check: `n_vulns ≥ 1` and the max score equals the NVD max.
3. "Este informe de pentest dice: [prose]. Calcula el CVSS y dime qué recomienda NIST para ese nivel." → `cvss_calculator` + `search_knowledge_base`. Check: the score equals ground truth and a 800-40 chunk is cited.
4. "¿Está CVE-XXXX en el catálogo KEV? Si lo está, ticket urgente." → KEV lookup + `open_ticket`. Check: the boolean matches the feed.
5. "Recalcula esta puntuación de proveedor: `CVSS:3.1/AV:L/AC:H/PR:H/UI:R/S:C/C:L/I:L/A:N`, ¿nos mintieron?" → `cvss_calculator` + KB (Roundup rule). Check: exact score.
- **Impossible task:** "Parchea automáticamente el servidor de producción." There is no tool with that power, and it would be unsafe. The agent must refuse the action and offer the ticket.

## 7. Domain reward

`metric_trace_reward`: +1 if the `<think>` contains a syntactically valid CVSS 3.1 vector whose computed score equals the `<answer>`, i.e. a self-consistent justification.

- **Hacking:** the model writes any vector and back-fits the answer to it. Accuracy then drops, but the domain reward stays 1.
- **Mitigation:** weight it 0.25 and gate it on accuracy (domain reward only if the answer is correct), or give per-metric partial credit against the true vector: 1/8 per correct metric, which is also a denser signal for GRPO. The per-metric version is the recommended one.

## 8. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Template prose → vector is too easy once the paraphrase table is memorised | High | High (interpretation) | Paraphrase pass with the teacher; the mined NVD real-description test set as OOD; report both |
| NVD backlog: 2025 labels mostly CNA-assigned | Verified | Medium | Mine 2021–2023 NVD-primary only (25.7k in 2023) |
| NVD rate limit (no key) during grading | Medium | Medium | A free key in `.env`, a local cache, retry with backoff; OSV as the primary |
| English corpus vs Spanish answers | Certain | Low | INCIBE docs; state the choice |
| Security topic: "offensive" misuse | Low | Low | Scoring and patching only; no exploit generation tool |
| Compute: prompts ≈ 180 tokens, answers short | — | Low | The best fit for 384-token GRPO completions of the five topics |

## 9. Closest professor example

**"Agente de triaje y reproducción de bugs para un proyecto open source"** (Software). Quote:

> "Este tema tiene el mejor verificador posible (tests que se ejecutan) y el mayor riesgo de
> *reward hacking*: el modelo aprenderá a escribir tests que fallan por cualquier motivo. Quiero
> ver cómo lo detectáis y cómo diseñáis la recompensa para evitarlo. En la fase 2, la seguridad
> del ejecutor es parte de la nota: qué puede y qué no puede hacer el código que ejecuta el
> agente."

**How ours differs:** the verifier is a closed-form specification rather than code execution, so
there is no sandbox risk and the reward can't be hacked through flaky tests. It triages
*vulnerabilities*, not bugs, and its hard cases are Scope Changed, the Roundup edge cases and
paraphrased metrics.

## 10. Scorecard

SCORECARD_CVSS
