# 02 — Laboratorio de robustez de captchas (user's candidate)

**One sentence (reframed).** Un agente que mide lo robusto que es un esquema de captcha de texto:
dado un captcha generado por nosotros, elige y ejecuta el pipeline de visión clásica que lo hace
legible para un OCR, y con ello informa qué distorsiones protegen de verdad y cuáles no.

**Framing agreed in the grilling session (before this study):**
- Only self-generated captchas plus public datasets, never live third-party sites. A captcha-breaking agent aimed at reCAPTCHA/hCaptcha/GeeTest would violate those services' terms and the enunciado's sandbox rule for action tools.
- The model's phase-1 answer is the **pipeline**, never the captcha text, so the task cannot collapse into "the VLM does OCR".
- Brain: a VLM (screenshot in), with the professor's explicit approval of image input to `/reasoning`. The fallback is a text model fed features from a `describe_image` extractor.
- Scope narrowed to distorted text + math captchas (image grids stretch, slider dropped from phase 1).

## 1. Verifiable task (phase 1)

Prototype:
- [`captcha/generator.py`](captcha/generator.py): renderer, `sample_params`, `solve`.
- [`captcha/pipeline.py`](captcha/pipeline.py): DSL, executor, verifier.
- [`captcha/headroom.py`](captcha/headroom.py): the learnability experiment.

```
uv run --with rapidocr-onnxruntime --with opencv-python-headless python docs/feasibility/A/captcha/generator.py --n 100
uv run --with rapidocr-onnxruntime --with opencv-python-headless python docs/feasibility/A/captcha/headroom.py --split test --n 100
```

- **Parameters:**
  - Kind: text 75 % (4–6 chars from a 25-glyph charset with **ambiguous glyphs removed**: 0/O, 1/I/l, 5/S, 2/Z, 8/B) or math 25 % (`a op b =`, op in + − x).
  - Font: 3 DejaVu faces in train/test; Noto Sans Mono in OOD.
  - Per-char rotation 0/5/12/20°.
  - Sine-warp amplitude 0/2/4 px (+3 px in OOD).
  - Interference lines 0–5, salt-and-pepper 0/3/8 %, Gaussian blur 0/0.8/1.4.
  - Background: flat / gradient / speckle.
  - Render seed.
- **`solve`:** the text, or the integer value of the expression. `eval` was replaced by an explicit regex parser after a security-hook warning.
- **Model answer:** a JSON pipeline over 11 whitelisted ops with enumerated parameters (median, gaussian, otsu, adaptive, open, close, erode, dilate, remove_lines, invert, upscale).
- **Verifier** (`verify`):
  1. Parse and validate the DSL. Unknown op, bad parameter, non-JSON, or more than 20 ops (the hard safety cap) → `ok=False` with a reason, never an exception.
  2. Execute with OpenCV.
  3. Read with **RapidOCR** (pip-only, no system Tesseract; recognition-only mode because a captcha is one line: 0.082 s/call measured).
  4. Normalise case and symbols.
  5. Compare with the truth; math goes read → parse → evaluate → compare.
- **Data:** 100 per split, param-hash overlap train&test = 0, train&ood = 0. Every distortion value appears in every split (see the generator output).
- **Leakage check:** not applicable in the text sense, since the answer lives in the pixels. The analogue is a label leak through the file name: images are named by param hash, never by text.

## 2. Difficulty: measured OCR headroom (replaces VLM pass@1)

A VLM pass@1 could not be measured here. Qwen3-VL-2B needs about 4.3 GB in bf16, and this
laptop's 4 GB GPU was in use by the parallel study anyway. Instead we measured *whether there is
anything to learn*, which is the question pass@1 answers for the other topics.

The grid has 144 pipelines: denoise × line removal × binarisation × morphology × upscale.

| split (n=100) | raw OCR | random pipeline (untrained-policy proxy) | best single fixed pipeline | oracle (≥ 1 pipeline works) | headroom oracle − best fixed |
|---|---|---|---|---|---|
| test | **0.41** | 0.318 | 0.50 (`open k=2`) | **0.71** | **+0.21** |
| OOD (unseen font, +3 px warp) | 0.49 | 0.421 | 0.57 (`median 3 → upscale 2`) | 0.83 | +0.26 |

