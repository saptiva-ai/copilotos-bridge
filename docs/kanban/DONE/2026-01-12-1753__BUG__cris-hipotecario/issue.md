# Reporte de Bugs (CRO: Chris Huertas) — 2026-01-12
Contexto: App tipo “chat + métricas” donde el asistente elige una métrica (ej. `CARTERA_VIVIENDA_TOTAL`, `CARTERA_COMERCIAL_TOTAL`, `CARTERA_TOTAL`) y ofrece abrir una gráfica con botón **“Abrir”**. En varios flujos, el asistente **no entiende la intención**, **se queda “pegado” a una cartera**, o la **visualización/datos** salen incoherentes.

---
** Las imagenes estan en img/**

## BUG-CH-001 — NLU/Intención: “hipotecario” vs “vivienda” + rango “últimos 12 meses”
**Evidencia (screenshots):**
- `40ab65f2-2dc8-4f07-a41f-27c49c336910.png`
- `9e0ad2de-3b19-4021-9756-c746a75c3318.png`

**Comentario del usuario (Chris):**
- “No me entendió hipotecario… cuando le pedí vivienda, tampoco me dio los datos. Cuando le pedí los últimos 12 meses disponibles no me entendió.”

**Comportamiento actual:**
- El asistente no aterriza “cartera hipotecaria” a una métrica coherente (parece que intenta forzar selección de opciones).
- No respeta/entiende el constraint temporal “últimos 12 meses disponibles”.
- Termina en una respuesta que no entrega datos o que pide más detalles como si no hubiera entendido el dominio.

**Comportamiento esperado:**
- Normalizar términos: *hipotecario* ≈ *vivienda* (si en su modelo de datos “hipotecario” se mide como “cartera vivienda”, debe mapearse explícitamente).
- Parsear “últimos 12 meses disponibles” como una instrucción de rango de fechas (maximizar el rango disponible hacia atrás 12 meses).
- Si NO existe esa data, decirlo con precisión: “no hay mensualidad / solo hay cortes anuales / solo sistema no por banco”.

**Hipótesis probables (causas):**
1. **Diccionario de sinónimos/ontología incompleta**: no hay regla clara `hipotecario -> vivienda`.
2. **Parser temporal débil**: “últimos 12 meses disponibles” no se traduce a `date_from/date_to`.
3. **Selector forzado**: el flujo tipo wizard obliga “elige banco/métrica”, y el modelo no logra casar eso con el texto natural.
4. **Tool constraints**: el set de métricas permitidas no incluye “hipotecario” y el LLM queda “a ciegas”.

**Dónde buscar (rápido y con bisturí):**
- Config de mapeo intención→métrica (keywords, embeddings, reglas).
- Parser de fechas / normalizador de rangos.
- Prompt del “planner” que decide métrica y dimensiones.
- Logs de tool-calls: ¿qué tool se invocó? ¿con qué `metric_id` y `date_range`?

**Preguntas útiles (para cerrar ambigüedad de datos):**
- ¿“Hipotecario” vive en la misma serie que “Vivienda” o son métricas distintas?
- ¿La data está mensual, trimestral o anual? (Esto explica muchísimo el bug de la gráfica con picos)

---

## BUG-CH-002 — UI/Frontend: botón “Abrir” no muestra gráfica (o queda en blanco)
**Evidencia (screenshots):**
- `40ab65f2-2dc8-4f07-a41f-27c49c336910.png` (Chris: “cuando intento abrir la gráfica, no me deja ver nada.”)
- `9e385b16-e819-451a-9c12-bc6eef5a49af.png`
- `19e4ebc8-9fe2-4a0a-8e35-3d55db65c766.png`

**Comportamiento actual:**
- El asistente ofrece una tarjeta con la métrica y un CTA **“Abrir”**, pero al abrir: **no aparece nada / no carga / parece vacío**.

**Comportamiento esperado:**
- “Abrir” debe:
  1) abrir modal/panel,
  2) disparar fetch de serie,
  3) renderizar estado loading,
  4) renderizar serie o un empty-state explícito (“no hay puntos en el rango”).

**Hipótesis probables (causas):**
1. **La serie viene vacía o con todo ceros** y el chart library revienta o decide no pintar (y ustedes están swallow-eando el error).
2. **Bug de navegación/modal**: route incorrecta, z-index, o el panel abre pero queda fuera de viewport (especialmente si es responsive).
3. **Race condition**: el estado `selectedMetric` cambia después de abrir y el componente queda con `undefined`.
4. **Error silencioso**: hay error en consola pero no se muestra UI fallback.
5. **Backend 4xx/5xx** al pedir la serie (CORS, auth, timeout, payload shape).

**Dónde buscar:**
- Frontend: handler del botón **Abrir** + componente del chart (modal/drawer/page).
- Network tab: request que se dispara al abrir (status + payload).
- Consola: errores de render o de parseo.
- Backend endpoint de series: validación cuando no hay datos (¿regresa `[]`, `null`, o shape inconsistente?).

---

## BUG-CH-003 — “Sticky context”: el asistente se queda pegado a una cartera (“ya no se le olvida esto”)
**Evidencia (screenshots):**
- `9e385b16-e819-451a-9c12-bc6eef5a49af.png` (queda en `CARTERA_VIVIENDA_TOTAL`, BANORTE)
- `0b38ee88-6e59-433c-b0e3-0e95a2025b49.png` (“ya no se le olvida esto”)
- `122f5c29-d119-4373-91eb-a8260bb11218.png` (pregunta de tarjetas y sigue usando `CARTERA_VIVIENDA_TOTAL`)

**Comentario del usuario (Chris):**
- “ya no se le olvida esto”
- “está limitado a unas carteras”

**Comportamiento actual:**
- Después de seleccionar/usar `CARTERA_VIVIENDA_TOTAL` para `SISTEMA, BANORTE`, el asistente:
  - lo trata como **contexto fijo**,
  - incluso para una pregunta nueva (“cuántas tarjetas de crédito…”).

**Comportamiento esperado:**
- Resetear el “scope” cuando cambia la intención.
- Si existe un “pin” de métrica, debe ser **explícito** (UI: “Métrica fija activa”) y el asistente debe saber cuándo ignorarlo.

**Hipótesis probables (causas):**
1. **Estado global de sesión**: guardan `selected_metric`/`selected_bank` en servidor o store y lo reinyectan siempre al prompt.
2. **System prompt accidentalmente rígido**: algo como “You are using METRIC=X” se queda como instrucción inmutable.
3. **Heurística de continuidad agresiva**: el router de intención decide “sigue en el mismo tema” aunque el user cambió de tema.
4. **No existe un “intent boundary detector”** (detecta cambio de tema y resetea herramientas).

**Dónde buscar:**
- Backend: session store / conversation state (dónde se persiste `metric_id`, `bank_id`).
- Prompting: mensajes del sistema que fijan métrica.
- Frontend: si la UI manda `activeMetricId` en cada request sin darse cuenta.

---

## BUG-CH-004 — Mapeo de intención incorrecto: “tarjetas de crédito” termina en “cartera comercial”
**Evidencia (screenshots):**
- `122f5c29-d119-4373-91eb-a8260bb11218.png`
- `3f178a63-6217-4953-9a81-7edfc88d22fd.png`
- `ab8fd7ad-856f-4698-8f4b-b778f5a9a0f2.png`

**Comportamiento actual:**
- Usuario: “cuantas tarjetas de crédito bancarias hay en México”
- El sistema responde con métricas monetarias tipo:
  - `CARTERA_COMERCIAL_TOTAL` (MDP),
  - tendencias raras,
  - y se asume que eso responde “tarjetas”.

**Comportamiento esperado:**
- O se responde con un indicador de **conteo** (número de tarjetas) si existe dataset.
- O se dice claramente: “este sistema no tiene esa estadística (conteos), solo saldos/portafolios”.

**Hipótesis probables (causas):**
1. **Solo existen datasets de “carteras”** (saldos) y el modelo hace “best-effort mapping” incorrecto.
2. **No hay tipado semántico de métricas**: `unit = MDP` vs `unit = count`.
3. **Retrieval por similitud**: “tarjetas de crédito” se parece más a “cartera comercial” en embeddings que a otra cosa (porque no hay nada mejor).

**Dónde buscar:**
- Registro/catálogo de métricas: ¿tienen `unit`, `kind`, `dimensions`?
- Router de intención: reglas “si pregunta es COUNT -> no uses métricas MDP”.
- UI/UX: mostrar límites de cobertura (“Este módulo responde solo sobre X métricas”).

---

## BUG-CH-005 — Data/Viz: gráfica con picos en enero y “caídas” absurdas (granularidad/zero-fill)
**Evidencia (screenshot):**
- `d27ec365-a9ea-44d3-9e81-71110812b8f3.png`

**Comentario del usuario (Chris):**
- “está rara esta gráfica… como que toma datos en donde enero es mucho mayor que los demás meses”
- “no me hace sentido que haya caído tanto la cartera”

**Comportamiento actual:**
- Serie temporal muestra **picos tipo “una vez al año”** (enero) y el resto de meses casi en cero.
- Eso produce lecturas falsas: “-94.7%” o “cayó drásticamente”.

**Comportamiento esperado:**
- Si la data es **anual**, se debe graficar anual (o interpolar/step con claridad).
- Si la data es **mensual**, no debe haber zero-fill artificial.
- Si faltan meses, usar `null` y un UI hint: “faltan meses en la serie”.

**Hipótesis probables (causas):**
1. **Granularidad mal interpretada**: dataset anual metido en eje mensual.
2. **Relleno con ceros**: missing months => 0 en lugar de `null`.
3. **Join incorrecto** (por mes) y solo “match” en enero por cómo están las llaves/fechas.
4. **“Corte de año”**: están usando “fecha de actualización” como fecha del dato.
5. **Scale/units bug**: MDP vs pesos, o “millones de MDP” (doble multiplicación) que distorsiona.

**Dónde buscar:**
- Query SQL/ETL que construye la serie (groupby date).
- Transformaciones de resampling (pandas/polars/db).
- El endpoint que alimenta la gráfica: revisar si manda `0` donde debería mandar `null`.
- Validaciones de integridad: conteo de puntos por año esperado.

---

## BUG-CH-006 — No entrega el breakdown más básico: “cartera total, por banco, por año”
**Evidencia (screenshot):**
- `7e19ed4a-78c7-4af9-b013-cb6c6410f82d.png`

**Comportamiento actual:**
- Usuario: “dame la cartera total, por banco, por año”
- Asistente: “no puedo proporcionar la cartera total por banco y por año… datos limitados a SISTEMA… periodo N/A”
- O sea: justo lo más básico (bank × year) no sale.

**Comportamiento esperado:**
- Si existe dimensión banco y fecha, debe poderse hacer:
  - `GROUP BY bank, year` (o al menos `bank` con filtro anual).
- Si NO existe, UX debe decirlo desde el principio (y no después de preguntar).

**Hipótesis probables (causas):**
1. **El dataset actual solo tiene agregado “SISTEMA”** (sin banco).
2. **La API no soporta dimensiones** (solo un time-series simple).
3. **Permisos**: el usuario no tiene permiso para ver por banco.
4. **El LLM se está confundiendo** y cree que no puede aunque sí se puede (falla en tool-call).

**Dónde buscar:**
- Modelo de datos: ¿existe columna `bank_id`?
- Analytics service: ¿acepta parámetros `group_by=bank` y `bucket=year`?
- UI: selector de dimensiones (si el selector existe, no debe prometer cosas imposibles).

---

# Síntesis de raíz (lo que huele a “causa madre”)
1) **No hay contrato semántico fuerte de métricas** (unidad, granularidad, dimensiones permitidas).  
2) **State management débil**: la métrica “se pega” entre preguntas y contamina intención.  
3) **Serie temporal mal construida**: cero-fill + granularidad equivocada genera gráficas mentirosas.  
4) **UX promete más de lo que la data soporta** (y el asistente improvisa).

---

# Checklist de investigación (para ingeniería)
- [ ] Loggear cada tool-call con: `metric_id`, `bank_scope`, `date_range`, `granularity`, `group_by`, `unit`.
- [ ] Agregar “intent boundary”: si cambia de tema (hipotecas→tarjetas), resetear métrica.
- [ ] Validar serie: si `missing_ratio > X%`, mostrar warning o no calcular tendencia.
- [ ] Tipar métricas: `kind = {amount, count, rate}`, `unit`, `min_granularity`, `dimensions`.
- [ ] “Abrir” debe tener empty-state y error-state (nunca silencio).

---

# Prompt para un agente codificador (Claude Code/Codex) con acceso a terminal
> Objetivo: reproducir, localizar causa y proponer fix mínimo con tests para los 6 bugs.

## Instrucciones
1. **Repro local**
   - Levanta frontend + backend (docker-compose).
   - Abre la app y reproduce estos prompts en el chat:
     - “¿Cómo se comportó la cartera hipotecaria… últimos 12 meses?”
     - “cuantas tarjetas de crédito bancarias hay en México”
     - “dame la cartera total, por banco, por año”
   - Clic en **Abrir** en cada tarjeta y captura: consola + network.

2. **Inspección de estado “sticky metric”**
   - Encuentra dónde se guarda `selectedMetric/selectedBank`:
     - frontend store (redux/zustand/context)
     - backend session (redis/db/in-memory)
     - prompt injection (“Estoy usando X para Y…”)
   - Confirma si se manda en cada request aunque el user cambió intención.

3. **Inspección del router de intención (métrica)**
   - Ubica el módulo que mapea texto→métrica.
   - Agrega reglas mínimas:
     - `hipotecario -> vivienda` (si aplica)
     - Si user pide **conteo** (“cuantas”, “número de”), NO elegir métricas con unit monetaria.
   - Si no hay dataset de conteo, responder “no soportado” sin inventar.

4. **Bug de gráfica (Abrir)**
   - Localiza componente ChartModal/Drawer/Page.
   - Asegura:
     - loading state
     - error state (render del error real)
     - empty state (serie vacía o todo-null)
   - Log de payloads para detectar shape inconsistente.

5. **Bug de granularity / enero spikes**
   - Ubica query SQL/ETL de series.
   - Busca si:
     - se hace fill de meses con 0
     - se convierte anual->mensual
   - Cambia a:
     - `null` para missing
     - o graficar por año si dataset es anual
   - Agrega test que valide “no más de N meses en cero consecutivos” si debería ser mensual.

6. **Breakdown por banco/año**
   - Verifica si el dataset tiene dimensión banco.
   - Si sí: implementa `group_by=bank, bucket=year`.
   - Si no: cambia UX/respuesta para no prometerlo.

## Entregables
- PR con:
  - fix de sticky metric (reset por intent boundary)
  - fix de Abrir (states + no-silent-fail)
  - fix de granularity (no zero-fill, bucket correcto)
  - tests unit/integration (mínimo 1 por bug)
- Documento corto en `docs/bugs/CH-2026-01-12.md` con antes/después + capturas.

---

## Resolution Status (2026-01-19)

**Status: RESOLVED (Consolidated)**

This issue was resolved as part of **ISSUE-003** fixes. The overlapping bugs were addressed by:

| Bug | Resolution |
|-----|------------|
| BUG-CH-001 (NLU/sinónimos) | Synonyms expansion in `synonyms.yaml`, RAG priority fixes (`ea5eff58`) |
| BUG-CH-002 (Abrir no funciona) | BA-002 multi-tenant + chart flow fixes (`fead91a5`) |
| BUG-CH-003 (Sticky context) | State reset in chart flow handler (`d3901120`) |
| BUG-CH-004 (Mapeo incorrecto) | RAG grounding improvements (`db9ca3e0`) |
| BUG-CH-005 (Gráfica/granularidad) | Chart normalizer service in streaming refactor |
| BUG-CH-006 (Breakdown) | Data availability documented; system-level only |

**Related:** See `docs/kanban/DONE/ISSUE-003_user-reported-bugs/` for full fix details.


