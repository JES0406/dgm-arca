# PVPC 2.0TD bill & load shifting — research evidence (subagent report, 2026-09-26)

Collected by a research subagent of Agent B. Samples (10 PDFs + extractions, REData/ESIOS
JSON) stored under the job's tmp dir, not committed.

## 1. Bill rules (peninsula, 2026)
**Periods** — Circular 3/2020 art. 7.3 (consolidated p. 8)
<https://www.boe.es/buscar/pdf/2020/BOE-A-2020-1066-consolidado.pdf>:
Mon–Fri working days P1 10–14 & 18–22, P2 8–10, 14–18, 22–24, P3 0–8. Saturdays,
Sundays, 6 January and national holidays all P3, "con exclusión tanto de los festivos
sustituibles como de los que no tienen fecha fija". Power: P1 = punta+llano, P2 = valle.
Ceuta/Melilla shift one hour.

**Peajes 2026**: CNMC Resolution 18/12/2025 (BOE-A-2025-26348,
<https://www.cnmc.es/sites/default/files/6331866.pdf> Anexo I pp. 10–11).
**Cargos 2026**: Orden TED/1524/2025 (BOE-A-2025-26705).

| Term | P1 | P2 | P3 |
|---|---|---|---|
| Power peaje €/kW·yr | 23.324952 | 0.443770 | – |
| Power cargo €/kW·yr | 4.379461 | 0.281653 | – |
| Energy peaje €/kWh | 0.033261 | 0.016409 | 0.000077 |
| Energy cargo €/kWh | 0.064292 | 0.012858 | 0.003215 |
| **Energy peaje+cargo** | **0.097553** | **0.029267** | **0.003292** |

Cross-check: ESIOS archive 70 (2026-09-25) TEUPCB = 97.55 / 29.27 / 3.29 €/MWh — exact match.

- Marketing margin 3.113 €/kW·yr (Orden ETU/1948/2016; ASSUMPTION still current, P1 kW only).
- Bono social financing 6.979247 €/CUPS·yr (TED/1524/2025 apartado Décimo d; ASSUMPTION
  passed through pro-rata).
- Power pro-rated by days (Circular 3/2020 art. 9.2; /365 ASSUMPTION).
- Energy: RD 216/2014 (<https://www.boe.es/buscar/pdf/2014/BOE-A-2014-3376-consolidado.pdf>);
  since RD 446/2023 futures weight 0.55 in 2026. The published PVPC hourly price **already
  includes** peajes+cargos: energy € = Σ kWh_h × PVPC_h / 1000.
- PVPC only for ≤10 kW (CNMC FAQ p. 8, <https://www.cnmc.es/file/304523/download>).
- **IEE** 5.11269632 % of (power+energy), minimum 1 €/MWh household (0.5 professional).
  2026: RD-ley 7/2026 cut IEE to 0.5 % and IVA to 10 % from 22 March; reverted 1 June
  (AEAT notes 25/03/2026 and 19/05/2026). RD-ley 18/2026 (BOE-A-2026-14112) allows
  reactivation Aug/Sep 2026 on a CPI condition (ASSUMPTION: not triggered; verify with AEAT).
- **IVA** 21 % on everything incl. IEE and meter (ASSUMPTION in force Sep 2026).
- **Meter rental** 0.81 €/month single-phase smart meter (Orden ITC/3860/2007; ASSUMPTION).

Worked example: 4.6 kW, 30 days, 250 kWh at 0.15 €/kWh → power P1 11.65 + P2 0.27 +
energy 37.50 + bono 0.57 = 50.00; IEE 2.56; meter 0.80; IVA 21 % → **64.56 €**.

## 2. APIs
- **REData** (no key, CORS *, Imperva CDN, no documented limit):
  `https://apidatos.ree.es/es/datos/mercados/precios-mercados-tiempo-real?start_date=2026-09-25T00:00&end_date=2026-09-25T23:59&time_trunc=hour`
  → `included[type=PVPC].attributes.values` = 24 hourly values (`{"value":195,"datetime":"2026-09-25T00:00:00.000+02:00"}`);
  spot series now 96 quarter-hour values.
- **ESIOS** indicators API: 403 without token (token by email, <https://www.esios.ree.es/es/token>,
  header `x-api-key`). Public archive tokenless:
  `https://api.esios.ree.es/archives/70/download_json?locale=es&date=2026-09-25` (PCB, TEUPCB, PMH…).

## 3. Corpus (verified with pdftotext)
| Document | Pages | Extraction |
|---|---|---|
| Circular 3/2020 consolidated | 28 | clean; formulas are images |
| CNMC peajes 2026 | 17 | tables clean with `-layout` |
| RD 216/2014 consolidated | 45 | clean; formulas partly lost |
| Orden TED/1524/2025 | ~20 | HTML tables flatten but parse |
| CNMC "Nueva factura" FAQ | 35 | clean |
| CNMC consumer guide 2022 | 28 | clean |
| Bill model resolution 2021 (BOE-A-2021-7120) | 18 | clean |
| Consumo Responde bill model | 30 | clean |
| IDAE Guía Práctica de la Energía (2011) | 93 | clean but **outdated** (pre-2.0TD) |
| Ley 38/1992 (IEE) | HTML | — |
Expandable to 25–40 docs (2024/2025 peajes & cargos, RD 148/2021, RD 446/2023,
RD-ley 7/2026, 18/2026, holiday calendar resolution, CNMC/OCU guides).
Licence: BOE reuse under Ley 37/2007 (<https://www.boe.es/informacion/aviso_legal/index.php>);
legal texts not copyrightable (art. 13 LPI); CNMC/IDAE reuse ASSUMPTION (CNMC aviso legal 404).

## 4. Gold questions
1. Is 6 January all P3; are substitutable regional holidays? → yes; excluded. Circular 3/2020 art. 7.3 p. 8.
2. Deadline to publish next-day PVPC → "antes de las 20 horas 15 minutos del día anterior". RD 216/2014 p. 20.
3. 2026 P1 power peaje 2.0TD → 23.324952 €/kW·yr. CNMC Res. 18/12/2025 Anexo I p. 10.
4. 2026 P1 energy cargo → 0.064292 €/kWh. Orden TED/1524/2025 Primero b).
5. >10 kW in valle → no PVPC. CNMC FAQ p. 8.

## 5. Gotchas
DST days have 23/25 PVPC values (key on UTC offset); next-day PVPC after ~20:15; negative
spot prices exist; only national fixed-date holidays are P3; mid-period price or tax change
→ pro-rate by days; 2026 tax regime is date-indexed.