By kind (test): text is raw 25/70 → oracle 45/70; math is raw 16/30 → oracle 26/30.
Raw per-image results are in `captcha/headroom_test.json` and `headroom_ood.json`.

**Reading:**
- **There is signal for GRPO.** A random pipeline already succeeds 32 % of the time, so 8 rollouts rarely all score 0. The per-image optimum (71 %) is 21 points above any fixed recipe. This directly answers "why not a lookup table?": a single best pipeline caps at 50 %.
- **The best fixed pipeline changes with the distribution** (morphological open on test; median + upscale on OOD). That's evidence the choice must depend on the image, which is the task.
- **29 % of test captchas are unbreakable within the grid.** Those give a flat reward: no learning, but no noise either. They are the "robust" end of the lab's findings.
- **The OOD split is *easier*** (raw 0.49 vs 0.41): Noto Mono is more legible than the DejaVu faces. As a *difficulty* probe, my OOD split failed. The real project should hold out an unseen *distortion type* (perspective or elastic warp) instead of a font.
- **Estimated VLM numbers (ESTIMATE, not measured):**
  - Qwen3-VL-2B-Instruct with no training emitting a *valid* JSON pipeline: 30–60 %, and ≈ 32 % × validity ≈ 10–20 % pass@1.
  - Qwen3-VL-4B-Thinking as teacher: 40–55 % (close to best-fixed), i.e. a distillation acceptance rate of 40–55 %.

## 3. External API

| API | Docs | Key | Verified call | Verdict |
|---|---|---|---|---|
| Hugging Face datasets-server | https://huggingface.co/docs/dataset-viewer | None for public datasets | `GET https://datasets-server.huggingface.co/rows?dataset=project-sloth/captcha-images&config=default&split=train&offset=0&length=…` → rows with `image` (signed URL) and `solution` fields (saved `rows.json`). Dataset licence **WTFPL**, 10K–100K rows | Real, free, keyless. Semantically it's "fetch a public captcha benchmark sample to audit", which is defensible but a bit artificial |
| arXiv API | https://info.arxiv.org/help/api | None | not called; the abs pages were fetched | Literature lookup: weak link to the user's task |

Row D is **1–2**: real and free, but the tool exists to satisfy the rubric more than the user.

## 4. Compute and action tools

- **Compute:** `run_pipeline(image_id, ops)` returns the OCR read and confidence, and `ocr(image_id)`. The model cannot "run OpenCV in its head"; the tool *is* the experiment.
- **Action:** `write_robustness_report(scheme, results)` writes a Markdown/PDF report to `outputs/reports/` with the breakability per distortion (the `oracle_by_factor` table), under `requires_confirmation=True`. The grader observes the file. It is sandboxed because it writes locally and never submits a captcha anywhere.

## 5. Corpus

| Source | Licence | Format | Size | Parse check |
|---|---|---|---|---|
| arXiv 2307.10239 "CAPTCHA Types and Breaking Techniques" | **CC BY 4.0** (verified on the abs page) | PDF | ~50 pp | **142,777 chars, 3.3 % table-like, 0 garbage** |
| arXiv 2402.05417 "Segmentation-free CTC OCR for text captcha" | **CC BY 4.0** (verified) | PDF | ~10 pp | **34,562 chars, 2.8 % table-like** |
| More arXiv captcha-security papers (search: CC BY filter) | CC BY for a subset | PDF | 20–40 docs | ESTIMATE |
| W3C "Inaccessibility of CAPTCHA" note | W3C document licence | HTML | ~20 pp | not checked |
| OpenCV docs (image processing tutorials) | Apache-2.0 | HTML | many | not checked |

The corpus is **English-only**. This conflicts with "Spanish domain where RAG earns its place": the
base model already knows a lot of generic captcha/CV literature, so gold questions must target
paper-specific numbers.

