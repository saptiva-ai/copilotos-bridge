# Bug Report (basado en screenshots) — Octavios Chat / Saptiva Turbo
Fecha de screenshots: 2026-01-13 y 2026-01-14  
Fuentes: comentarios de Carlos Lara y Cris Huertas (Slack) + UI del chat + panel de gráficas
Imagenes: img/ 
---

## Índice de evidencias (archivos)
1) `17c7ddfd-9b8d-4044-87e3-6a1885a7c1b4.png` — “Preguntas como botones” (UX)  
2) `77226c55-5054-4c72-a1d3-7c9d8c6c541b.png` — “Datos solo hasta dic 2024” (recencia/ingesta)  
3) `8d9a6c31-71f2-4b20-825a-dfb018a53bb7.png` — “IMOR = 2024%” (parsing/unidades)  
4) `f4579494-9296-4da4-ad89-3039856f0623.png` — “ICAP = 2024%” (parsing/unidades)  
5) `148f964b-f637-4bcf-ae74-0001a1871858.png` — “Solo hay datos hasta 2023 vs 2025” (ambiente/dataset)  
6) `77f0a9f8-b400-478c-91fb-f94efb9c8d1d.png` — “Error al cargar la gráfica” (payload inválido)  
7) `00ce35b8-0686-403f-8ead-49cb4b1c0d34.png` — “Tabla con números incorrectos” (grounding / data correctness)  
8) `0232d0c3-a5c6-49ba-a23c-f64aa0c84459.png` — “No restaura gráfica al volver / en blanco” (persistencia / rehidratación)

---

## 1) `17c7ddfd-...png` — Preguntas se muestran como botones (UX + semántica incorrecta)
### Qué se ve / qué reporta el usuario
Carlos: “No me hace mucho sentido que esas preguntas se presenten como botones.”  
La UI dice “Necesito un poco más de información…” y luego muestra:
- “¿De qué banco o institución financiera deseas la información?”
- “¿Para qué periodo de tiempo necesitas los datos?”
Ambas aparecen como *botones/cajas clicables*.

### Problema (comportamiento actual)
El sistema “pide aclaraciones”, pero la representación como botón sugiere acción inmediata / quick-replies, no “falta de información”.
Se siente como que el producto te está empujando a clickear en vez de contestar.

### Comportamiento esperado
- Mostrar estas preguntas como texto normal + inputs (dropdown/autocomplete para banco, date-range picker para periodo).
- Si se usan quick-replies, que sean opciones concretas (p. ej. “BBVA”, “Santander”, “2023”, “Últimos 12 meses”), no preguntas.

### Hipótesis técnicas
- El backend está devolviendo un bloque tipo `clarification_questions[]` y el frontend lo mapea a componente “Button/Chip” por default.
- No existe distinción entre:
  - `question` (requiere input del usuario)
  - `option` (quick reply)
- O están usando el mismo renderer de “tool suggestions” para “clarification prompts”.

### Debug plan
- Inspeccionar payload del mensaje en Mongo: buscar estructuras tipo `ui_blocks`, `actions`, `suggestions`, `clarifications`.
- Revisar renderer del message card en frontend: ¿qué tipo dispara render de botón?

---

## 2) `77226c55-...png` — Dataset parece terminar en dic 2024 (recencia / ingesta)
### Qué se ve / qué reporta el usuario
Texto arriba: “Validar con Fernando Saavedra… parece que tiene datos hasta diciembre 2024… ¿Cómo tenemos data más actualizada?”
En la respuesta el sistema dice que no hay IMOR a cierre dic 2025 y propone consultar dic 2024 como “último dato”.

### Problema (comportamiento actual)
- El sistema afirma que no hay datos y además justifica con “todavía no publican reportes oficiales para dic 2025”.
- Pero por contexto (y por comentario posterior de Cris) **ustedes sí tenían data hasta sep/oct 2025** → suena a:
  1) el sistema está conectado a un dataset viejo, o
  2) hay filtros/cortes de fecha, o
  3) hay un bug en el “max available date”.

### Comportamiento esperado
- Responder con el rango real disponible (p. ej. “último dato: 2025-10”).
- Si no hay, decir “no está en nuestra base” sin inventar una razón temporal dudosa.

### Hipótesis técnicas
- Conexión a otra BD/colección (staging vs prod).
- Un “cap” hardcodeado: `max_year=2024` o `max_date=2024-12-31`.
- La consulta a Mongo filtra por `report_type == annual` y descarta mensual 2025.
- ETL incompleto: los docs 2025 existen pero están en otro esquema/colección y el router no los ve.

### Debug plan
- En Mongo: obtener `max(date)` por métrica IMOR y por banco.
- Revisar “router” del plugin IMOR: ¿qué query arma cuando piden dic 2025?
- Confirmar con Fernando cuál es la fuente correcta y hasta qué fecha llega.

