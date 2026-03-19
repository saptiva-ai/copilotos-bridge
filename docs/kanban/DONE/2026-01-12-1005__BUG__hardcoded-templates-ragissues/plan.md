# Plan – Sugerencias dinámicas para clarificaciones (scoring)

## Objetivo
Reemplazar enums fijas en clarificaciones por sugerencias dinámicas basadas en contexto (mensaje, historial, universo de bancos/métricas), evitando hardcodes de INVEX/ICAP y reduciendo sobre-ruteo.

## Alcance
- Backend: scorer ligero que combine señales (historial, universo, fuzzy) y exponga `suggested_banks`, `suggested_metrics`, `related_queries`.
- Integración: clarificaciones (genéricas y del plugin) deben incluir el payload enriquecido sin romper compatibilidad.
- Frontend: (pendiente) mostrar sugerencias separadas de los selects actuales; permitir búsqueda libre con catálogo ampliado.

## Tareas
- [x] Crear módulo de sugerencias: `bank_suggestions.py` con:
  - Normalización de texto (lower + strip acentos).
  - Scoring simple: bancos = detecciones en mensaje + bancos históricos + “SISTEMA” + universo; métricas = detecciones + histórico + universo.
  - Related queries: combinaciones top2 bancos × top2 métricas × periodo (“últimos 3/12 meses”).
- [x] Integrar en `tool_execution_service`:
  - Normalizar siglas antes de MCP; guard clause para definiciones sin tokens bancarios.
  - Adjuntar `suggested_banks`, `suggested_metrics`, `related_queries` en clarificaciones y `available_banks` deducido del scorer (no enum fija).
- [x] Ajustar heurística de intent (`is_bank_query`):
  - Quitar patrón genérico “qué/que” y posesivos→INVEX; filtrar definiciones sin tokens bancarios; normalizar acrónimos (CNVB→CNBV).
- [x] Neutralizar prompts de ejemplos (“IMOR de INVEX” → neutral).
- [ ] Frontend: renderizar `related_queries` y `suggested_*` en clarificación (chips/botones) y permitir búsqueda libre sobre `available_banks`.
- [ ] Tests:
  - Unit scorer: dado historial BBVA/IMOR, sugerir BBVA/IMOR arriba; sin señales, top universo sin duplicados.
  - SSE: “qué es X” → sin bank_chart; “CNVB?” → sugiere CNBV/bancos top; “IMOR” sin banco → clarificación con catálogo amplio.

## Riesgos / mitigación
- Sobre-corrección de siglas: limitar fuzzy a siglas 3–6 chars y umbral ≤1; loggear normalizaciones.
- Ruido en sugerencias: limitar a top-5; si no hay señales, usar genéricas mínimas.
- Compatibilidad frontend: incluir nuevos campos sin eliminar los actuales; mantener `options` y `context`.

## Métricas / logging
- Logs estructurados: `suggestions.banks`, `suggestions.metrics`, `related_queries`, fuente de señal (mensaje/historial/universo).
- Métricas deseables (futuro): CTR de sugerencias, ratio de clarificación resuelta en primer intento.
