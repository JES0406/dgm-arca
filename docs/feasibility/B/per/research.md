# PER navigation tutor — research evidence (subagent report, 2026-09-26)

Collected by a research subagent of Agent B; conclusions re-checked by Agent B where marked.
Samples (not committed, not redistributable in bulk) were stored under the job's tmp dir:
`rd875_2014_consolidado.pdf`, `ripa_consolidado.pdf`, `iala_draft.pdf`,
`dgmm_enunciados_abril_2026.pdf`, `dgmm_plantillas_abril_2026.pdf`, Gencat PEE papers.

## 1. Exam rules and syllabus
- **RD 875/2014** consolidated: <https://www.boe.es/buscar/act.php?id=BOE-A-2014-10344>
  (116 pp). Annex II §3 = PER exam (pp. 34–43). Art. 8 c) PER scope: motorboats ≤15 m,
  ≤12 nm from coast, plus inter-island Balearics/Canaries (p. 9).
- **Format (Annex II p. 43):** 45 MCQ, 4 options, 1 h 30 min; pass ≥32 correct with ≤5
  errors RIPA, ≤2 Balizamiento, ≤2 Carta. Per unit: UT1 4, UT2 2, UT3 4, UT4 2, UT5 5,
  UT6 10, UT7 2, UT8 3, UT9 4, UT10 5, UT11 4.
- **Scope:** UT11 chart exercises are "en ausencia de viento y corriente" (pp. 42–43).
  Current triangle = Patrón de Yate (UT4.5, pp. 45–46). Rule of twelfths only in Anexo III
  practical training (p. 56).
- **Official past exams (DGMM):**
  <https://www.transportes.gob.es/marina-mercante/titulaciones/titulaciones-de-recreo/examenes/examenes-para-la-obtencion-de-titulaciones-de-recreo>
  ≈22 question-paper PDFs (2016 → June 2026) and ≈38 answer-key PDFs incl. corrections.
  Example: <https://cdn.transportes.gob.es/portal-web-transportes/maritimo/examenes-teoricos/enunciados_examenes_abril_2026.pdf>
  (147 pp, text layer) + `plantillas_respuestas_abril_2026.pdf`. April 2026: 4 PER
  variants; key for Test 01 aligns (Q38 = C "suma algebraica de dm y desvío", Q41 = D "Veril").
- **Gencat:** bilingual PEE papers + solution PDFs,
  <http://agricultura.gencat.cat/ca/ambits/nautica-busseig/Questionaris-solucions-examens-nautica-esbarjo-00002>;
  solution sheets are answer grids, poor text extraction.
- **Minable size:** ≈22 sittings × ≈4 PER tests × 45 ≈ 3,500–4,000 MCQ with gold letters,
  ≈350 Carta questions. ESTIMATE extrapolated from April 2026; older PDFs may be scanned.

## 2. Formulas
- `Ct = dm + Δ`, `Rv = Ra + Ct`, `Rm = Ra + Δ`; E = +, W = −.
  Sources: <https://es.wikipedia.org/wiki/Correcci%C3%B3n_total>,
  <https://es.wikipedia.org/wiki/Desv%C3%ADo_de_aguja>, Greenwich Náutica
  <https://campus.greenwichnautica.es/mod/book/view.php?id=3358&chapterid=3617>.
  Exams write "desvío 2°(-)", "declinación 2°(E)" (April 2026 Q42).
- Declination update: `dm_now = dm_chart + annual × (year − chart_year)`; worked example
  6°40′W (1992), 8′E/yr, 23 yr → 3°36′W. Syllabus 10.5 (RD 875 p. 42).
- `D = V·t`; dead reckoning Δl = D cos Rv, Δλ = D sin Rv / cos lm (ASSUMPTION: not checked
  against a Spanish source).
- Tide depth = sounding + tide height (Anuario) − pressure correction (ASSUMPTION ≈1 cm/hPa).

## 3. APIs (curl 2026-09-26)
- **Open-Meteo Marine** (no key): `https://marine-api.open-meteo.com/v1/marine?latitude=39.45&longitude=-0.25&hourly=wave_height,...`
  → wave_height 0.20 m, direction 74°, period 6.15 s. Tide only modelled `sea_level_height_msl`.
- **Open-Meteo Forecast** (no key): first call `{"reason":"The service is overloaded","error":true}`,
  retry OK (wind 5.6 kn from 102°, 1019.2 hPa) → needs retry/backoff + fixtures.
- **NOAA declination**: key required ("key parameter is missing"); free registration.
  Returned WMM-2025 declination +1.516°, annual +0.126°/yr with a demo key.
- **Puertos del Estado / Portus**: no documented REST API (probes 404/405). Avoid.

## 4. Corpus (≈30 docs realistic)
| Doc | URL | Pages | Extraction |
|---|---|---|---|
| RD 875/2014 | BOE-A-2014-10344 | 116 | clean; 2-column syllabus tables interleave |
| RIPA/COLREG | <https://www.boe.es/buscar/act.php?id=BOE-A-1977-15605> | 28 | very clean |
| RIPA amendments | BOE-A-2010-4648, BOE-A-2003-2716, BOE-A-1994-22801 | short | — |
| IALA R1001 (ES draft, Puertos del Estado) | puertos.es (2024-02 draft) | 34 | tables legible with `-layout`, 66 images lost; final Ed. 2.0 URL is 404 |
| DGMM papers + keys | transportes.gob.es | ~60 PDFs | eval set, not RAG corpus |
| AEMET Guía Meteorología Marítima, NT-4 | aemet.es | — | not downloaded |
Licence: BOE/ministry reuse (Ley 37/2007, ASSUMPTION); IALA copyright (restricted, ASSUMPTION).

## 5. Gold questions
1. Masthead light range for a vessel <12 m → 2 millas (side lights 1). RIPA Regla 22 c).
2. Overtaking angle → more than 22,5° abaft the beam. RIPA Regla 13.
3. PER limits → motor ≤15 m, 12 nm, inter-island Baleares/Canarias. RD 875 art. 8 c) p. 9.
4. Carta errors allowed / correct to pass → 2; 32/45. RD 875 Annex II §3 p. 43.
5. South cardinal light → VQ(6)+LFl 10 s or Q(6)+LFl 15 s, white. IALA R1001 ES, Cuadro 6 p. 14.

## 6. Text-solvability
UT1–UT10 (41/45) text-solvable. Of 4 Carta questions, 3 need landmark coordinates +
plotting (gazetteer of ≈40 Strait landmarks + Mercator code would make them solvable), 1
needs Anuario tide values not in the question.
