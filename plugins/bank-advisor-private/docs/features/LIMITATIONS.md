# BankAdvisor - Known Limitations

This document describes what the system **does NOT do** and known constraints.
Written in estoic-honest mode for technical stakeholders.

---

## Scope Limitations

### Banks Supported

| Bank | Status | Notes |
|------|--------|-------|
| INVEX | Supported | Primary bank, default for queries |
| SISTEMA | Supported | Aggregate of all banks |
| Others | Not supported | Would require ETL extension |

**Impact**: Queries like "IMOR de Banorte" will return empty or clarification.

### Metrics Supported

Currently **15 metrics** in whitelist:

- `imor` - Índice de morosidad
- `icap` - Índice de capitalización
- `icor` - Índice de cobertura
- `cartera_comercial_total` - Cartera comercial
- `cartera_vencida_total` - Cartera vencida
- `reservas_etapa_todas` - Reservas totales
- `perdida_esperada_total` - Pérdida esperada
- `cartera_comercial_sin_gob` - Calculated (comercial - gubernamental)
- ... (see `config/metrics.yaml` for full list)

**Impact**: Queries for unlisted metrics will fail or return clarification.

### Time Range

| Dimension | Value |
|-----------|-------|
| Data start | 2017-01 |
| Data end | 2025-10 (last ETL) |
| Granularity | Monthly |

**Impact**:
- Queries for dates before 2017 → empty response
- Queries for future dates (2030) → empty response (no crash)
- Daily/weekly granularity → not supported

---

## Language Limitations

### Supported Language

- **Spanish only** (Mexican banking terminology)
- No English support
- No Portuguese support

### Query Complexity

**Supported patterns**:
```
"IMOR de INVEX en 2024"
"Cartera comercial vs sistema"
"Compara ICAP de INVEX contra sistema"
"Evolución del IMOR últimos 12 meses"
```

**NOT supported**:
```
"What is the IMOR for INVEX?"              # English
"Dame el IMOR y el ICAP juntos"            # Multi-metric in single query
"IMOR de INVEX dividido entre sistema"     # Arithmetic operations
"Predicción del IMOR para 2025"            # Forecasting
"Por qué subió el IMOR?"                   # Causal analysis
```

### Colloquial Language

The system expects **formal banking terminology**.

**Works**:
- "índice de morosidad"
- "cartera vencida"
- "reservas totales"

**May fail**:
- "cuánto deben los morosos"
- "la lana que no han pagado"
- "el dinero guardado por si acaso"

---

## Technical Limitations

### Database Schema

**Current**: Single denormalized table (`monthly_kpis`)

**Implications**:
- No dimension tables (dim_bank, dim_metric, dim_date)
- Limited flexibility for complex aggregations
- Schema changes require ETL rewrite

**Future**: Consider fact/dim model for scale (see roadmap).

### Performance Characteristics

| Query Type | p50 | p95 | Bottleneck |
|------------|-----|-----|------------|
| Simple (rules) | 16ms | 26ms | None |
| Timeline | 112ms | 206ms | DB query |
| Calculated | 1.6s | 1.7s | LLM API call |

**Scaling considerations**:
- Current dataset: ~200 rows
- If 10x rows: May need indexes on (banco_norm, fecha)
- If 100x rows: Consider partitioning or materialized views

### LLM Dependency

**Hybrid strategy**:
- 80% of queries → rules-based (no LLM)
- 20% of queries → LLM fallback

**LLM failure modes**:
- Timeout → falls back to rules
- Invalid response → falls back to rules
- No API key → rules only (degraded accuracy)

**Impact**: System continues working without LLM, but may misclassify ambiguous queries.

---

## Visualization Limitations

### Chart Types

| Type | Supported | Notes |
|------|-----------|-------|
| Line chart | Yes | Evolution/timeline |
| Bar chart | Yes | Comparison |
| Scatter | Yes | Point values |
| Pie chart | No | Not implemented |
| Heatmap | No | Not implemented |
| Map | No | Not implemented |

### Customization

**Hardcoded**:
- Colors: INVEX=#E45756, SISTEMA=#AAB0B3
- Font: Default Plotly fonts
- Title format: "Metric - Bank"

**NOT configurable** (without code changes):
- Custom color palettes
- Logo/branding
- Export formats (PDF, PNG)

---

## ETL Limitations

### Data Source

- **Single source**: CNBV Excel files
- **Format dependency**: If CNBV changes format, ETL breaks
- **No automatic detection**: Must manually update parser

### Schedule

- **Fixed**: 2:00 AM daily via cron
- **No retry**: If fails, waits until next day
- **No alerting**: Must manually check `/health` or `etl_runs` table

### Incremental Updates

- **Full reload**: Each ETL run replaces all data
- **No delta**: Cannot process "only new months"
- **Duration**: ~3 minutes for full dataset

---

## Security Limitations

### Authentication

- **None**: API is open (relies on network security)
- **No rate limiting**: No protection against abuse
- **No audit log**: Query history not persisted

### Data Protection

- **No PII**: Dataset contains only aggregate metrics
- **No encryption at rest**: Standard PostgreSQL storage
- **Whitelist protection**: Only allowed metrics can be queried

---

## Integration Limitations

### MCP Protocol

- **JSON-RPC only**: No REST endpoints for direct SQL
- **Single tool**: `bank_analytics` only
- **No streaming**: Full response returned at once

### Frontend

- **Plotly.js required**: Client must render Plotly JSON
- **No SSR**: Charts rendered client-side only
- **No caching**: Each query hits the database

---

## What This System Does NOT Do

1. **Predictive analytics** - No ML models, no forecasting
2. **Real-time data** - Monthly granularity, daily ETL
3. **Multi-bank comparison** - Only INVEX vs SISTEMA
4. **Custom reports** - Fixed visualization templates
5. **User management** - No authentication/authorization
6. **Data entry** - Read-only system
7. **Audit trail** - No query logging (yet)
8. **Alerting** - No threshold-based notifications

---

## Roadmap Considerations

These limitations are **known and prioritized** for future work:

| Priority | Limitation | Effort | Impact |
|----------|------------|--------|--------|
| P1 | More banks | Medium | High business value |
| P1 | Normalized schema | High | Enables scale |
| P2 | Query logging | Low | Enables analytics |
| P2 | English support | Medium | International users |
| P3 | Forecasting | High | Requires ML |
| P3 | Real-time data | High | Requires different architecture |

---

## Questions?

If you encounter a limitation not listed here, please:

1. Check if it's a bug (unexpected behavior)
2. Document the use case
3. Add to this file or create an issue

This document should be updated as limitations are addressed or new ones discovered.
