---
id: "REFACTOR-2026-02-18__qdrant-to-weaviate-cleanup"
title: "Limpiar referencias legacy a Qdrant y completar migracion a Weaviate Cloud"
status: "DONE"
phase: "Research"
priority: "P1"
scope_in:
  - "P0: Evaluar y eliminar workaround non-streaming en message_endpoints.py (lineas 82-89)"
  - "P1: Renombrar campo 'qdrant' a 'weaviate' en resources.py endpoint y ResourceMetrics schema"
  - "P1: Actualizar resource_lifecycle_manager.py enum QDRANT_VECTORS → WEAVIATE_VECTORS"
  - "P2: Eliminar qdrant_service_deprecated.py (codigo muerto, no importado)"
  - "P2: Eliminar qdrant-client de requirements.txt y requirements-runtime.txt"
  - "P3: Actualizar docstrings y comentarios que referencian Qdrant en codigo activo"
  - "Verificar que resource_cleanup_worker.py llame WeaviateService.cleanup_expired_sessions()"
scope_out:
  - "Renombrar colecciones existentes en Weaviate Cloud (RAG_Documents, Ontology_Term)"
  - "Cambiar schema de colecciones Weaviate (strict schema, requiere recrear)"
  - "Migracion de datos entre colecciones"
  - "Cambios funcionales en el pipeline RAG (ya funciona con Weaviate)"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - "python3.11 -m pytest apps/backend/tests/unit -q --maxfail=3"
  - "python3.11 -m pytest apps/backend/tests/integration -q --maxfail=3"
  - "PYTHONDONTWRITEBYTECODE=1 python3.11 -c \"import ast; [ast.parse(open(f).read()) for f in __import__('glob').glob('apps/backend/src/**/*.py', recursive=True)]; print('All files compile OK')\""
  - "cd apps/web && pnpm test"
pr_files: []
test_status: "research-only"
---

# Summary
- Objective: Completar la limpieza de referencias legacy a Qdrant tras la migracion al pipeline Weaviate Cloud que ya esta operativo.
- Constraint: No tocar colecciones existentes en Weaviate Cloud (`RAG_Documents`, `Ontology_Term`). No romper el flujo RAG de documentos que ya funciona.

# Contexto

La migracion del data path principal ya esta completa (~90%):

```
GetRelevantSegmentsTool
  -> AdaptiveRetrievalOrchestrator
    -> SemanticSearchStrategy
      -> WeaviateService  (weaviate_service.py)
```

Weaviate Cloud maneja 2 colecciones:
1. **`RAG_Documents`** - chunks de documentos de usuario (env var: `RAG_COLLECTION_NAME`)
2. **`Ontology_Term`** - ontologia bancaria (hardcoded en `_augment_query()` y `resolve_ambiguous_term()`)

Sin embargo, quedan ~10 referencias activas a Qdrant en codigo, docstrings, enums y un endpoint de API publica.

# Inventario de referencias legacy

| Archivo | Tipo | Impacto |
|---------|------|---------|
| `services/qdrant_service_deprecated.py` | Codigo muerto (620 lineas) | Bajo - no importado |
| `routers/resources.py:32,76,86,98-103` | Endpoint API devuelve campo `qdrant` | Medio - API publica |
| `services/resource_lifecycle_manager.py` | Enum `QDRANT_VECTORS`, docstring | Medio - metricas rotas |
| `workers/resource_cleanup_worker.py` | Docstring "Qdrant old sessions" | Bajo - solo comentario |
| `routers/chat/endpoints/message_endpoints.py:82,89` | Workaround "until Qdrant indexing..." | **Alto** - degrada UX |
| `services/streaming/document_context.py` | Log referencia "Qdrant" | Bajo - solo log |
| `services/retrieval/semantic_search_strategy.py:12` | Docstring dice "Qdrant" | Bajo - ya usa Weaviate |
| `requirements.txt` / `requirements-runtime.txt` | `qdrant-client` como dependencia | Bajo - peso muerto |

# Problema principal: Workaround non-streaming (P0)

`message_endpoints.py:79-92` fuerza **non-streaming cuando hay documentos adjuntos**:

```python
# WORKAROUND: Force non-streaming when documents are attached
# until Qdrant indexing is fully operational for streaming RAG
```

Weaviate ya esta operativo. `DocumentContextBuilder` funciona en streaming path via `streaming_handler.py`. Este workaround probablemente **degrada la experiencia de usuario** al forzar respuestas no-streaming para queries con documentos, negando la UX de typing progresivo.

**Investigar**: Verificar si el streaming path con docs funciona end-to-end antes de eliminar el workaround.

# Fases propuestas

## P0 - Eliminar workaround non-streaming
- Evaluar si streaming + docs funciona E2E (manual test con PDF)
- Si funciona: eliminar lineas 79-92 de `message_endpoints.py`
- Si no: documentar por que y convertir en TODO con fecha

## P1 - Renombrar qdrant → weaviate en API publica
- `resources.py`: campo `qdrant` → `weaviate` en response schema
- `resource_lifecycle_manager.py`: enum `QDRANT_VECTORS` → `WEAVIATE_VECTORS`
- `resource_cleanup_worker.py`: actualizar referencia al cleanup method

## P2 - Eliminar codigo muerto
- Borrar `qdrant_service_deprecated.py`
- Remover `qdrant-client` de requirements (verificar que no hay import transitivo)
- Remover tests legacy en `tests_legacy/integration/test_qdrant_integration.py`

## P3 - Actualizar docstrings
- `semantic_search_strategy.py:12` - "Qdrant" → "Weaviate"
- `document_context.py` - log "Qdrant" → "Weaviate"
- `message_endpoints.py` - cualquier comentario residual

# Criterios de aceptacion
- [ ] Streaming funciona con documentos adjuntos (o workaround documentado con justificacion)
- [ ] Endpoint `/resources` retorna campo `weaviate` en lugar de `qdrant`
- [ ] `grep -r "qdrant" apps/backend/src/` retorna 0 matches (excluyendo deprecated)
- [ ] `qdrant_service_deprecated.py` eliminado
- [ ] `qdrant-client` removido de requirements
- [ ] Tests existentes siguen pasando sin regresion

# Updates
- 2026-02-18 - Ticket creado con inventario completo de referencias legacy y plan de limpieza por fases.
