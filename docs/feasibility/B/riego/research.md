# FAO-56 irrigation scheduler — research evidence (subagent report, 2026-09-26)

Collected by a research subagent of Agent B. Samples (FAO-56 text, MAPA/IVIA/Cajamar/IFAPA
PDFs, SIAR manual, Open-Meteo JSON) stored under the job's tmp dir, not committed.

## 1. Formulas
FAO-56 (Allen et al. 1998), HTML <https://www.fao.org/4/x0490e/x0490e00.htm>; printed page
= PDF page − 26 in the mirror used.
- ETc = Kc·ETo (p. 9, ch. 6). Kc curve Eq. 66 (p. 132): constant in initial and mid,
  linear in development and late.
- Table 11 (stage lengths, pp. 104–108), Table 12 (Kc, pp. 110–113):

| Crop | Lini/Ldev/Lmid/Llate | Kc ini/mid/end | T11/T12 p. |
|---|---|---|---|
| Tomato (Apr/May, Medit.) | 30/40/45/30 | 0.6 / 1.15 / 0.70–0.90 | 104/110 |
| Lettuce (Apr, Medit.) | 20/30/15/10 | 0.7 / 1.00 / 0.95 | 104/110 |
| Sweet pepper | 25-30/35/40/20 | 0.6 / 1.05 / 0.90 | 104/110 |
| Potato (Apr, Europe) | 30/35/50/30 | 0.5 / 1.15 / 0.75 | 105/110 |
| Maize grain (Spain) | 30/40/50/30 | 0.3 / 1.20 / 0.60–0.35 | 106/111 |
| Wine grape | 30/60/40/80 | 0.30 / 0.70 / 0.45 | 107/112 |
| Citrus 70 % canopy | 60/90/120/95 | 0.70 / 0.65 / 0.70 | 107/113 |
| Olive 40–60 % canopy | 30/90/60/90 | 0.65 / 0.70 / 0.70 | 108/113 |

- TAW = 1000(θFC − θWP)Zr (Eq. 82), RAW = p·TAW (Eq. 83), p. 162; Table 19 soils p. 144;
  Table 22 Zr/p pp. 163–165 (tomato 0.7–1.5 m / 0.40; lettuce 0.3–0.5 / 0.30; pepper
  0.5–1.0 / 0.30; potato 0.4–0.6 / 0.35; maize 1.0–1.7 / 0.55; grape 1.0–2.0 / 0.45;
  citrus 1.2–1.5 / 0.50; olive 1.2–1.7 / 0.65).
- Effective rainfall (monthly): MAPA sheet
  <https://www.mapa.gob.es/es/desarrollo-rural/temas/gestion-sostenible-regadios/precipitacionefectiva05_tcm30-82980.pdf>
  lists SCS formula, fixed 0.7–0.9·Pt, "fiable" 0.6Pt − 10 (Pt < 70) / 0.8Pt − 24 (Pt > 70);
  FAO TM3 uses 75 mm / −25 (<https://www.fao.org/4/s2022e/s2022e08.htm>); InfoRiego uses a
  torrentiality coefficient.
- Application efficiency: ITACyL/InfoRiego goteo 0.9, aspersión 0.8, cañón 0.7, pivote
  0.85, gravedad 0.5; IVIA Ficha 2 drip 0.90. (Sprinkler 0.75 not found — use 0.8.)
- Drip run time: gross = (ETc − Pe)/Ea (mm = L/m²); t = gross × area / (n × q). Cajamar
  example: 2.3 L/m²·day ÷ (3 L/h × 2 emitters/m²) = 23 min/day (p. 4).
- **Oracle:** FAO-56 Example 37 p. 168 (tomato, Zr 0.8, p 0.40, θFC 0.32, θWP 0.12 → TAW
  160, RAW 64 mm; ETo 5, Kc 1.2, Dr0 55 mm; daily Ks/ETc_adj/Dr table).

## 2. APIs
- **Open-Meteo** (no key):
  `https://api.open-meteo.com/v1/forecast?latitude=37.98&longitude=-1.13&daily=et0_fao_evapotranspiration,precipitation_sum,temperature_2m_max,temperature_2m_min&timezone=Europe/Madrid&forecast_days=7`
  → ETo [4.04, 3.25, 2.86, 2.80, 3.74, 3.51, 2.33] mm, rain [0,…,0.30]. Terms: non-commercial,
  <10,000/day, 5,000/h, 600/min, CC-BY 4.0.
- **SIAR (MAPA)**: token needs SiAR account + REGEUS registration with NIF/NIE; 30 req/min,
  1,000/day; returns EtPMon, PePMon. Barrier → optional.
- **AEMET OpenData**: free key by email + reCAPTCHA; no ETo.

## 3. Corpus (~25 docs, >30 with more IVIA/SIAM)
Licences: **FAO-56 1998 "All rights reserved"** (RAG over a local copy ok for coursework,
not redistributable); FAO-56 Rev.1 2025 licence unverified (ASSUMPTION CC BY-NC-SA 3.0 IGO);
InfoRiego "Todos los derechos reservados"; MAPA/IVIA ASSUMPTION Ley 37/2007; Cajamar private.
Downloaded: MAPA hoja 17/1990 (24 pp, **OCR errors**), MAPA Kc sheet, MAPA Pe, Calera et al.
2016 (19 pp), IFAPA strawberry balance (19 pp), NEIKER (12 pp), IVIA Fichas 2/8/9 (Ficha 2
garbled layers; Ficha 8 table is an image), Cajamar Almería 2005 (9 pp, table-driven), SIAR
manual (17 pp). FAO-56 PDF: clean text but **footnote superscripts fuse with table numbers**
("1.152" = 1.15 + note 2) → hand-curate Tables 11/12/19/22 as JSON.

## 4. Gold questions
1. FAO-56 tomato p and Zr → 0.40; 0.7–1.5 m (Table 22 p. 163).
2. Example 37 TAW, RAW → 160 mm, 64 mm (p. 168).
3. MAPA HD 17/1990 minimum wetted share, horticulture → 70 % (30–40 % trees) (p. 9).
4. Cajamar Almería minutes/day at 2.3 L/m²·day, 2 emitters/m² × 3 L/h → 23 min (p. 4).
5. Calera et al. 2016 vineyard NDVI 0.4, ETo 6.5, 70 % deficit → Kcb 0.48, 3.12, 2.2 mm/day (p. 12).

## 5. Gotchas
mm = L/m²; effective-rain formulas are monthly; thresholds differ (MAPA 70/−24 vs FAO
75/−25); MAPA Kc sheet ET0 0.80 mm/day in July is implausible; Table 11 has several rows
per crop; tree crops need monthly Kc; FAO Kc assumes RHmin 45 %, u2 2 m/s (climate
adjustment Eq. 62); partial-cover drip needs a wetted-fraction convention.
