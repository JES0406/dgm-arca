## Plan de trabajo por fase (para el ganador)

Semanas contadas desde la aprobación de la propuesta. El calendario oficial de entregas no está
en el repositorio (ASSUMPTION: cuatro fases de ~3 semanas cada una hasta enero).

| Fase | Semanas | Entregables | Riesgo principal y cómo se ataja |
|---|---|---|---|
| 0 | esta semana | `docs/propuesta.md` (borrador abajo), envío al profesor | Aprobación: la propuesta incluye ya dos ejemplos resueltos y el generador ejecutable |
| 1 | 1–3 | `verifier.py` + tests de bordes; generador → 800 train / 200 test (50 auditados a mano) / 100 OOD; `distill.py` con Qwen3-4B (4 trazas/problema, tasa de aceptación); SFT LoRA 0.6B; GRPO con 3 recompensas; `grpo_step.py`; `evaluate.py` con curvas | Longitud de razonamiento > 384 tokens: medir la distribución en la destilación y subir `max_completion_length` o quitar la hoja de reglas tras SFT |
| 2 | 4–5 | 3 herramientas con Pydantic; bucle de 5 pasos con multi-step y paralelo; banco de 30 casos (≥ 6 sin herramienta); con/sin herramientas | Límites de la API: caché local y reintentos con backoff |
| 3 | 6–8 | Corpus descargado por script (licencias en `rag/corpus/README.md`); chunking recursivo vs semántico; denso + BM25 + híbrido con barrido de λ; 50 preguntas doradas; citas con comprobación | Tablas del BOE/NVD/especificación: usar HTML y trocear por fila/artículo |
| 4 | 9–11 | ReAct propio; 3 cerebros; memoria con resumen; 20 tareas con comprobación automática; JSON vs `CodeAgent`; UI de trazas | Tareas del profesor no vistas: incluir en el banco las familias de casos límite |
| Cierre | 12 | `EXPERIMENTS.md` fechado, README de portfolio, Docker, limpieza | Borrar este directorio de trabajo `docs/feasibility/` (la rúbrica penaliza andamiaje) |

## Reparto entre las tres personas del equipo

Cada fase tiene un responsable, pero todos revisan todo: en la defensa preguntan a cualquiera
sobre cualquier parte.

| Persona | Responsable de | Apoya en | Por qué este reparto |
|---|---|---|---|
| P1 | Fase 1 completa (generador, verificador, destilación, SFT, GRPO, `grpo_step.py`) | Fase 4 (cerebro `rlm`) | La fase 1 es la más larga y la que más se aprieta en la propuesta; conviene una persona dedicada desde el día 1 |
| P2 | Fase 2 (herramientas, bucle, banco de 30) y Fase 4 (ReAct, memoria, banco de 20, UI) | Fase 1 (tests del verificador) | Las fases 2 y 4 comparten parser, registro y herramientas |
| P3 | Fase 3 (corpus, chunking, retrievers, conjunto dorado, citas) y documentación (`EXPERIMENTS.md`, README) | Fase 4 (`search_knowledge_base`) | La fase 3 es mucho trabajo manual (50 preguntas doradas); la documentación continua evita el atracón final |

Reunión semanal de 30 minutos: cada uno explica a los otros dos una pieza del otro (entrena la
defensa oral).
