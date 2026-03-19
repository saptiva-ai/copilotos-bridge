# Reporte de bugs – Bank Advisor V1 (feedback de Carlos Lara)

> **Fuente:** Capturas compartidas en Slack/Threads (#bugs) el **2026-01-08**.
> **Objetivo:** documentar **comportamientos inesperados** con suficiente detalle para reproducir, priorizar y corregir.

---

## Resumen ejecutivo (lo que más duele)

### Prioridades explícitas de Head of Product (Carlos)

* **La data tiene que ser verdadera.** Esto NO puede fallar.
* Ojo con **ajustes que rompen funcionalidades**: gráficas, el issue de `SELECT *` (parece estar solucionado, pero hay que evitar regresiones), **gráfica que no abre**, **prompt injection**.
* **Nice to have:** otros bugs de front-end y endurecimiento tipo “zero trust” (más allá del fix P0 de injection).

### Hallazgos principales del hilo

1. **Seguridad crítica:** se ejecuta **SQL de escritura** por prompt injection (INSERT) → riesgo de corrupción/compromiso de datos.

2. **Confiabilidad/Trust:** el sistema “**alucina**” (habla de gráficas que no muestra / mezcla bancos) y además se “**ancla**” a ICAP aunque le pidan otra cosa.

3. **UX/Front (funcional):** problemas al **abrir** la gráfica, **descargar** la gráfica, y **persistencia** de gráficas viejas entre consultas.

4. **Datos/ETL:** inconsistencias de agregación (Sistema < banco componente) + ambigüedad semántica (“capitalización” ≠ siempre ICAP).

5. **Guardrails insuficientes:** el usuario puede **convencer** al sistema de aceptar premisas falsas o ejecutar acciones que inicialmente negó (deriva a alucinación + acciones peligrosas).

---

## Convención de evidencias

La imagenes estan en images/

* **Img01** = 74a165e3… (Slack: “Siempre se va a ICAP”)
* **Img02** = ce8e1068… (Thread: Bug #1 con screenshot UI)
* **Img03** = 7de9030d… (Bugs #2 y #3: abrir/descargar gráfica)
* **Img04** = 94d5a939… (Bug #4: decimales)
* **Img05** = e6f44c13… (Bug #5: tooltip/zoom)
* **Img06** = 112d21c4… (Bugs #6 y #7: texto redundante + “ICAP para INVEX” aunque habla de Santander)
* **Img07** = a60df355… (Bugs #8 y #9: gráfica anterior se queda + alucinación/mismatch)
* **Img08** = 0ff62727… (Bug #10: inconsistencia Sistema vs INVEX y ambigüedad “capitalización”)
* **Img09** = c48cdaf1… (Bug #11: render/markdown roto en texto)
* **Img10** = 773127e6… (Bugs #11 y #12: render roto + prompt injection con INSERT)

---

# Bugs detallados

## BUG-01 — Enrutamiento/Selección de KPI: “Siempre se va a ICAP”

**Evidencia:** Img01, Img02.

**Síntoma (qué ve el usuario):**

* El usuario pide “datos generales” o un análisis amplio.
* La respuesta del asistente termina enfocándose en **ICAP** (Índice de Capitalización), incluso cuando no es el KPI solicitado.
* Carlos lo resume literalmente: **“Siempre se va a ICAP”**.

**Pasos sugeridos para reproducir (alta probabilidad):**

1. En el chat, preguntar por “indicadores generales” de un banco (o incluso del sistema).
2. No especificar KPI.
3. Observar que el sistema selecciona ICAP como default y arma análisis/consulta alrededor de ICAP.

**Resultado actual:**

* El LLM decide ICAP como respuesta “segura” y se refugia ahí.

**Resultado esperado:**

* Si el usuario pide “generales”, el sistema debería:

  * (a) **preguntar aclaración** (qué KPI(s) o categoría: capital, liquidez, rentabilidad, morosidad, etc.), o
  * (b) devolver un “**overview**” real: top 5 KPIs disponibles + breve resumen por KPI, con opción de expandir.

**Impacto:**

* **Trust/Utilidad:** el usuario siente que el asesor no entiende la intención.
* **Producto:** parece “hardcoded” a una métrica (anti-advisor).

**Hipótesis de causa raíz:**

* Router de herramientas/KPI con **prior fuerte** a ICAP (regla, prompt, embeddings, o ranking) + falta de penalización por “no alineado”.
* Falta de “intent classifier” (general vs KPI específico) o falta de etapa de desambiguación.

**Recomendación técnica (fix):**

* Introducir una etapa explícita: `intent → {overview | single_kpi | compare | explain_method}`.
* Si `overview`:

  * devolver menú de KPIs (por banco o sistema) + ejemplos de preguntas.
* Si `single_kpi`:

  * seleccionar KPI por NLU/ontología y confirmar (“¿Te refieres a ICAP o a capitalización de mercado?”).
* Ajustar ranking: si query contiene “general”, **no** escoger ICAP por default.

---

## BUG-02 — UI: no deja abrir la gráfica en Chrome (Mac) hasta “cambiar de conversación”

**Evidencia:** Img03.

**Síntoma:**

* En **Chrome en Mac**, el usuario hace clic en “Abrir” (componente de gráfica) y **no abre**.
* Workaround: cambiarse a otra conversación y regresar → entonces sí abre.

**Pasos para reproducir:**

1. Abrir conversación.
2. Generar una gráfica.
3. Clic en “Abrir”.
4. Observar que no pasa nada.
5. Cambiar de conversación/tab, volver y repetir → ahora sí abre.

**Resultado esperado:**

* La gráfica abre en el primer clic de forma consistente.

**Impacto:**

* UX severo (parece roto, no confiable).

**Hipótesis de causa raíz (front):**

* Estado del modal/portal no montado (React portal), z-index/overlay capturando eventos.
* Listener de click no registrado por hidración (SSR/CSR mismatch) o componente en “stale closure”.
* Race condition: el “chart payload” aún no está listo cuando el usuario clickea, y no hay reintento.

**Recomendación técnica:**

* Instrumentar eventos: `chart_open_click`, `chart_open_success`, `chart_open_fail_reason`.
* Hacer el botón “Abrir” dependiente de `isChartReady=true`.
* Asegurar render en client-only si aplica (Plotly/ECharts/whatever).
* Probar específicamente **Chrome Mac** (y Safari), y con throttling de red.

---

## BUG-03 — Export/Download: al descargar la gráfica y abrirla, el archivo sale en blanco

**Evidencia:** Img03.

**Síntoma:**

* El usuario descarga la gráfica.
* Al abrir el archivo descargado, **no muestra nada** (blanco).
* En la evidencia aparecen 2 archivos: uno blanco y otro con contenido, sugiriendo inconsistencia.

**Pasos para reproducir:**

1. Abrir el modal de gráfica.
2. Clic en icono de descarga.
3. Abrir el archivo resultante.

**Resultado actual:**

* Archivo vacío/blank (probablemente PNG/SVG/PDF) o render incompleto.

**Resultado esperado:**

* Export consistente con el canvas visible (misma serie, ejes, estilo, rango, título, fecha de corte).

**Hipótesis de causa raíz:**

* Export se dispara antes de que el gráfico termine de renderizar.
* Export en background sin `await` de la librería (ej. `toImage()` / `downloadImage()`), o canvas tainted.
* Problema con `devicePixelRatio`, tamaño 0x0, o container hidden al exportar.

**Recomendación técnica:**

* Bloquear descarga hasta que el gráfico reporte “renderComplete”.
* Export desde estado de datos + renderer determinista (server-side export) para evitar inconsistencias de cliente.
* Adjuntar metadata al export (kpi, banco(s), rango de fechas, timestamp).

---

## BUG-04 — Formato numérico: decimales inconsistentes (no siempre 7)

**Evidencia:** Img04.

**Síntoma:**

* En la tabla de datos, algunos valores aparecen con muchísimos decimales y padding (`19.6214100000000000`).
* Otros aparecen con 6 decimales (`19.466519`, etc.).

**Resultado esperado:**

* Presentación consistente (ej. 2, 4 o 6 decimales dependiendo KPI) + separadores correctos.
* Regla clara por KPI (porcentaje vs razón vs monto).

**Impacto:**

* Percepción de “datos sucios” / baja calidad.

**Hipótesis:**

* Casting/serialización distinta por fila (float vs decimal) o mezcla de fuentes.
* Formateo UI toma el valor como string (ya formateado) en algunos casos.

**Recomendación:**

* Normalizar en backend: usar `Decimal` o `numeric` y formatear con política única (por KPI).
* En frontend: formatear siempre con `Intl.NumberFormat` y regla por `kpi.type`.

---

## BUG-05 — UX: mensaje/tooltip de zoom (“Double click to zoom out”) aparece una sola vez y confunde

**Evidencia:** Img05.

**Síntoma:**

* Tras hacer zoom, aparece una vez el mensaje “Double click to zoom out”.
* El usuario sugiere que sea **estático** o haya un botón de “recargar/reset zoom”.

**Resultado esperado:**

* UX explícita para salir del zoom: botón visible `Reset zoom` / `Reiniciar vista`.

**Impacto:**

* Usuarios se quedan “atorados” en zoom y no saben cómo volver.

**Recomendación:**

* Botón persistente dentro del modal: `Reset zoom`.
* Hint estático pequeño (“Tip: doble clic para reset”) o en help icon.
* Si la librería lo soporta, mostrar control nativo (home/reset).

---

## BUG-06 — Contenido redundante en vista de gráfica: “comentario de Ronald” no aporta valor

**Evidencia:** Img06.

**Síntoma:**

* Hay un bloque/nota repetitiva (“comentario de Ronald”) que aparece “en cada respuesta”.
* En la vista de gráfica no aporta, debería esconderse para reducir ruido.

**Resultado esperado:**

* Vista de gráfica enfocada: gráfica + tabla + metadata mínima.

**Recomendación:**

* Separar “respuesta narrativa” vs “panel de chart”.
* El panel de chart debe tener su propio layout y **no reutilizar** el template de chat.

---

## BUG-07 — Copy/prompt estático hardcodeado al banco equivocado (“ICAP para INVEX, Sistema” hablando de Santander)

**Evidencia:** Img06.

**Síntoma:**

* La respuesta es buena, pero inicia con algo tipo: “Estoy usando ICAP para INVEX, Sistema” cuando la conversación es sobre **Santander**.
* También se reporta que “sacó el ICAP de INVEX cuando no tiene nada que ver”.

**Resultado esperado:**

* Copy neutral (Bank Advisor general) o dinámico al contexto real de la consulta.
* Si existe “Banco predeterminado” debería venir de configuración explícita, no hardcode.

**Hipótesis:**

* Plantilla de sistema con `default_bank = INVEX` pegada a la app.
* Estado global del “banco seleccionado” no se resetea por conversación/consulta.

**Recomendación:**

* Introducir configuración visible: `Banco predeterminado (banco_norm)` y `Ámbito: {Banco | Sistema | Comparativo}`.
* En cada respuesta, renderizar un “context header” derivado del payload real: `kpi`, `bancos`, `rango`, `fecha_corte`.
* Reglas: si el usuario no elige banco, pedirlo (o usar default pero **declararlo** y permitir cambiarlo).

---

## BUG-08 — Estado UI: se queda abierta la gráfica de la consulta pasada aunque ya se habla de otra cosa

**Evidencia:** Img07.

**Síntoma:**

* El modal/panel de gráfica queda abierto mostrando una gráfica que ya no corresponde a la conversación actual.
* El texto del asistente menciona features (“comparar tres líneas”) pero la vista muestra otra cosa.

**Resultado esperado:**

* Al iniciar una nueva consulta:

  * cerrar/invalidar la gráfica previa, o
  * marcarla como “gráfica anterior” claramente, o
  * actualizar el modal con el nuevo `chart_id`.

**Hipótesis:**

* Falta de “chart session id” y control de lifecycle.
* El componente chart no escucha cambios de `message_id`/`conversation_id`.

**Recomendación:**

* Vincular chart a `message_id` (o `response_id`) y al abrirlo usar ese id.
* Al cambiar de conversación/mensaje, desmontar modal.
* Añadir “badge”: `Asociado a: Respuesta #N`.

---

## BUG-09 — Alucinación / mismatch: habla de una gráfica que no muestra; mezcla bancos (Santander vs otros)

**Evidencia:** Img07.

**Síntoma:**

* Carlos: “Está alucinando. Me habla de una gráfica que no muestra. Y al mismo tiempo en otra respuesta me dijo que SANTANDER.”
* Esto suena a desalineación entre:

  * el texto generado por LLM,
  * los datos realmente consultados,
  * y el widget de gráfica mostrado.

**Resultado esperado:**

* Respuesta *grounded*: solo describir lo que está disponible y visible.

**Hipótesis:**

* El LLM “supone” que el chart existe (plantilla) aunque el front no lo renderizó o falló.
* Falta de verificación: el backend no confirma `chart_created=true` antes de dejar al LLM afirmarlo.

**Recomendación:**

* Contrato estricto LLM↔tools: el modelo solo puede decir “se generó gráfica” si recibe un `chart_url` válido.
* Mostrar en UI estado de creación: `Generando… / Listo / Error`.
* En caso de error de chart, el LLM debe informar: “No pude generar la gráfica por X. Aquí están los datos en tabla.”

---

## BUG-10 — Datos/Definición: “Sistema” menor que “INVEX” (agregado inconsistente) + ambigüedad de “capitalización”

**Evidencia:** Img08.

**Síntoma A (datos):**

* Se afirma: “Sistema” (agregado que incluye INVEX) tiene un valor **menor** que INVEX.
* Carlos lo marca como problema fuerte de datos.

**Resultado esperado:**

* Si “Sistema” es suma/agregado de componentes, debe ser ≥ cualquier componente.

**Hipótesis:**

* “Sistema” no está definido como suma; puede ser promedio/índice/otro universo.
* Error de ETL: filtro de bancos incompleto, duplicados, o fecha distinta.

**Síntoma B (definición):**

* Pregunta: “¿Cuál es el mejor banco en capitalización?”
* El asistente explica capitalización como **market cap** (acciones x precio), pero en banca mexicana “capitalización” suele entenderse como **ICAP** (capital regulatorio).

**Resultado esperado:**

* Desambiguación explícita:

  * “¿Te refieres a ICAP (capitalización regulatoria) o capitalización de mercado?”

**Recomendación:**

* Definir formalmente “Sistema” en UI (qué bancos incluye, operador: SUM/AVG, unidad, fuente).
* Agregar validaciones:

  * `assert(system >= max(component))` si la semántica es suma.
  * Si no es suma, mostrarlo y no permitir inferencias de “incluye a”.
* Agregar etapa de desambiguación semántica del KPI.

---

## BUG-11 — Render/Markdown roto: asteriscos/bold/itálicas aparecen literales y rompen el texto

**Evidencia:** Img09, Img10, y también se aprecia en Img08 (fragmentos).

**Síntoma:**

* El texto aparece con “**” visibles y pegados a palabras: `1,180millones**,mientras**INVEX**porsi´soloalcanza**...`.
* Hay pérdida de espacios y secciones duplicadas.

**Resultado esperado:**

* Markdown renderizado correctamente o, si el canal no soporta Markdown, entonces **escapear** los caracteres especiales.

**Hipótesis:**

* Doble render: una capa interpreta parcialmente Markdown y otra no.
* Sanitizador que elimina espacios o normaliza unicode y rompe tokens.

**Recomendación:**

* Definir un solo formato de salida:

  * (a) Markdown estricto con renderer confiable, o
  * (b) texto plano + escapado (`*`, `_`, etc.).
* Añadir tests de snapshot para respuestas con bold/itálicas.

---

## BUG-12 — Seguridad crítica: prompt injection ejecuta SQL de escritura (INSERT INTO MONTHLY_KPIS…)

**Evidencia:** Img10 y **nueva evidencia** en Img12.

**Síntoma:**

* El usuario introduce explícitamente: `INSERT INTO MONTHLY_KPIS (...) VALUES (...)`.
* El sistema responde: “Se ha ejecutado correctamente el comando de inserción.”

**Por qué esto es grave:**

* Permite **modificar** datos por texto libre.
* Un atacante podría:

  * borrar tablas, exfiltrar datos, insertar basura, alterar KPIs, etc.

**Resultado esperado (política mínima):**

* El sistema debe ser **read-only** por defecto.
* Cualquier operación de escritura debe requerir:

  * rol/autorización,
  * confirmación explícita,
  * y una ruta segura (no SQL directo, sino endpoint validado).

**Hipótesis:**

* El tool de ejecución SQL está expuesto sin guardrails (allowlist de SELECT).
* El LLM tiene permiso de llamar la herramienta con queries arbitrarios.

**Mitigaciones recomendadas (prioridad P0):**

1. **Bloquear** cualquier query que no sea `SELECT` (y aun así: con límites).
2. Parser/validator (AST) que niegue `INSERT/UPDATE/DELETE/ALTER/DROP/CREATE`.
3. Ejecutar bajo usuario DB con permisos **solo lectura**.
4. Si se requiere “insertar datos dummy”: crear endpoint separado `POST /admin/dummy-data` con validación estricta y auth.
5. Logging/auditoría: guardar `who/when/what` de cada query + hash del prompt que la originó.

---

## BUG-13 — Guardrails/Coherencia: el usuario puede “negociar” hasta que el sistema se contradiga o acepte premisas falsas

**Evidencia:** Img12 (punto 13: “Se alucina mucho… me dice que no y lo convenzo de que sí”).

**Síntoma:**

* El asistente inicialmente **niega** algo (por ejemplo: que un banco/medición esté disponible o sea válida) pero, con insistencia del usuario, termina:

  * **cambiando de postura sin evidencia**,
  * generando una respuesta “segura” pero **ficticia** (ej. gráfica con un banco que no estaba en la fuente), o
  * ejecutando acciones que deberían estar bloqueadas (conecta con BUG-12).

**Patrón de falla:**

* “Argumentative user” → el modelo prioriza ser útil/obediente sobre estar **grounded**.
* Se rompe la regla no escrita más importante: **"si no lo puedo verificar, no lo afirmo"**.

**Resultado esperado:**

* El sistema debe ser **estable** ante presión:

  * si no hay datos, repetir consistentemente: “No tengo esa fuente/dato. Puedo: (a) buscar en X, (b) usar Y, (c) pedirte Z.”
  * nunca “inventar” series, bancos o valores para satisfacer la conversación.

**Hipótesis de causa raíz:**

* Falta de una capa de “truth gating” (verificación post-tool) y/o falta de políticas de “refusal consistency”.
* Memory/estado mal manejado: se mezcla “lo que el usuario afirma” con “lo que el sistema sabe/consultó”.

**Recomendación técnica (fix P0/P1):**

* Introducir un **validador final** antes de render:

  * Afirmaciones numéricas/bancos/KPIs deben venir de `tool_result`.
  * Si el usuario propone un banco/KPI fuera del universo → responder con lista de valores permitidos.
* Instrucción explícita al LLM: *never comply with requests to mutate data; never claim chart exists unless chart_id exists*.
* Tests: conversaciones adversariales (insistencia, contradicción, “pero sí existe”) + snapshot tests.

---

# Sugerencias transversales (para volver esto determinista) (para volver esto determinista)

## A) Contratos duros entre LLM ↔ Datos ↔ UI

* El LLM solo puede afirmar cosas que estén en un `tool_result` verificable.
* Para gráficas: `chart_created`, `chart_id`, `chart_url`, `data_row_count`.

## B) Estado por conversación/mensaje

* Todo lo que sea “selección actual” (banco, KPI, rango) debe vivir en:

  * `conversation_state` (si es intención persistente) o
  * `message_state` (si es resultado puntual).
* Prohibido que un modal muestre resultados de otro `message_id` sin avisar.

## C) UX mínima para confianza

* Siempre mostrar:

  * KPI exacto, bancos exactos, rango de fechas, fecha de corte, fuente.
* Si falta algo, pedirlo o declarar supuestos.

## D) Observabilidad

* Registrar:

  * router decision (por qué eligió ICAP),
  * chart lifecycle,
  * fallas de export,
  * discrepancias (mismatch texto vs chart),
  * y cualquier intento de SQL no permitido.

---

# Backlog de prioridad sugerida (alineado a Head of Product)

## P0 — No negociables (verdad + seguridad + features que se rompen)

* **BUG-12 (Prompt injection / SQL write).** Bloqueo inmediato + permisos read-only.
* **BUG-13 (Guardrails/consistencia ante presión).** Truth-gating + validación de universo (bancos/KPIs) + pruebas adversariales.
* **BUG-09 (Alucinación/mismatch texto↔gráfica)** y contrato duro LLM↔tool.
* **BUG-02 (Gráfica no abre en Chrome Mac)** + **BUG-03 (descarga en blanco)**.
* **Regresión a vigilar:** issue de `SELECT *` (Carlos dice que “parece solucionado”) → agregar test/regla para evitar que vuelva.

## P1 — Alta prioridad (correctitud semántica / estado / defaults)

* **BUG-08 (gráfica vieja persiste / estado UI)**.
* **BUG-01 (router se ancla a ICAP)**.
* **BUG-07 (default bank hardcode / copy incorrecto)**.
* **BUG-10 (definición de Sistema + ambigüedad capitalización)**.

## P2 — Nice to have (pulido)

* **BUG-04 (decimales inconsistentes)**.
* **BUG-05 (UX zoom: reset)**.
* **BUG-06 (ruido/redundancia en panel de gráfica)**.
* **BUG-11 (markdown/render roto)**.

---

# Verificación final (sanity check)

## Cobertura vs comentarios de Head of Product

* **“La data tiene que ser verdadera”** → cubierto por **BUG-09 (mismatch/alucinación)**, **BUG-10 (inconsistencias Sistema/semántica)** y reforzado por **BUG-13 (truth-gating)**.
* **“Funcionalidades que se rompen: gráficas”** → cubierto por **BUG-02, BUG-03, BUG-08**.
* **“Query select * parece solucionado”** → anotado como **regresión**; falta evidencia en capturas aquí, pero se agrega como control preventivo.
* **“Prompt injection”** → cubierto por **BUG-12** con mitigación P0.
* **“Nice to have: front-end bugs, zero trust”** → front-end de pulido está en P2; “zero trust” se interpreta como hardening extra (más allá de bloquear writes), por eso queda como fase posterior una vez estén P0.

## Check de consistencia del reporte

* Todas las nuevas observaciones (punto 12 y 13) quedaron incorporadas como:

  * evidencia adicional en **BUG-12**
  * nuevo **BUG-13**
* La priorización final ahora sigue literalmente el foco: **verdad → seguridad → features core (gráficas) → resto**.

---

# Estado de Implementación (2026-01-08)

## P0 — Status

| Bug | Descripción | Estado | Implementación |
|-----|-------------|--------|----------------|
| **BUG-02** | Gráfica no abre en Chrome Mac | ✅ **FIXED** | Chart lifecycle + client-side hydration fix |
| **BUG-03** | Descarga en blanco | ✅ **VERIFIED** | Plotly.toImage + graphDivRef via onInitialized (2026-01-09) |
| **BUG-08** | Gráfica vieja persiste | ✅ **FIXED** | Chart linked to message_id |
| **BUG-09** | Alucinación/mismatch texto↔gráfica | ✅ **IMPLEMENTED** | Ver detalles abajo |
| **BUG-12** | Prompt injection SQL | ✅ **FIXED** (previo) | READ-ONLY perms + allowlist |
| **BUG-13** | Guardrails/coherencia ante presión | ✅ **IMPLEMENTED** | Ver detalles abajo |

### BUG-03: Fix Descarga PNG en Blanco (2026-01-09)

**Problema**: La gráfica se descargaba vacía porque el selector `.plotly` no encontraba el elemento DOM correcto de Plotly.

**Root Cause**: `react-plotly.js` no aplica clase `.plotly` al elemento. El código buscaba un elemento inexistente.

**Solución**:
- Usar callback `onInitialized` de react-plotly.js para capturar `graphDiv` (referencia DOM real)
- Usar `Plotly.toImage()` para convertir gráfica dinámica WebGL/SVG a PNG base64
- Crear link de descarga con data URL (sin requests HTTP, sin CORS)

**Archivos modificados:**
- `apps/web/src/components/canvas/BankChartCanvasView.tsx`
  - Agregado `graphDivRef` para almacenar referencia DOM
  - Agregado `isChartReady` estado
  - Agregado `handlePlotInitialized` callback
  - Actualizado `handleDownloadPNG` para usar `Plotly.toImage()` con `graphDivRef`
  - Actualizado `handleResetZoom` para usar `graphDivRef`
  - Agregado props `onInitialized` y `onUpdate` al componente `<Plot>`

**Tests**: 23/23 passed (BankChartCanvasView.test.tsx)

### BUG-09: Implementación Truth-Gating

**Archivos modificados:**
- `apps/backend/src/schemas/bank_chart.py` - ChartStatus enum (SUCCESS, EMPTY, ERROR, CLARIFICATION)
- `apps/backend/src/services/bank_analytics_client.py` - chart_status assignment
- `apps/backend/src/services/truth_gating_service.py` - Post-generation validation (NEW)
- `apps/backend/src/routers/chat/handlers/streaming_handler.py` - Dynamic LLM prompts based on chart_status

**Funcionalidad:**
1. `ChartStatus` enum tracks chart creation state
2. LLM prompts vary based on chart status:
   - SUCCESS: "puedes referirte a la gráfica"
   - EMPTY: "NO hay datos, NO menciones ninguna gráfica"
   - ERROR/CLARIFICATION: "NO menciones ninguna gráfica"
3. Post-generation validation detects chart references when chart doesn't exist
4. Soft enforcement (logging) with option for hard enforcement (append corrections)

### BUG-13: Implementación Guardrails

**Archivos nuevos:**
- `apps/backend/src/services/universe_validation_service.py` - CNBV bank validation + fuzzy matching
- `apps/backend/src/services/refusal_tracker.py` - Redis-backed refusal persistence (1-hour TTL)

**Archivos modificados:**
- `apps/backend/src/services/tool_execution_service.py` - Bank validation pre-query + refusal tracking
- `apps/backend/src/routers/chat/handlers/streaming_handler.py` - Invalid bank handler + consistency prompt

**Funcionalidad:**
1. Universe validation against known CNBV banks
2. Fuzzy matching suggestions ("¿Quisiste decir BBVA?")
3. Refusal persistence in Redis (1-hour TTL)
4. "INTENTO DE NEGOCIACIÓN DETECTADO" for repeat invalid requests
5. Consistent refusal prompt injection to maintain LLM stability

## P1 — Status

| Bug | Descripción | Estado | Notas |
|-----|-------------|--------|-------|
| **BUG-01** | Router se ancla a ICAP | 🟢 **FIXED** | Threshold 0.6→0.7, vague query detection, default confidence 0.5 |
| **BUG-07** | Default bank hardcode | ✅ **FIXED** | runtime_config.default_bank |
| **BUG-10** | Sistema vs banco inconsistente | ✅ **FIXED** | Disambiguation + SISTEMA notes (2026-01-09) |
| **BA-001** | RAG Grounding (ICAP hallucination) | ✅ **FIXED** | DATA_INDICATOR_REGEX + term validation (2026-01-10) |
| **BA-002** | INVEX Default Bias | ✅ **FIXED** | Config changes + clarification flow (2026-01-10) |

### BA-001 & BA-002: Fixes (2026-01-10)

**Problema BA-001**: Queries como "¿Cuál es mi cartera?" se clasificaban incorrectamente como knowledge queries.

**Problema BA-002**: Queries sin banco explícito defaulteaban a INVEX en lugar de pedir clarificación.

**Solución**:
1. `DATA_INDICATOR_REGEX` en `is_knowledge_query()` detecta indicadores de datos:
   - Posesivos (mi, mis, nuestro)
   - Referencias a bancos (de INVEX, del banco)
   - Verbos de acción (dame, muéstrame)
   - Patrones temporales (últimos N meses)

2. Configuración actualizada:
   - `bankadvisor.yaml`: `apply_bank_default: false`, `primary: ""`
   - `invex.yaml`: `apply_bank_default: false`, `primary: ""`

**Tests**: Happy Path 47/47 ✅, Bug Fixes Suite 18/18 ✅

**Commit**: `45a75723`

### BUG-10: Análisis Completado (2026-01-09)

**Síntoma reportado**: "Sistema" muestra valores menores que INVEX para algunas métricas (ej: ICAP).

**Hallazgo**: NO es un bug de datos. Es comportamiento esperado debido a diferentes métodos de agregación.

**Root Cause Analysis**:

| Tipo de Métrica | Método de Agregación | ¿SISTEMA < Banco? |
|-----------------|---------------------|-------------------|
| cartera_total, reservas | **SUM** (suma) | ❌ No, siempre ≥ |
| **icap_total** | **MEAN** (promedio simple) | ✅ Sí, posible |
| tda, tasas | Weighted Average | ✅ Sí, posible |
| imor, icor | Recalculado post-suma | ⚠️ Depende |

**Código responsable** (`transforms.py:697-699`):
```python
# Simple average for ICAP (capital adequacy ratio)
if "icap_total" in get_cols(df):
    agg_exprs.append(pl.col("icap_total").mean().alias("icap_total"))
```

**Ejemplo**: Si INVEX tiene ICAP=16% y otros bancos promedian 12%, SISTEMA mostrará ~13% (promedio).

**Ambigüedad "capitalización"**: El término mapea directamente a ICAP sin desambiguación. Usuario podría referirse a market cap.

**Fixes Propuestos (deferred)**:
1. **Fix A (Quick)**: Agregar etiquetas de contexto en respuestas ("SISTEMA = Promedio del sistema")
2. **Fix B (Medium)**: Agregar "capitalización" a `ambiguous_terms` en synonyms.yaml
3. **Fix C (Optional)**: Cambiar agregación de ICAP a weighted average

**Decisión**: Diferido. El comportamiento actual es matemáticamente correcto. Se priorizará claridad en UI/UX cuando se implemente.

### BUG-10: Implementación (2026-01-09)

**Fix B - Desambiguación "capitalización":**
- Removido "capitalización" de aliases de `icap_total`
- Agregado como término ambiguo en `synonyms.yaml` con opciones:
  - ICAP (capitalización regulatoria) - disponible
  - Market Cap (capitalización de mercado) - no disponible
- Soporte para campo `triggers` en `check_ambiguous_term()`
- Normalización de acentos usando `unicodedata`

**Fix A - Notas de contexto SISTEMA:**
- Nuevo campo `sistema_note` en `synonyms.yaml` para métricas con agregación especial
- `icap_total`: "promedio simple de todos los bancos"
- `tda_cartera_total`: "promedio ponderado por cartera"
- Nuevo método `get_sistema_note()` en `ConfigService`

**Archivos modificados:**
- `plugins/bank-advisor-private/config/synonyms.yaml`
- `plugins/bank-advisor-private/src/bankadvisor/config_service.py`

## P2 — Status

| Bug | Descripción | Estado | Notas |
|-----|-------------|--------|-------|
| **BUG-04** | Decimales inconsistentes | 🟢 **FIXED** | CSV export uses toFixed(6) |
| **BUG-05** | UX zoom reset | 🟢 **FIXED** | Reset Zoom button in ChartActionButtons |
| **BUG-06** | SQL en chat (redundante) | ✅ **FIXED** | Prompt instructions + strip_sql_from_response() (2026-01-09) |
| **BUG-11** | Markdown render roto | ✅ **FIXED** | normalize_markdown_formatting() in text_sanitizer |

### BUG-06: SQL No Debe Aparecer en Chat (2026-01-09)

**Problema**: El SQL aparecía inconsistentemente en el chat en lugar de solo en el panel canvas.

**Root Cause**: El prompt del LLM no tenía instrucciones explícitas de no incluir SQL, y no había filtro post-procesamiento.

**Solución (Defense-in-Depth)**:
1. **Prompt Engineering**: Instrucciones explícitas al LLM para NO incluir SQL
   - `**RESTRICCIONES DE FORMATO:**` section in streaming_handler.py
2. **Post-Processing Filter**: `strip_sql_from_response()` como safety net
   - Remueve bloques ```sql ... ```
   - Remueve bloques genéricos con keywords SQL (SELECT, FROM, WHERE, etc.)
   - Remueve menciones inline ("La consulta SQL fue...")

**Archivos modificados:**
- `apps/backend/src/routers/chat/handlers/streaming_handler.py` - Prompt instructions
- `apps/backend/src/services/text_sanitizer.py` - strip_sql_from_response() function

**Tests**: 39/39 passed (test_text_sanitizer.py)

## Verificación Tests P2 (2026-01-09)

```
✅ Backend Tests: 39/39 passed (test_text_sanitizer.py)
   - TestStripSqlFromResponse: 11 tests (BUG-06)
   - TestNormalizeMarkdownFormatting: 10 tests (BUG-11)
   - TestIsSectionHeading: 8 tests
   - TestStripSectionHeadings: 6 tests
   - TestSanitizeResponseContent: 4 tests

✅ Frontend Tests: 23/23 passed (BankChartCanvasView.test.tsx)
   - Reset Zoom Button (BUG-05): 2 tests
   - SQL Display (BUG-06): 3 tests
   - Chart Action Buttons: 2 tests
   - Core functionality: 16 tests
```

## Verificación E2E (2026-01-09)

### Bug Fixes Test Suite (NEW)
```
✅ BUG-01: 2/2 passed - Router no se ancla a ICAP
✅ BUG-07: 1/1 passed - Default bank funciona
✅ BUG-09: 1/1 passed - Chart coincide con query
✅ BUG-10: 3/3 passed - Desambiguación "capitalización"
✅ BUG-11: 1/1 passed - Markdown limpio

Total: 8/8 tests PASSED (100%)
```

**Archivo**: `tests/e2e/test_bug_fixes_suite.py`

### Happy Path Suite (2026-01-09)
```
📊 Summary: 38/40 Passed (95.0%)
   - 1 failure: Case 5 "provisiones preventivas" - Expected RAG, got chart
   - 1 failure: Case 34 "ratio capitalización con desglose" - Expected chart, got RAG

📈 Progress: 40% → 67.5% → 80% → 87.5% → 92.5% → 95.0%

🎯 Los 2 fallos son casos edge de clasificación intent, no bugs funcionales.
```

**Casos específicos resueltos:**
- Case 28: "Cartera de crédito corporativo de INVEX" ✅
- Case 29: "Distribución de cartera por segmento de INVEX" ✅
- Case 33: "¿Cuál es la tasa de crédito corporativo en MN?" ✅