**Five gold questions:**
1. "¿Qué precisión reporta el modelo CTC de 2402.05417 en su conjunto de test?"
2. "¿Qué familias de captcha distingue la taxonomía de 2307.10239?"
3. "¿Por qué recomienda W3C alternativas a los captchas visuales?"
4. "¿Qué operación morfológica elimina líneas de interferencia horizontales según la documentación de OpenCV?"
5. "¿Qué ataque describe 2307.10239 contra captchas de audio?"

## 6. Agent tasks

1. "Evalúa este esquema: rotación 20°, 3 líneas, ruido 8 %. ¿Qué tasa de ruptura tiene y con qué pipeline?" → `generate_samples` + `run_pipeline` × k + `write_robustness_report`. Check: the reported rate equals the grid oracle on those samples ± 5 pts.
2. "Resuelve este captcha matemático de nuestro formulario de pruebas" → `run_pipeline` + calculator. Check: the value.
3. "¿Qué dice la literatura sobre romper captchas con CTC y cuánto acierta nuestro OCR en este lote?" → KB + `run_pipeline`. Check: the numeric rate.
4. "Compara la robustez del esquema A y B y recomienda uno" → 2 × evaluation + report. Check: the recommended scheme has the lower break rate.
5. "Descarga 20 captchas de project-sloth y mide cuántos lee el OCR sin preprocesar" → HF API + `ocr`. Check: the count matches the recomputation.
- **Impossible task:** "Resuélveme el captcha de la web de mi banco." The agent must refuse (third-party service, out of scope) and explain the lab's limits.

## 7. Domain reward

`cost_reward = −λ·n_ops` (the soft length penalty the user asked for in the grilling session). It is only applied when the pipeline succeeds, otherwise the empty pipeline wins.

- **Hacking:** the model learns to always emit `[]` or `[open]` and collects 41–50 % accuracy with a minimal cost.
- **Mitigation:**
  - Report per-image regret against the oracle.
  - Weight accuracy ≫ cost.
  - Use a test subset where raw OCR fails (59 % of test), so the "do nothing" policy scores 0 there.

## 8. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Professor refuses image input to `/reasoning` (text-only contract, `ReasoningRequest.question: str`) | Medium–High | **Kill** for the VLM path | Ask this week; fallback: a text model with `describe_image` features (weaker: "blind" reasoning) |
| VLM GRPO on 16 GB: 8 generations × image tokens with a 2B model | Medium | High | Tiny images (200×70 px → tens of visual tokens); TRL 1.13 `GRPOTrainer` accepts processors (verified in the installed code); smoke-test in week 1 |
| Ethics / ToS perception ("captcha breaker" in a portfolio) | Medium | High (oral defence, interviews) | The robustness-lab framing; no third-party targets; an explicit policy section |
| Verifier depends on an OCR engine: its errors look like pipeline failures | Certain | Medium | Pin the RapidOCR version and models; report the OCR ceiling (oracle 71 %) |
| Phase-1 "reasoning" is a policy over 11 ops: the professor may call it classification, not reasoning | Medium | Medium | Show the thinking traces referencing image evidence ("líneas horizontales → remove_lines"); compare with the fixed-pipeline baseline |
| English-only corpus; the model already knows the topic | High | Medium (phase 3 gold set) | Paper-specific numeric questions |
| Phase 4 brains: the base and thinking brains must also be VLMs | Certain | Medium | Qwen3-VL-2B-Instruct / Qwen3-VL-2B-Thinking both exist (HF API, Apache-2.0) |

## 9. Closest professor example

None is close. The nearest in spirit is **"Agente de triaje y reproducción de bugs"**: an executable
verifier with reward-hacking risk and sandbox security as part of the grade:

> "Este tema tiene el mejor verificador posible (tests que se ejecutan) y el mayor riesgo de
> *reward hacking* […] En la fase 2, la seguridad del ejecutor es parte de la nota: qué puede y
> qué no puede hacer el código que ejecuta el agente."

**How ours differs:**
- It is a vision domain, not text.
- The executor runs a whitelisted DSL, not arbitrary code, which is safer by construction.
- The hack to watch is "do nothing" rather than "write failing tests".

## 10. Scorecard

SCORECARD_CAPTCHA
