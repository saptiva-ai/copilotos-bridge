# Informe técnico – BankAdvisor (RAG/ICAP/INVEX)

## BUG-01: Definición/truncado de glosario
- Repro:
  1) Mensaje: “¿Qué es un fideicomiso?” sin mencionar bancos/series.
  2) Observar SSE: se dispara bank_analytics (chart/knowledge) y la respuesta llega como “Fideicomiso de Contragarantía…” cortada.
- Evidencia raíz:
  - `apps/backend/src/services/bank_analytics_client.py:595+` `is_bank_query` incluye patrones genéricos (“qué/que”, “indicador”) sin exigir banco/métrica → clasifica como bancario. Los high-confidence keywords incluyen “qué” por estar dentro de `query_patterns`.
  - `apps/backend/src/routers/chat/handlers/streaming_handler.py:2315+` fast-path knowledge usa `response_text` sin validar término ni fallback de RAG; no revisa que el término consultado esté en el chunk ni que el chunk esté completo.
  - `apps/backend/src/services/embedding_service.py:113-140` chunking 500 tokens / 100 overlap → puede cortar frases; no hay “sentence boundary” ni re-ensamblado para knowledge.
  - No hay verificación UI de truncado: `apps/web/src/components/chat/ChatMessage.tsx` y `BankChartMessage.tsx` renderizan markdown tal cual; el recorte se origina en backend, no en overflow CSS.
- Fix propuesto (MVP):
  - Endurecer `is_bank_query`: quitar patrón genérico `qué/que`; requerir token de banco/métrica/regulador.
  - En `invoke_bank_analytics`/`is_bank_query`, si patrón de definición (`que es|qué es|significado|definición`) y sin banco/métrica → return False.
  - En fast-path knowledge: validar que el chunk contenga el término; si no, reintentar con `DocumentContextBuilder` o pedir más segmentos antes de emitir.
  - Opcional: subir overlap a 150–200 tokens o cortar por oración para respuestas de glosario.
- Riesgos: Menor recall en queries ambiguas; mitigable con tests.

## BUG-02: ICAP + gráfica por defecto
- Repro:
  1) Mensaje conceptual: “Define fondeo bancario” o “¿Qué es un fideicomiso?”.
  2) Se abre panel de gráfica/ICAP aunque no se pidió serie temporal.
- Evidencia raíz:
  - `is_bank_query` heurística amplia (palabras “qué”, “indicador”) → siempre True.
  - `invoke_bank_analytics` se llama antes de saber intención de serie; no filtra por términos de tiempo/serie.
  - `apps/backend/src/services/tools.py` habilita `bank_analytics` por defecto para Saptiva (`normalized["bank_analytics"] = True`), por lo que el router siempre lo tiene disponible.
  - En streaming: `apps/backend/src/routers/chat/handlers/streaming_handler.py:355+` invoca `invoke_bank_analytics` incluso antes de detectar clarificaciones/documentos → cualquier True de `is_bank_query` termina en `ChartFlowHandler`.
- Fix propuesto:
  - En `is_bank_query`: exigir banco/métrica/keyword de serie; eliminar “qué” genérico.
  - En `invoke_bank_analytics`: guard clause si no hay métrica/banco ni términos de serie (`gráfica|grafica|serie|evolución|histórico|últimos N meses`) → no invocar tool y dejar respuesta textual.
  - UI (opcional): mostrar botón “Mostrar gráfica” solo si llega un `bank_chart`.
- Riesgos: Alguna consulta de métrica muy corta podría no disparar; cubrir con tests.

## BUG-03: Typos acrónimos (CNVB) sin fuzzy ni glosario en contexto
- Repro:
  1) Mensaje: “CNVB?”.
  2) Devuelve “CNVB” inventado o clarificación pobre, sin sugerir CNBV ni glosario.
- Evidencia raíz:
  - No hay normalización de acrónimos antes de bank_analytics; `is_bank_query` no corrige.
  - Sin índice corto de glosario en contexto; knowledge path depende de lo que regrese MCP.
  - El validador de bancos (`UniverseValidationService`) está, pero no se usa para siglas de reguladores/entidades (CNBV) ni para acrónimos de términos: solo para bancos.
- Fix propuesto:
  - Añadir normalización de acrónimos cortos (`cnvb`→`cnbv`) y Levenshtein<=1 sobre lista de siglas conocidas antes de `is_bank_query` y `invoke_bank_analytics`.
  - Si la query es solo sigla/definición, saltar a flujo “knowledge” (glosario) y no a chart.
  - Construir “glossary memory” (término→definición corta + fuente) y adjuntarlo al prompt para siglas conocidas.
- Riesgos: Sobre-corrección; limitar a 3–6 chars y similitud alta.

