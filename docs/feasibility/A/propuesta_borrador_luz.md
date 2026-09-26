# Propuesta de tema — ARCA

## Equipo

- [Nombre 1] — [correo]
- [Nombre 2] — [correo]
- [Nombre 3] — [correo]

## El tema en una frase

Un agente que recalcula y explica la factura de la luz de un hogar español (tarifa 2.0TD),
consulta los precios horarios reales de Red Eléctrica y programa en el calendario cuándo usar los
electrodomésticos para pagar menos.

## El usuario y su problema

Cualquier hogar con suministro de hasta 15 kW: más de veinte millones de contratos en España,
empezando por nosotros tres. Hoy la factura llega como un PDF con siete conceptos (potencia,
energía por periodos, bono social, financiación del bono, impuesto eléctrico, alquiler del
contador e IVA), y casi nadie sabe si está bien cobrada. Tampoco sabe a qué hora le conviene
poner la lavadora: el PVPC cambia cada hora. Comprobar una factura a mano lleva media hora con la
hoja de cálculo y el BOE abiertos. Equivocarse cuesta dinero: potencia mal dimensionada, un bono
social mal aplicado, una tarifa peor que el PVPC.

## Diez preguntas o tareas reales

1. ¿Qué es el término de potencia y por qué lo pago aunque no gaste luz?
2. ¿A qué hora de mañana es más barata la luz?
3. ¿Cuánto me cuesta poner el horno una hora a las 20:00 y cuánto a las 15:00?
4. Mi factura dice 61,37 € por 31 días, con 4,6 kW y 120, 95 y 210 kWh en punta, llano y valle: ¿está bien cobrada?
5. Vivo en Las Palmas: ¿por qué mi factura no lleva IVA?
6. Soy consumidor vulnerable con bono social: ¿por qué el descuento no se aplica a todo lo que consumo?
7. ¿Me compensa bajar la potencia de 5,75 kW a 4,6 kW?
8. Busca las dos horas más baratas de mañana para la lavadora y ponlo en mi calendario.
9. Con mis consumos del último mes, ¿habría pagado menos con el PVPC que con mi precio fijo?
10. Mi comercializadora cambió los precios a mitad del periodo de facturación: recalcula la factura prorrateando y dime si me han cobrado bien.

## La tarea verificable (fase 1)

**Tipo de problema.** Cálculo del importe total de una factura 2.0TD al céntimo. Datos de entrada:
días del periodo, potencia contratada en P1 y P2, precios de potencia y de energía por periodo,
kWh consumidos en P1, P2 y P3, bono social (sin bono, vulnerable o vulnerable severo, con
categoría de límite) y territorio (península y Baleares con IVA, Canarias con IGIC, Ceuta y Melilla
con IPSI). Antes de calcular hay que decidir tres cosas: si el consumo supera el límite
bonificable del bono social, qué impuesto indirecto aplica y cómo se prorratea un cambio de precio.

**Dos ejemplos** (salida real del generador):

- *Sevilla, 32 días, 3,3 kW en P1 y P2 a 0,073486 y 0,039512 €/kW·día; 159, 178 y 76 kWh a 0,260404,
  0,165785 y 0,087579 €/kWh; bono social vulnerable severo, categoría B.* → **79,90 €**
- *Suministro en Las Palmas de Gran Canaria, sin bono social* (mismo formato; se aplica IGIC 3 % en
  vez de IVA 21 %) → el importe que da `solve` (véase `luz/data/test.jsonl`).

**Cómo se verifica.** Comparación numérica con tolerancia de 0,01 €. Usamos un analizador propio
que acepta la coma decimal ("79,90", "1.234,56"), porque el `normalize_number` del repositorio
convierte "79,90" en 7990. Los tests del verificador cubren la coma decimal, los separadores de
miles, el total frente a la base sin impuestos y el redondeo concepto a concepto frente al
redondeo del total.

