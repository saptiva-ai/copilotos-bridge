# Arquitectura: Modelo de Datos

> **Cuándo leer**: Para entender el schema de Weaviate, ETL ontológico y QuerySpec.

## Colecciones en Weaviate

| Colección | Tipo | Propósito | TTL |
|-----------|------|-----------|-----|
| `Ontology_Terms` | Global, persistente | Entidades estructuradas para grounding | ∞ |
| `RAG_Documents_Temp` | Efímero | PDFs temporales del usuario | 24-72h |
| `Query_Examples` | Global, curado | Few-shot examples versionados | ∞ |

---

## Schema: Ontology_Terms (Crítico)

```json
{
  // === Identificadores ===
  "term_id": "sha256_stable",           // Estable, no cambia
  "term_name": "Índice de Morosidad",   // Nombre canónico
  "code": "IMOR",                        // Código corto

  // === Contenido Conceptual ===
  "definition": "Cartera vencida / Cartera total × 100",
  "calculation_logic": "División de cartera vencida entre total",
  "formula_text": "(CV / CT) × 100",
  "variables": ["CV", "CT"],

  // === Mapeo a Datos ===
  "synonyms": ["morosidad", "mora", "cartera vencida ratio"],
  "sql_column": "imor",
  "sql_table": "monthly_kpis",

  // === Metadata ===
  "unit": "%",
  "category": "riesgo",
  "source_refs": ["pdf:glosario.pdf#p12", "cnbv:anexo36"],
  "link_confidence": 0.95,
  "version_tag": "v1.2.1_2025-01"
}
```

### Cambio Crítico vs v1.0

| Versión | Enfoque | Problema |
|---------|---------|----------|
| v1.0 | 3,526 términos como chunks genéricos | Sin mapeo a SQL |
| v1.2 | Entidades estructuradas | Mapeo explícito SQL |

---

## ETL Ontológico

### Pipeline (idempotente y versionado)

```
Excel + PDF
     │
     ▼
┌─────────────┐     ┌─────────────┐
│ Parse Excel │     │  Parse PDF  │
│ - campos    │     │ - términos  │
│ - tablas    │     │ - fórmulas  │
│ - unidades  │     │ - páginas   │
└──────┬──────┘     └──────┬──────┘
       │                   │
       └─────────┬─────────┘
                 ▼
         ┌─────────────┐
         │   Linker    │
         │ (Entity     │
         │ Resolution) │
         └──────┬──────┘
                │
                ▼
┌───────────────────────────────────┐
│        Ontology_Terms             │
│  - Consolida por term_id          │
│  - Upsert a Weaviate              │
└───────────────────────────────────┘
                │
                ▼
         Artefactos:
         - link_report.csv
         - manual_overrides.yml
```

### Linker (Entity Resolution)

| Técnica | Uso |
|---------|-----|
| Similitud de strings | Fuzzy match de nombres |
| Embeddings | Similitud semántica |
| Heurísticas | Patrones conocidos (IMOR, ICAP) |

**Output**:
- Matches automáticos (score alto)
- Reporte de low confidence para revisión

### Corrección Manual

```yaml
# manual_overrides.yml
overrides:
  - pdf_term: "Capital Básico"
    excel_field: "CAPITAL_BASICO_NETO"
    sql_table: "vw_banking_metrics"
    confidence: 1.0

  - pdf_term: "Índice de Morosidad"
    excel_field: "IMOR"
    sql_table: "monthly_kpis"
    confidence: 1.0
```

**Alcance v1.2**:
- Linker automático con scoring básico
- Manual override para top 20 términos críticos
- ❌ NO hay UI de corrección

---

## QuerySpec: Contrato JSON

### Schema v1.1

```json
{
  "intent": "SQL_QUERY",
  "bank": "INVEX",
  "metric_code": "IMOR",
  "metric_term_id": "term_abc123",

  "sql": {
    "table": "monthly_kpis",
    "column": "imor",
    "filters": [
      {"field": "bank", "op": "=", "value": "INVEX"}
    ],
    "time_grain": "monthly",
    "limit": 5000
  },

  "confidence": 0.92,
  "ambiguity_flags": [],

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

### Reglas de QuerySpec

| Regla | Enforcement |
|-------|-------------|
| No inventar tablas/columnas | Solo elegir de Ontology_Terms |
| Confidence mínimo | Si < 0.7 → abstención |
| Trazabilidad obligatoria | Siempre incluir source_refs |

---

## Few-shot Examples

Ubicación: `plugins/bank-advisor-private/config/query_examples.json`

**Alcance v1.2**:
- 20-30 ejemplos curados
- Versionados con el código
- Críticos para precisión del LLM

---

## Tablas SQL Permitidas

| Tabla/Vista | Tipo | Métricas |
|-------------|------|----------|
| `monthly_kpis` | Tabla | IMOR, ICOR, ICAP, Carteras |
| `vw_banking_metrics` | Vista | Agregaciones seguras |
| `metricas_financieras` | Tabla | Métricas derivadas |

---

**Versión**: 1.2.1 | **Fuente**: `docs/tex/Arquitectura.tex` secciones 4, 5, 6
