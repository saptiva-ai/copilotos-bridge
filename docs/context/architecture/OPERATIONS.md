# Arquitectura: SLAs y Observabilidad

> **Cuándo leer**: Para entender latencia, métricas de trust y monitoreo.

## SLAs de Latencia

> El BRD define TTI (Time-To-Insight) < 5s como meta.

### Objetivos por Intent

| Intent | p50 | p95 | Timeout |
|--------|-----|-----|---------|
| `BANK_KNOWLEDGE` | 800ms | 2s | 5s |
| `SQL_QUERY` (simple) | 1.5s | 4s | 15s |
| `SQL_QUERY` (agregación) | 3s | 8s | 30s |
| `VISUALIZATION` | 2s | 5s | 15s |
| `SQL_QUERY + VIZ` (combo) | 4s | 10s | 45s |

### Estrategias de Optimización

| Intent | Estrategia |
|--------|------------|
| `BANK_KNOWLEDGE` | Cache en Weaviate con TTL 24h para términos frecuentes |
| `SQL_QUERY` | Vistas materializadas para agregaciones comunes |
| `VISUALIZATION` | Generación de chart config en paralelo con fetch |
| Fallback | Si p95 > target → respuesta parcial + "cargando más" |

---

## Métricas de Trust

> Gap crítico del BRD: "tasa de respuestas con trazabilidad completa, incidentes de alucinación".

### Métricas de Confiabilidad

| Métrica | Target v1.2 | Cálculo |
|---------|-------------|---------|
| `grounding_rate` | ≥ 95% | Queries con source_refs válidas / Total |
| `abstention_rate` | ≤ 15% | Queries con clarificación / Total |
| `validation_success` | ≥ 90% | QuerySpecs válidos / Total generados |
| `hallucination_rate` | ≤ 2% | Respuestas con columnas inventadas / Total |
| `avg_confidence` | ≥ 0.85 | Promedio de confidence en QuerySpecs |

### Métricas de Feedback

| Métrica | Target v1.2 | Fuente |
|---------|-------------|--------|
| `thumbs_up_rate` | ≥ 80% | 👍 / (👍 + 👎) |
| `feedback_coverage` | ≥ 30% | Mensajes con feedback / Total |
| `negative_resolved` | Tracking | 👎 con corrección posterior |

---

## Logging Estructurado

Cada query genera:

```json
{
  "trace_id": "uuid",
  "timestamp": "2025-01-10T14:30:00Z",
  "user_id": "user_abc",
  "organization_id": "org_xyz",
  "intent": "SQL_QUERY",
  "query_text": "Dame IMOR de INVEX",
  "queryspec_confidence": 0.92,
  "validation_passed": true,
  "sql_fingerprint": "sha256:abc123",
  "data_as_of_date": "2024-12-31",
  "latency_ms": 2340,
  "result_row_count": 12,
  "source_refs": ["ontology:term_imor", "table:monthly_kpis"],
  "user_feedback": null
}
```

---

## Dashboard de Observabilidad (v1.2 Mínimo)

### Paneles Requeridos

| Panel | Descripción | Alertas |
|-------|-------------|---------|
| Queries por intent | Distribución KNOWLEDGE / SQL / VIZ | - |
| Latencia p50/p95 | Por intent | Si > target |
| Abstention rate | Tendencia diaria | Si > 15% |
| Feedback rate | 👍 vs 👎 por día | Si 👎 > 20% |
| Top queries fallidas | Para priorizar mejoras | - |

### Alertas Críticas

| Condición | Acción |
|-----------|--------|
| p95 > 2x target | Escalar a infra |
| hallucination_rate > 5% | Revisar ontología |
| validation_success < 80% | Revisar few-shot examples |
| abstention_rate > 25% | Mejorar cobertura de términos |

---

## Trazabilidad de Respuestas

Cada respuesta al usuario incluye:

```json
{
  "answer": "El IMOR de INVEX en diciembre 2024 fue 2.3%",
  "traceability": {
    "data_as_of_date": "2024-12-31",
    "source_refs": [
      "ontology:term_imor#definition",
      "table:monthly_kpis#imor"
    ],
    "calculation_method": "direct_column",
    "data_freshness_hours": 24
  }
}
```

> **Alineación BRD**: "definición oficial con fuente/tabla/fecha de corte"

---

## Monitoreo de Salud

### Endpoints de Health

| Servicio | Endpoint | Frecuencia |
|----------|----------|------------|
| Backend | `/api/health` | 30s |
| Bank Advisor | `/health` | 30s |
| Weaviate | `/v1/.well-known/ready` | 30s |
| PostgreSQL | Connection pool | 60s |

### Métricas de Infraestructura

| Métrica | Umbral |
|---------|--------|
| CPU Backend | < 80% |
| Memoria Backend | < 85% |
| Conexiones PostgreSQL | < 80% pool |
| Latencia Weaviate | < 100ms |

---

## Debugging

### Trace ID Flow

```
Frontend → X-Request-ID: uuid
    │
    ▼
Backend → trace_id en logs
    │
    ▼
Bank Advisor → mismo trace_id
    │
    ▼
PostgreSQL → query comment con trace_id
```

### Query de Debug

```sql
-- Buscar query por trace_id
SELECT * FROM query_logs
WHERE trace_id = 'uuid-xxx';
```

---

**Versión**: 1.2.1 | **Fuente**: `docs/tex/Arquitectura.tex` secciones 10, 11