---

## 3) `8d9a6c31-...png` — IMOR = 2024% (valor imposible: parsing/unidades)
### Qué se ve / qué reporta el usuario
Arriba: “Error de fondo de nuevo. Esto parece estar mal.”
La respuesta dice: “IMOR del SISTEMA al cierre de 2024, que fue **2024%**.”

### Problema (comportamiento actual)
Año “2024” se está usando como si fuera el valor porcentual → esto huele a bug de mapeo de campos:
- se tomó el campo `year` como `value`,
- o concatenación errónea `f"{year}%"`,
- o un fallback tipo “si no hay value, usa year”.

### Comportamiento esperado
- Si no hay dato, devolver “no disponible” y no renderizar un número.
- Si hay dato, debería ser algo como `2.3%`, `3.1%` (lo que aplique), nunca `2024%`.

### Hipótesis técnicas
- Bug en normalización: `value = doc.get("value", doc.get("year"))`
- Confusión entre columnas (`period`, `value`, `label`) al convertir a series.
- Conversión de unidades: `0.2024 -> 2024%` por multiplicación *x100* aplicada dos veces, o por parsing de string.

### Debug plan
- Trazar el documento Mongo exacto que alimenta esa respuesta.
- Loggear el “row” previo a formateo y el output final.

---

## 4) `f4579494-...png` — ICAP = 2024% (misma clase de bug)
### Qué se ve / qué reporta el usuario
“De nuevo con 2024%. Hay algo hardcodeado que está mal.”
La respuesta: “ICAP para Banorte en 2024, que fue **2024%**”.

### Problema
Exactamente el mismo patrón que IMOR. Esto sugiere que el bug está en una capa común:
- formateador de métricas (%),
- normalizador de series temporales,
- mapper de “period/value”.

### Comportamiento esperado
- ICAP típicamente no debería aparecer como 2024%.
- Si hay ambigüedad de definición (ICAP vs índice de capitalización), se debe resolver por catálogo de métricas, no con inventos.

### Hipótesis técnicas
- “Formatter” global para cualquier métrica que termina en `%` usando el campo equivocado.
- Al construir `points[]`, se está metiendo `x=year`, `y=year` por error.

### Debug plan
- Buscar en código dónde se genera el string `"{value}%"`.
- Unit tests para: “si value > 1000 y es porcentaje, marcar como inválido”.

---

## 5) `148f964b-...png` — Inconsistencia: “solo hay datos hasta 2023” vs dataset real hasta 2025
### Qué se ve / qué reporta el usuario
Cris: “en general me emociona… pero: **solo hay datos hasta 2023**. Los datos que les había pasado estaban hasta sep/oct 2025.”

### Problema
Esto grita “conectado al dataset equivocado” o “feature flag apuntando a snapshot viejo”.

### Comportamiento esperado
- Si la data existe (sep/oct 2025), el sistema debe verla.
- Si NO existe en ese ambiente, el sistema debe explicar “en este entorno solo está cargado hasta 2023”.

### Hipótesis técnicas
- Variables de entorno: URI de Mongo o DB name apuntando a `demo`/`staging_old`.
- Namespace multi-tenant: tenant incorrecto (otro cliente / otra colección).
- Index/partition: las queries recientes no matchean por formato de fecha (string vs Date).

### Debug plan
- Confirmar “qué ambiente” estaba usando Cris (URL / tenant / branch).
- Comparar `db.stats()` + nombres de colecciones vs el ambiente correcto.
- Checar `max(date)` en ambos ambientes.

---

## 6) `77f0a9f8-...png` — Error al cargar la gráfica (payload inválido o faltante)
### Qué se ve / qué reporta el usuario
Carlos: “Es un error de renderizado?”
Panel derecho: “Error al cargar la gráfica — Datos de gráfica inválidos o faltantes” + botón “Reintentar”.
Título arriba: `GRAFICA CARTERA_VIVIENDA_TOTAL`.

### Problema
- El frontend recibió algo que no cumple el contrato esperado (por ejemplo: `series=[]`, `x=null`, `y="N/A"`, JSON mal formado, etc.)
- O la API falló y el FE lo tradujo a “datos inválidos”.

### Comportamiento esperado
- Si la serie viene vacía: mostrar “No hay datos para este rango” (no “error”).
- Si la API falla: mostrar error con `request_id` para rastreo.

### Hipótesis técnicas
- Backend devuelve `200` con `data: null` (y el FE no lo tolera).
- El router de métricas no reconoce `CARTERA_VIVIENDA_TOTAL` y retorna placeholder.
- Campos con strings tipo `"115k"` en lugar de número → rompe chart.

### Debug plan
- Revisar en Mongo si se almacenó un “chart artifact” con schema incompleto.
- Revisar logs de la ruta `/chart` o equivalente: request/response.