## BUG-04: Plantilla “usando ICAP para INVEX/HSBC”
- Repro:
  1) Preguntas bancarias genéricas devuelven texto con “ICAP para INVEX/HSBC” aunque no se solicitó.
- Evidencia raíz:
  - Prompts con ejemplos fijos “IMOR de INVEX…” (`apps/backend/prompts/registry.yaml`).
  - `is_bank_query` usa pronombres posesivos como indicio de INVEX (`apps/backend/src/services/bank_analytics_client.py:1180+`).
  - `_build_generic_bank_clarification` (en `tool_execution_service.py`) ofrece siempre métricas IMOR/ICOR/ICAP → empuja ICAP.
  - Inyección de `context_banks` en `invoke_bank_analytics` desde mensajes previos aunque la nueva consulta no lo pida.
  - `apps/backend/src/services/universe_validation_service.py` lista bancos con INVEX primero; si esa lista se inyecta sin orden controlado, refuerza INVEX en prompts.
- Fix propuesto:
  - Remover heurística “possessive ⇒ INVEX”; inyectar bancos solo si usuario los dijo.
  - No añadir `context_banks` para consultas conceptuales; limpiar al detectar definición.
  - Cambiar ejemplos de prompt a placeholders neutrales.
  - Diversificar clarificación: no sesgar a ICAP, pedir primero si quiere definición vs métrica.
- Riesgos: Menos auto-completado en follow-ups; mitigable con memoria explícita cuando el usuario sí mencionó banco.

## BUG-05: Selector de banco solo INVEX/Sistema
- Repro:
  1) Clarificación por falta de banco muestra solo INVEX/Sistema.
- Evidencia raíz:
  - `_build_generic_bank_clarification` arma `banks` con detección regex limitada; no rellena con universo conocido.
  - MCP puede devolver enum corto.
- Fix propuesto:
  - Si detección <2 bancos, rellenar con `UniverseValidationService.get_valid_banks_list()` (o top-N) antes de enviar clarificación.
  - Incluir `available_banks` en payload para que frontend muestre catálogo más amplio.
  - Asegurar que MCP no recorte a INVEX/Sistema cuando no detecta banco.
- Riesgos: Lista larga en UI; limitar a top-N + búsqueda.

## Parches mínimos por archivo
- `apps/backend/src/services/bank_analytics_client.py:is_bank_query`: endurecer heurística (quitar “qué/que”, posesivos→INVEX).
- `apps/backend/src/services/bank_analytics_client.py`: añadir `_normalize_acronyms` para CNBV/CNVB y usarla antes de clasificación.
- `apps/backend/src/services/tool_execution_service.py`:
  - Normalizar acrónimos antes de invocar MCP.
  - Guard clause para queries conceptuales sin serie.
  - `_build_generic_bank_clarification`: rellenar bancos desde UniverseValidationService.
- `apps/backend/src/routers/chat/handlers/streaming_handler.py`: validar knowledge chunk contiene el término; fallback a RAG si no.
- `apps/backend/prompts/registry.yaml`: quitar ejemplos fijos INVEX/ICAP; usar placeholders.

## Quick checks
1) `is_bank_query("que es un fideicomiso?")` → False; `is_bank_query("ICAP de BBVA 2024")` → True.  
2) `invoke_bank_analytics("CNVB?")` → sugerir CNBV sin chart.  
3) E2E (mock MCP): “¿Qué es un fideicomiso?” → definición completa, sin eventos `bank_chart`.  
4) E2E: “Muéstrame el ICAP de BBVA 2024” → `bank_chart` correcto, sin contaminar banco en otra conversación.  
5) UI: clarificación muestra catálogo amplio de bancos; no aparece selector para preguntas conceptuales.

## Evidencia adicional y señales de riesgo
- Heurística actual de `is_bank_query` mezcla signos de pregunta generales y términos bancarios, lo que maximiza recall pero dispara falso positivo en definiciones. El costo es el sobre-enrutamiento a chart.
- `ChartFlowHandler` acepta `bank_chart_data` incluso cuando es `clarification` → el pipeline no se corta al detectar que solo hay aclaración.
- Universo de bancos (`UniverseValidationService.VALID_BANKS`) incluye muchos bancos; no exponerlos en clarificación es una decisión de UI/tool, no de datos.

## Sugerencias de logging para validar fixes
- En `is_bank_query`: log structured con `matched_keyword`, `category`, `message_preview` y `decision` (True/False) para auditar FP/FN.
- En `invoke_bank_analytics`: log `will_invoke` con flags `has_metric`, `has_bank`, `has_series_keyword`, `normalized_acronym`.
- En fast-path knowledge: log si `term_present_in_chunk` y el tamaño del chunk; si False, log fallback activado.
