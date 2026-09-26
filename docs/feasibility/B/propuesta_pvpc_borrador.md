# Propuesta de tema — borrador (Agente B)

> Borrador generado por el estudio de viabilidad B para la fase 0. Sigue la plantilla de
> `docs/00_propuesta.md`. Antes de entregarlo como `docs/propuesta.md` hay que rellenar el
> equipo y revisar las cifras marcadas como estimación.

## Equipo

- [Nombre 1] — [correo]
- [Nombre 2] — [correo]
- [Nombre 3] — [correo]

## El tema en una frase

Un agente que explica y comprueba la factura de la luz regulada (PVPC, peaje 2.0TD) de un
hogar español, calcula cuánto cuesta cada consumo según la hora y programa los
electrodomésticos en las horas más baratas.

## El usuario y su problema

Cualquier hogar acogido al PVPC (el mercado regulado, para potencias de hasta 10 kW). Hoy
recibe una factura con ocho o nueve líneas que no entiende (potencia en dos periodos,
energía, financiación del bono social, impuesto eléctrico, alquiler del contador, IVA). No
sabe si es correcta y no sabe cuándo es de verdad «valle»: por ejemplo, Viernes Santo es
festivo pero **no** es valle, porque la Circular 3/2020 solo cuenta los festivos nacionales
de fecha fija. Además, en 2026 el IVA y el impuesto eléctrico cambiaron dos veces por
decreto. Le cuesta dinero (poner la lavadora o cargar el coche en punta) y tiempo
(comparar precios hora a hora en la web de REE). Nosotros también somos usuarios: pagamos
facturas PVPC.

## Diez preguntas o tareas reales

1. «¿Qué es P1, P2 y P3 en mi factura?»
2. «¿Ahora mismo, sábado a las 12, estoy en valle?»
3. «¿El Viernes Santo cuenta como valle?»
4. «¿Cuánto me cuesta tener el horno de 2 kW una hora y media esta tarde?»
5. «¿A qué hora de mañana pongo el lavavajillas (2 horas) para que salga más barato?»
6. «Mi factura de 30 días con 4,6 kW y 250 kWh sale 64,55 €, ¿está bien?»
7. «¿Por qué en abril pagué menos IVA en la luz?»
8. «Si cargo el coche de 2 a 6 en vez de 19 a 23, ¿cuánto ahorro al mes?»
9. «Prográmame lavadora, secadora y lavavajillas esta semana en las horas baratas, sin
   solaparlos, y pásamelo al calendario.»
10. «Compara mi factura de agosto con lo que habría pagado moviendo el 30 % del consumo
    de punta a valle, y dime si me compensa bajar la potencia contratada.»

## La tarea verificable (fase 1)

**Tipo de problema.** Cálculo determinista con las reglas publicadas del peaje 2.0TD. Cuatro
familias:

- Periodo tarifario de una fecha y hora (P1/P2/P3), con fines de semana, festivos
  nacionales de fecha fija y trampas (Viernes Santo, festivos autonómicos).
- Coste de un consumo (kW × minutos) con precios horarios, incluyendo horas parciales y
  paso de medianoche.
- Importe total de una factura al céntimo: potencia (peajes + cargos + margen), energía,
  bono social, impuesto eléctrico, contador e IVA, redondeando cada línea.
- Hora de inicio de la ventana de k horas consecutivas más barata.

**Dos ejemplos con respuesta.**

- «Fecha: viernes 3 de abril de 2026 (Viernes Santo). Hora: 11:00. ¿Periodo 2.0TD?» →
  **P1** (no es festivo nacional de fecha fija).
- «Factura de 30 días; 4,6 kW en P1 y P2; 250 kWh en P1 a 0,15 €/kWh. ¿Importe total?» →
  **64,55 €** (potencia 11,65 + 0,27; energía 37,50; bono social 0,57; impuesto eléctrico
  2,56; contador 0,80; IVA 21 %).

**Cómo se verifica.** Etiqueta exacta para el periodo; número con dos decimales para los
importes (sin tolerancia más allá del céntimo); entero para la hora. El verificador rechaza
respuestas con dos valores («2,35 o 2,36») y acepta coma o punto decimal. Tenemos los casos
raros escritos como tests.

