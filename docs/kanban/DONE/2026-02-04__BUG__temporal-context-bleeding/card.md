---
status: DONE
---
# BUG: Context Bleeding Temporal - Año Incorrecto en Respuestas

**Prioridad:** P1 - High
**Fecha:** 2026-02-04
**Reportado por:** cb6c6879-e598 (11 reports)
**Status:** DOING

---

## Resumen

El sistema muestra datos del año incorrecto cuando el usuario especifica un periodo. El problema principal es "context bleeding" donde el año de un prompt anterior se aplica al prompt actual, o el sistema confunde 2024 con 2025.

**Impacto:** 11 feedback negativos - usuarios no pueden confiar en datos temporales

---

## Casos Reportados

### Conversación 765a97e9: Cartera Comercial INVEX

**Secuencia de queries:**
1. `muestrame la cartera comercial de invex` → "no me dio lo que le pedí"
2. `muestrame la cartera comercial de invex en 2024` → "me dice que no tiene datos y me mostro datos de 2025"
3. `muestrame la cartera comercial de invex en 2025` → "texto da info de 2025, gráfica da datos de 2024"
4. `cuanto creció la cartera comercial de invex en 2025 ?` → "me mostró el de 2024 en la gráfica"

**Feedback detallado:**
- "no me mostro la cartera comercial de 2024, me dice que no tiene datos y me mostro la grafica y datos de 2025"
- "en el texto del mensaje me da la información de 2025, sin embargo, la grafica y los datos me los da de 2024 cuando antes me dijo que no tenia la información de ese año"
- "para la grafica esta tomando en cuenta el prompt anterior y me despliega esos datos"

### Conversación adb56434: ICAP Comparativo

**Secuencia de queries:**
1. `compara el ICAP de BBVA, Banamex y Santander en 2024` → "no me la proporciono, dice que no hay datos anteriores a 2025"
2. `compara el ICAP de BBVA, Banamex y Santander` → "tomó el prompt anterior de 2024 y me dio esos datos"
3. `muéstrame una comparación del ICAP de mayo de 2024 a mayo de 2025 ?` → "no fue capaz de detectar el periodo solicitado"

**Feedback detallado:**
- "esperaba la grafica y tabla comparativa del ICAP de los bancos en 2024 y no me la proporciono - menciona que no se tienen datos anteriores a 2025"
- "esperaba que al no poner año me diera el ICAP mas reciente pero tomó el prompt anterior de 2024"
- "en la respuesta anterior menciono que no había datos para 2024 pero si los hay"

### Conversación 9e267c84: ICAP por Año

**Secuencia de queries:**
1. `compara el ICAP total de banamex, bbva y santander en 2024` → "no me mostró el ICAP del año solicitado"
2. `compara el ICAP total de banamex, bbva y santander en 2025` → "me mostro el del 2024, tomando en cuenta el prompt anterior"

**Feedback detallado:**
- "no me mostró el ICAP del año solicitado"
- "le pedí el ICAP de 2025 y me mostro el del 2024, en el prompt anterior no me lo mostro y ahora al solicitar el 2025 me muestra el del 2024"

### Conversación 304a4616: Filtro de Periodos

**Query:** `dime en que periodos el ICAP total de Santander estuvo por encima del 15% ?`
**Feedback:** "solo me mostro el ultimo año de ICAP Santander, no todos los periodos en los que estuvo por encima del 15%"

### Conversación b96f4170: Promedio Anual

**Query:** `cual fue el IMOR promedio de Santander en 2025 ?`
**Feedback:** "esperaba el resultado promedio de todo 2025 (a partir de enero) y solo me lo dio a partir de mayo"

---

## Análisis Técnico

### Patrones Identificados

1. **Context Bleeding:** El año del prompt N se aplica al prompt N+1
   - Query 1: "en 2024" → "no hay datos"
   - Query 2: "en 2025" → muestra datos de 2024 (usó contexto anterior)

2. **Desync Texto/Gráfica:** El texto describe un año, la gráfica muestra otro
   - Texto: "Aquí están los datos de 2025..."
   - Chart: Muestra evolución de 2024

3. **Filtro de Fecha Ignorado:** WHERE fecha = '2024' no se aplica al SQL

4. **Datos Disponibles Negados:** "No tengo datos de 2024" pero los datos SÍ existen

### Causa Raíz Probable

