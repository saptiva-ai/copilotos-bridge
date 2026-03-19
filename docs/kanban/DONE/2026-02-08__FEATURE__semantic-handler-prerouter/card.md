---
id: 2026-02-08__FEATURE__semantic-handler-prerouter
title: Semantic Handler Pre-Router using Embedding Service
status: DONE
type: FEATURE
priority: P2 - Medium
---

# FEATURE: Semantic Handler Pre-Router

**Prioridad**: P2 - Medium
**Fecha**: 2026-02-08
**Status**: BACKLOG

## Descripcion

Reemplazar el keyword-based handler matching en el QueryRouter del plugin
bank-advisor con un semantic pre-router basado en embeddings. Esto resuelve
de forma general el problema de handler priority collisions (como BUG-CH-006)
donde keywords greedy capturan queries para el handler equivocado.

## Motivacion

El pattern actual usa `matches()` con listas de keywords hardcodeados en cada
handler (13 handlers). Esto causa:
1. **Colisiones de prioridad**: `ViviendaPerfilHandler` captura "cartera
   hipotecaria por banco" antes que `InstitutionRankingHandler`
2. **Mantenimiento fragil**: cada bug requiere agregar keywords/guards manuales
3. **No generaliza**: typos, sinónimos, y variaciones semánticas no se detectan

## Arquitectura Propuesta

### Opcion A: Semantic Pre-Router en Backend (recomendada)

Antes de llamar al plugin, el backend clasifica la query contra exemplars
por handler usando el `SemanticIntentScorer` existente:

```
User Query
    → Backend: SemanticHandlerScorer.score(query)
    → Resultado: {handler: "institution_ranking", confidence: 0.85}
    → Pasar hint al plugin como parámetro
    → Plugin: QueryRouter usa hint para priorizar handler
```

### Infraestructura Existente (reutilizable)

| Componente | Estado |
|---|---|
| EmbeddingService plugin (MiniLM-L12-v2, 384 dim) | Desplegado en PROD |
| Backend EmbeddingService client (gRPC + HTTP) | Operativo |
| SemanticIntentScorer (exemplar-based classification) | Usado en 3 puntos del pipeline |
| table_mode_semantic (mismo patron) | Operativo |

### Estimación

- Esfuerzo: 2-3 días
- Riesgo: Bajo (aditivo, no reemplaza — hint opcional)
- Dependencias: Ninguna nueva

## Criterios de Aceptación

- [ ] `SemanticHandlerScorer` con exemplars para 13 handlers
- [ ] Hint de handler pasado al plugin como parámetro opcional
- [ ] QueryRouter usa hint cuando confidence > threshold
- [ ] Fallback a keyword matching cuando hint ausente o bajo confidence
- [ ] Tests unitarios con queries ambiguas (como "cartera hipotecaria por banco")
- [ ] Latencia < 5ms adicionales (embeddings cacheados)

## Origen

Descubierto durante investigación de BUG-CH-006 (cartera-por-banco-por-ano).
Ver `docs/kanban/DOING/2026-01-20__BUG__cartera-por-banco-por-ano/research.md`
sección 6 para análisis completo.