**Estrategia de datos: generador programático (estrategia 1).** `sample_params` muestrea días
(27–34), potencias estándar (2,3 a 6,9 kW), precios, consumos (con un modo "hogar pequeño" para
equilibrar la rama del límite del bono social), bono y territorio. `solve` implementa las reglas
con las cifras de la ley: impuesto eléctrico del 5,11269632 % (Ley 38/1992, art. 99), alquiler del
contador de 0,81 €/mes (guía de la CNMC) y 2.0TD hasta 15 kW (Circular 3/2020). Hay cuatro
plantillas con el orden de los datos variable. El prototipo ya funciona: 0 fugas de la respuesta
en el enunciado y 0 solapamientos entre particiones por hash de parámetros.

| Conjunto | Problemas | Notas |
|---|---|---|
| train | 800 (SFT) + 1.500 (GRPO) | generados, sin revisión manual |
| test | 200, 50 auditados a mano | incluye casos límite forzados: el mínimo del impuesto eléctrico, el límite exacto del bono, periodos de 27 y 34 días |
| test OOD | 100 | cambio de precios a mitad de periodo, ausente del entrenamiento |
| control | 30 % de GSM8K | para comprobar que no se degrada lo general |

## Las herramientas (fase 2)

- **Consulta externa:** API REData de Red Eléctrica (https://www.ree.es/es/apidatos), sin clave.
  Probada el 26-09-2026: devuelve los 24 precios PVPC del día en €/MWh.
- **Cálculo:** `calcular_factura` (el mismo motor que `solve`) y `mejor_franja`, que busca la ventana
  más barata de N horas sobre los precios del día. El modelo no debe hacer de cabeza siete
  redondeos ni sumar 24 precios.
- **Acción con efecto observable:** `programar_electrodomestico` escribe un evento `.ics` en
  `outputs/calendar/` y pide confirmación antes. Se comprueba leyendo el fichero y comparando su
  DTSTART con la franja óptima recalculada.

## El corpus (fase 3)

- **Fuentes:** BOE (Resolución de la CNMC de 18-12-2025 con los peajes de 2026, Orden TED/1524/2025
  de cargos, Circular 3/2020, RD 216/2014 del PVPC, RD 897/2017 del bono social y Ley 38/1992),
  guías de la CNMC para consumidores y guías del IDAE. En total, entre 15 y 25 documentos y unas
  400–600 páginas.
- **Formato:** PDF y HTML del BOE. Las tablas de peajes se trocearán por fila a partir del HTML:
  en el PDF un 16,9 % de las líneas son tablas aplanadas.
- **Licencia:** el BOE permite reutilizar sus contenidos citando la fuente. Las guías de la CNMC
  y del IDAE son contenido público; su aviso legal está por confirmar.
- **Dos preguntas que solo responde el corpus:**
  - "¿Cuánto vale en 2026 el término de potencia del peaje de transporte 2.0TD en P1?" → 3,233054 €/kW·año.
  - "¿Cuál es el mínimo del impuesto eléctrico para usos industriales?" → 0,5 €/MWh.

## Qué puede salir mal

1. **El razonamiento no cabe en 384 tokens.** Con siete conceptos y tres decisiones, las trazas
   pueden ser largas. Mediremos la distribución de longitudes en la destilación. Si hace falta,
   subiremos `max_completion_length` a 768 o quitaremos la hoja de reglas del enunciado tras el SFT
   y lo compararemos.
2. **Los valores regulados cambian** (porcentajes del bono social, rebajas temporales de
   impuestos). La fase 1 se evalúa contra una hoja de reglas con fecha que va en el enunciado. El
   corpus guarda las normas fechadas y el agente cita qué versión aplica.
3. **La API de REE falla el día de la corrección.** La herramienta guarda caché por fecha y usa
   ESIOS como respaldo.

## Por qué este tema

Porque todos pagamos una factura de la luz que no entendemos del todo, y un agente que la
comprueba y ahorra dinero es algo que usaríamos cada mes. También porque el dominio es español y
reciente: justo donde el modelo base sabe poco y el RAG se nota.