---

## 7) `00ce35b8-...png` — Números incorrectos / posible alucinación
### Qué se ve / qué reporta el usuario
Cris: “los datos están mal… todos los bancos colocaron aprox 115K créditos hipotecarios en 2024 y aquí dice que solo BBVA colocó esa cantidad”
Se ve una tabla “Evolución de la cartera hipotecaria (2019–2023)”.

### Problema
Dos posibilidades (y ambas son graves):
1) **Grounding roto**: el modelo está inventando números por “rellenar”.
2) **Semántica mal mapeada**: “colocación de créditos” vs “número de créditos” vs “cartera (MDP)” se mezclan.

### Comportamiento esperado
- Si falta data: decir “no tengo la cifra exacta en la base” y pedir fuente/rango.
- Si hay data: citar de dónde sale (tabla/campo/fecha) y no contradecir hechos obvios del dominio.

### Hipótesis técnicas
- No hay “term-in-chunk validation” / “no-hallucination guard” en tablas.
- La tabla se arma con “defaults” (ej. 115,000) para llenar.
- Se están mezclando bancos/periodos por join incorrecto.

### Debug plan
- Ver si la respuesta incluye trazas internas (ids de docs, sources). Si no: agregar.
- Auditar pipeline de “table synthesis”: debe fallar si no hay fuentes.

---

## 8) `0232d0c3-...png` — No restaura la gráfica al volver (rehidratación / persistencia)
### Qué se ve / qué reporta el usuario
Carlos: “No sé si bajaste el servicio pero probé ahorita en blanco y **no restaura la gráfica**.”
Se ve una conversación existente con gráfica ICAP (BBVA vs Santander). El problema es que al “volver” o mandar mensaje en blanco, el panel no reconstruye/rehidrata.

### Problema
La gráfica parece ser un “artifact” asociado a mensajes.
Si el servicio se reinicia o si se reabre conversación, el UI debería reconstruir desde Mongo (o re-fetch por artifact_id).
No lo está haciendo consistentemente.

### Comportamiento esperado
- Al abrir conversación: cargar mensajes + artifacts asociados.
- Si el usuario envía un mensaje vacío: no debería romper nada; idealmente ignorarlo.

### Hipótesis técnicas
- Los artifacts no se persisten (solo viven en memoria).
- Se persisten pero no hay “link” mensaje->artifact (`artifact_id` missing).
- El FE necesita `conversation_state.graph_context` y no lo reconstruye si falta.
- “Blank prompt” dispara un flujo raro: limpia el panel sin re-fetch.

### Debug plan
- En Mongo: verificar si existe `artifact` para esa gráfica y si está referenciado.
- Revisar el “rehydration path”: cuando se carga historial, ¿también piden artifacts?

---

# Plan de debug (cross-cutting)
### A. Confirmar si es *data layer* o *render layer*
1) Para IMOR/ICAP: sacar `max(date)` y un sample de docs reales.
2) Para gráficas: verificar contrato de payload (schema) y validar con JSON schema.
3) Para tablas: exigir evidencia (source ids) o bloquear generación.

### B. Cortar el problema de raíz: validaciones
- Si métrica es `%` y `value > 100` → marcar invalid / revisar unidad.
- Si `value == year` → detectarlo como bug.
- Si series vacía → “no data”, no “error”.

### C. Observabilidad mínima para no adivinar
- Incluir `request_id`, `metric_key`, `tenant`, `env`, `artifact_id` en logs y (opcionalmente) en debug UI.

---

# Prompt para un agente codificador (con SSH + Mongo) — investigación por screenshot
> Objetivo: localizar en Mongo las conversaciones/mensajes/artifacts que corresponden a cada screenshot, extraer identifiers (conversation_id, message_id, artifact_id), y proponer el fix (backend/FE) con evidencia.

## Instrucciones para el agente
1) **Conectarse por SSH** al host correcto y entrar a `mongosh`.
2) **Identificar DB y colecciones** relevantes (ej: `conversations`, `messages`, `artifacts`, `charts`, `events`, `tenants`).
3) Para cada screenshot, ejecutar búsquedas por:
   - textos exactos (regex),
   - keys de métrica (`IMOR`, `ICAP`, `CARTERA_VIVIENDA_TOTAL`),
   - y ventana de tiempo (2026-01-13 10:05–10:25, y 2026-01-14 02:15–02:30).
4) Con cada match:
   - imprimir `_id`, `conversation_id`, `created_at`, `tenant`, `env`,
   - y el payload completo del bloque de UI (actions/suggestions/artifact refs).
5) **Verificar integridad del artifact**:
   - si existe artifact_id,
   - si tiene `series` válida,
   - si su schema coincide con lo que espera el frontend.