**Estrategia de `datasets.md`.** Principalmente la **1 (generador programático)**:
`sample_params` muestrea fechas, horas, potencias, consumos y precios; `solve` es la
implementación de referencia y el verificador; `render` tiene 11 plantillas en castellano.
Ya tenemos un prototipo que genera 2000 problemas únicos en segundos, con la tabla de ramas
equilibrada (festivos trampa, horas parciales, potencias distintas por periodo) y sin
intersección entre train, test y OOD por hash de parámetros. Lo complementamos con la
**2 (minería)**: el archivo público de ESIOS da el PVPC horario real y su desglose de peajes
y cargos de cada día desde 2021, que usamos como precios reales en los enunciados y como
comprobación de nuestras constantes (coinciden al céntimo con lo publicado el 25/09/2026).
Cantidades previstas: 500 problemas para SFT, 1500 para GRPO, 200 de test (50 revisados a
mano) y 100 fuera de distribución (año 2027, facturas de 60 días, ventanas de 3-4 horas en
listas de 24 precios). Grupo de control: 30 % de GSM8K.

## Las herramientas (fase 2)

- **Consulta fuera del modelo:** API de datos de Red Eléctrica (REData), sin clave:
  <https://www.ree.es/es/apidatos> (precios PVPC horarios), y el archivo público de ESIOS
  (<https://api.esios.ree.es/>) para el desglose. Días festivos: <https://date.nager.at>.
- **Cálculo:** calculadora de factura con la tabla de impuestos por fechas (en 2026 el IVA
  pasó al 10 % y el impuesto eléctrico al 0,5 % entre el 22 de marzo y el 31 de mayo) y
  prorrateo cuando cambia un precio dentro del periodo; y búsqueda de la ventana más barata.
  El modelo no debe hacerlo de cabeza: son ocho líneas redondeadas al céntimo y reglas que
  dependen de la fecha.
- **Acción con efecto observable:** genera un calendario `.ics` y un CSV con los
  electrodomésticos programados en `data/schedules/`, servidos por la API. Se comprueba
  descargando el fichero y verificando que cada evento empieza en la hora que devuelve la
  calculadora con los precios reales de ese día. No toca ningún enchufe ni cuenta real.

## El corpus (fase 3)

- **Origen y tamaño:** normativa y guías oficiales, unos 25-40 documentos y ~500 páginas:
  Circular 3/2020 de la CNMC (28 pp.), resoluciones de peajes y órdenes de cargos de 2024 a
  2026, Real Decreto 216/2014 del PVPC (45 pp.), RD 446/2023, RD-ley 7/2026 y 18/2026, Ley
  38/1992 del impuesto eléctrico, modelo de factura (BOE-A-2021-7120), preguntas frecuentes
  y guías de la CNMC (35 + 28 pp.), guías del consumidor y de ahorro del IDAE.
- **Formato:** PDF con capa de texto y HTML del BOE. Las fórmulas de la Circular y del RD
  216/2014 son imágenes: las escribiremos a mano como fragmentos documentados.
- **Licencia:** textos del BOE reutilizables según su aviso legal (Ley 37/2007); los textos
  legales no están sujetos a propiedad intelectual (art. 13 LPI). CNMC e IDAE, reutilización
  con atribución (pendiente de confirmar el aviso legal de la CNMC).
- **Dos preguntas que solo se responden leyendo el corpus:**
  - «¿Antes de qué hora se publican los precios PVPC del día siguiente?» → antes de las
    20:15 (RD 216/2014).
  - «¿Cuánto es el peaje de potencia del periodo 1 del 2.0TD en 2026?» → 23,324952
    €/kW·año (Resolución de la CNMC de 18/12/2025, anexo I).

## Qué puede salir mal

- **Las reglas cambian** (peajes cada enero, impuestos según el IPC en 2026). Mitigación:
  constantes indexadas por fecha y preguntas del conjunto dorado fechadas; el cambio se
  convierte en una tarea más del agente.
- **Una familia demasiado fácil** para el modelo base (la ventana más barata sobre pocas
  horas). Mitigación: hemos medido el modelo base antes de proponer (ver cifras en el
  informe de viabilidad) y movemos esa familia a listas largas si supera el 50 %.
- **La API de REE sin límites documentados o caída durante la corrección.** Mitigación:
  caché diaria, archivo de ESIOS como respaldo y ficheros de prueba congelados.

## Por qué este tema

Porque todos pagamos una factura PVPC que no entendemos, y porque es un dominio con reglas
publicadas, datos reales abiertos cada hora y trampas de verdad (festivos, cambios de
impuestos, cambio de hora) que el modelo no conoce: exactamente lo que la práctica pide.