1. **Multi-turn context** pasa el año anterior al nuevo query
2. **SQL generation** no parsea correctamente el año solicitado
3. **Chart generation** usa el resultado cacheado del query anterior
4. **Response grounding** no sincroniza texto con datos reales

### Verificación de Datos

```sql
-- Verificar que SÍ existen datos de 2024
SELECT DISTINCT EXTRACT(YEAR FROM fecha) as year, COUNT(*)
FROM bank_fact_kpis_mensual
GROUP BY year ORDER BY year;

-- Resultado esperado: 2000-2025 con datos
```

---

## Archivos Involucrados

- `apps/backend/src/services/streaming/chat_stream_producer.py` (context handling)
- `plugins/bank-advisor-private/src/bankadvisor/tools/comparison_tools.py` (date filtering)
- `plugins/bank-advisor-private/src/bankadvisor/tools/ranking_tools.py` (date filtering)
- `apps/backend/src/services/intent/context_enricher.py` (temporal context)

---

## Solución Propuesta

1. **Aislar contexto temporal por query**
   - No heredar el año del prompt anterior automáticamente
   - Extraer explícitamente el año de cada query

2. **Validar año en SQL generado**
   - Si el usuario dice "2024", verificar que WHERE incluya 2024
   - Logging de año solicitado vs año en SQL

3. **Sincronizar texto y chart**
   - El chart debe reflejar exactamente el periodo del SQL ejecutado
   - Incluir el periodo en el título del chart

4. **Verificar disponibilidad de datos**
   - Antes de decir "no hay datos", ejecutar COUNT(*)
   - Responder con el rango de fechas disponible

---

## Criterios de Aceptación

- [ ] Query "ICAP 2024" muestra solo datos de 2024
- [ ] Query "cartera 2025" después de "cartera 2024" muestra 2025 (no bleeding)
- [ ] Texto y gráfica muestran el mismo periodo
- [ ] No responde "no hay datos" cuando sí existen

---

## Referencias

- Ticket relacionado: `2026-02-03__BUG__ranking-data-extraction-failures` (DOING)
- Ticket cerrado: `2026-01-30__BUG__wrong-month-data-mapping`
- Ticket cerrado: `2026-02-03__BUG__response-grounding-desync`

## Feedback Vinculado

**3 reporte(s)** de usuarios en producción.

| # | Feedback ID | Usuario | Query | Feedback | Fecha |
|---|-------------|---------|-------|----------|-------|
| 1 | FDBK-0034 | `cb6c6879` | muestrame la cartera comercial de santander | no me dio la cartera comercial de santander | 2026-02-03 |
| 2 | FDBK-0035 | `cb6c6879` | dame la cartera de consumo de santander | menciona que no se dispone de informacion actualizada, sin embargo, en la gra... | 2026-02-03 |
| 3 | FDBK-0051 | `cb6c6879` | muestrame la cartera comercial de invex | no me dio lo que le pedí | 2026-02-04 |

<details>
<summary>Detalle completo de feedbacks</summary>

### FDBK-0034
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `6bf39d89-1f72-4814-9a1b-aaf0aa99b278`
- **Message**: `07076bf7-360e-492e-8410-ccdd3fb16b0c`
- **Rating**: 👎
- **Query**: "muestrame la cartera comercial de santander"
- **Feedback**: "no me dio la cartera comercial de santander"
- **Fecha**: 2026-02-03T22:59:56.719Z

### FDBK-0035
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `6bf39d89-1f72-4814-9a1b-aaf0aa99b278`
- **Message**: `fdbae129-e077-432f-9a4a-784e0a440da9`
- **Rating**: 👎
- **Query**: "dame la cartera de consumo de santander"
- **Feedback**: "menciona que no se dispone de informacion actualizada, sin embargo, en la grafica y tabla de datos si me muestra infromacion desde diciembre del 2000
  - revisar los datos que despliega, hay saltos muy grandes y valores en cero 
  - no hay valores para el año 2011 y 2012"
- **Fecha**: 2026-02-03T23:34:02.112Z

### FDBK-0051
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `765a97e9-eef8-43aa-8469-720c50e92815`
- **Message**: `84303438-672e-4fb0-8dc8-3ef7c1278a3d`
- **Rating**: 👎
- **Query**: "muestrame la cartera comercial de invex"
- **Feedback**: "no me dio lo que le pedí"
- **Fecha**: 2026-02-04T22:49:20.385Z

</details>