6) Redactar hallazgos + hipótesis confirmadas + fix sugerido.

## Queries sugeridas (ajustar nombres reales de colecciones/campos)
### 0) Recon: listar colecciones y ejemplo de schema
- `show dbs`
- `use <db>`
- `show collections`
- `db.messages.findOne()`
- `db.artifacts.findOne()`

### 1) Screenshot 1 — “preguntas como botones”
Buscar el texto:
- “Necesito un poco más de información”
- “¿De qué banco o institución financiera deseas la información?”
- “¿Para qué periodo de tiempo necesitas los datos?”
```js
db.messages.find(
  { $or: [
      { "text": /Necesito un poco más de información/i },
      { "text": /¿De qué banco o institución financiera/i },
      { "text": /¿Para qué periodo de tiempo necesitas/i },
      { "ui_blocks.text": /¿De qué banco/i },
      { "ui_blocks.text": /¿Para qué periodo/i }
  ]},
  { conversation_id:1, created_at:1, tenant:1, env:1, text:1, ui_blocks:1, actions:1 }
).sort({created_at:-1}).limit(20)
Luego: ubicar si actions[] tiene tipo button/chip y si debería ser input.

2) Screenshot 2/3 — IMOR “último dato dic 2024” y “2024%”
js
Copy code
db.messages.find(
  { $or: [
      { text: /IMOR/i },
      { text: /2024%/ },
      { text: /diciembre de 2024/i },
      { text: /diciembre de 2025/i }
  ]},
  { conversation_id:1, created_at:1, text:1, tool_calls:1, metadata:1 }
).sort({created_at:-1}).limit(50)
Luego:

extraer tool_calls (si existe) para ver query real

extraer metric_key, date_range, bank_scope

localizar docs de datos IMOR:

js
Copy code
db.imor.find({}, {date:1, bank:1, value:1}).sort({date:-1}).limit(10)
db.imor.aggregate([{ $group:{ _id:null, maxDate:{ $max:"$date" }}}])
Si la fecha está como string, repetir con parsing o comparar lexicográfico.

3) Screenshot 4 — ICAP “2024%”
js
Copy code
db.messages.find(
  { $or: [
      { text: /ICAP/i },
      { text: /2024%/ },
      { text: /Banorte/i },
      { text: /Santander/i },
      { text: /BBVA/i }
  ]},
  { conversation_id:1, created_at:1, text:1, tool_calls:1, metadata:1 }
).sort({created_at:-1}).limit(50)
Luego revisar colección de ICAP:

js
Copy code
db.icap.aggregate([{ $group:{ _id:null, maxDate:{ $max:"$date" }}}])
db.icap.find({ bank:"Banorte" }, {date:1, value:1, year:1}).sort({date:-1}).limit(20)
Confirmar si value está null y year existe → bug de fallback.

4) Screenshot 6 — “Error al cargar la gráfica” (CARTERA_VIVIENDA_TOTAL)
Buscar por key y por mensaje de error:

js
Copy code
db.messages.find(
  { $or: [
      { "metadata.metric_key": "CARTERA_VIVIENDA_TOTAL" },
      { text: /CARTERA_VIVIENDA_TOTAL/i },
      { text: /Error al cargar la gráfica/i }
  ]},
  { conversation_id:1, created_at:1, text:1, metadata:1, artifact_id:1 }
).sort({created_at:-1}).limit(50)
Si hay artifact_id, traerlo:

js
Copy code
db.artifacts.find({ _id: ObjectId("<artifact_id>") })
Validar:

series existe y es array

cada punto tiene x fecha y y número

no hay NaN, strings, nulls

5) Screenshot 8 — “no restaura la gráfica”
Buscar conversación y artifacts:

js
Copy code
db.messages.find(
  { $or: [
      { text: /no restaura la gráfica/i },
      { text: /ICAP histórico/i },
      { "metadata.metric_key": "ICAP" }
  ]},
  { conversation_id:1, created_at:1, text:1, artifact_id:1, metadata:1 }
).sort({created_at:-1}).limit(100)
Luego, por conversation_id:

js
Copy code
db.messages.find({ conversation_id:"<id>" }, { created_at:1, text:1, artifact_id:1 }).sort({created_at:1})
db.artifacts.find({ conversation_id:"<id>" }).sort({created_at:-1}).limit(20)
Ver si:

artifacts existen pero el FE no los pide,

o no existen (se perdieron al reiniciar).

Entregable del agente
Tabla por screenshot: conversation_id, message_id, artifact_id, tenant, env, metric_key, date_range.

Diagnóstico confirmado (con evidencia de docs/payloads).

Fix propuesto:

Backend: parsing/validación/queries + tests

Frontend: renderer de clarifications + rehidratación de artifacts

Lista de “guardrails” para evitar que vuelva (schema validation + no-hallucination para tablas).
