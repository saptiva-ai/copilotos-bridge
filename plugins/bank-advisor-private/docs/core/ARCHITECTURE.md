# BankAdvisor - Architecture

## Overview

BankAdvisor is a natural language query system for banking metrics (CNBV data).
It follows **SOLID principles** and uses a **hybrid classification strategy**.

---

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OctaviOS / Client                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼ JSON-RPC 2.0
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FastAPI Server (main.py)                          │
│                                                                             │
│  POST /rpc  ─────►  bank_analytics tool  ─────►  HU3 Pipeline               │
│  GET /health                                                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
           ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
           │ EntityService │ │ IntentService │ │ ConfigService │
           │               │ │               │ │               │
           │ - Extract     │ │ - Rules-first │ │ - metrics.yaml│
           │   metric      │ │ - LLM-fallback│ │ - aliases     │
           │ - Extract     │ │ - Confidence  │ │ - whitelist   │
           │   bank        │ │   scoring     │ │               │
           │ - Extract     │ └───────────────┘ └───────────────┘
           │   date range  │
           │ - Smart       │
           │   defaults    │
           └───────────────┘
                    │
                    ▼
           ┌───────────────┐
           │ Analytics     │
           │ Service       │
           │               │
           │ - Query DB    │
           │ - Format data │
           │ - Evolution/  │
           │   Comparison/ │
           │   Ranking     │
           └───────────────┘
                    │
                    ▼
           ┌───────────────┐
           │ PlotlyGenerator│
           │               │
           │ - HU3 → Legacy│
           │   adapter     │
           │ - Build config│
           │ - Chart type  │
           │   selection   │
           └───────────────┘
                    │
                    ▼
           ┌───────────────┐
           │ Visualization │
           │ Service       │
           │               │
           │ - Plotly JSON │
           │ - Layout      │
           │ - Colors      │
           │ - Formatting  │
           └───────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PostgreSQL                                     │
│                                                                             │
│  monthly_kpis (denormalized)  │  etl_runs (tracking)                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Roles

### 1. EntityService (`src/bankadvisor/entity_service.py`)

**Responsibility**: Extract entities from natural language query.

```python
# Input
query = "IMOR de INVEX en 2024"

# Output
ExtractedEntities(
    metric_id="imor",
    metric_display="IMOR",
    banks=["INVEX"],
    date_start="2024-01-01",
    date_end="2024-12-31"
)
```

**Smart Defaults** (Dependency Inversion):
- If metric + date but no bank → default to `PRIMARY_BANK` (INVEX)
- Avoids unnecessary clarification prompts

### 2. IntentService (`src/bankadvisor/services/intent_service.py`)

**Responsibility**: Classify query intent using hybrid strategy.

**Strategy (Open/Closed Principle)**:
```
1. Try rules-first (fast, deterministic)
2. If confidence >= 0.9 → use rules result
3. If confidence < 0.9 → consult LLM
4. If LLM fails → fallback to rules anyway
```

**Intents**:
| Intent | Trigger Keywords | Visualization |
|--------|------------------|---------------|
| `evolution` | "en 2024", "últimos N meses", date range | Line chart |
| `comparison` | "vs", "contra", "compara" | Bar chart |
| `ranking` | "top", "mejores", "peores" | Horizontal bar |
| `point_value` | Single value request | Single metric |

**Performance**:
- 80% of queries classified via rules in <1ms
- LLM only consulted for ambiguous cases

### 3. ConfigService (`src/bankadvisor/config_service.py`)

**Responsibility**: Load and validate metric configurations.

**Key files**:
- `config/metrics.yaml` - Metric definitions, aliases, types
- `config/visualizations.yaml` - Chart configurations

**Alias matching** (Open/Closed):
- Prefers longer/more specific matches
- "cartera comercial sin gobierno" → `cartera_comercial_sin_gob` (not `cartera_comercial_total`)

### 4. AnalyticsService (`src/bankadvisor/services/analytics_service.py`)

**Responsibility**: Execute DB queries and format results.

**Smart Evolution Default** (Liskov Substitution):
```python
# If intent is point_value but we have >3 data points
# → automatically format as evolution (show trend)
if len(rows) > 3:
    return _format_evolution(rows, ...)
```

**Output formats**:
- `evolution`: `{values: [{date, value, bank}, ...]}`
- `comparison`: `{values: [{bank, value}, ...]}`
- `ranking`: `{values: [{bank, value, rank}, ...]}`

### 5. PlotlyGenerator (`src/bankadvisor/services/plotly_generator.py`)

**Responsibility**: Convert HU3 format to Plotly config.

**Single Responsibility**: This is an adapter between:
- HU3 format: `{data: {values: [...]}}`
- Legacy format: `{data: {months: [...]}}`

```python
# Input (HU3)
data = {"values": [{"date": "2024-01", "value": 0.05}]}

# Output (Plotly config)
plotly_config = {
    "data": [{"x": ["2024-01"], "y": [0.05], "type": "scatter"}],
    "layout": {"title": "IMOR - INVEX"}
}
```

### 6. VisualizationService (`src/bankadvisor/services/visualization_service.py`)

**Responsibility**: Build final Plotly JSON with layout and styling.

**Features**:
- Dual mode: Same metric can be line (evolution) or bar (comparison)
- Consistent colors: INVEX = #E45756, SISTEMA = #AAB0B3
- Ratio formatting: `.1%` for IMOR, ICAP, ICOR

---

## Data Flow Example

**Query**: `"IMOR de INVEX en 2024"`

```
1. EntityService.extract()
   → metric_id="imor", banks=["INVEX"], date_range=2024

2. IntentService.classify()
   → Rule match: has date range → intent=evolution (conf=0.95)
   → Skip LLM (confidence >= 0.9)

3. AnalyticsService.execute()
   → SQL: SELECT fecha, imor FROM monthly_kpis
          WHERE banco_norm='INVEX' AND fecha BETWEEN '2024-01-01' AND '2024-12-31'
   → Format as evolution: {values: [{date, value}, ...]}

4. PlotlyGenerator.generate()
   → Convert HU3 format to legacy format
   → Call VisualizationService.build_plotly_config_enhanced()

5. VisualizationService.build_plotly_config_enhanced()
   → mode="timeline", chart_type="line"
   → Return Plotly JSON with traces + layout

6. Response
   → {data: {type: "data", values: [...], plotly_config: {...}}}
```

---

## ETL Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ CNBV Excel  │ ──► │ etl_runner  │ ──► │ monthly_kpis│
│ files       │     │ .py         │     │ table       │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ etl_runs    │
                    │ (tracking)  │
                    └─────────────┘
```

**Schedule**: Daily at 2:00 AM via cron
**Validation**: `scripts/ops_validate_etl.py`

---

## SOLID Principles Applied

| Principle | Implementation |
|-----------|----------------|
| **S**ingle Responsibility | Each service has one job (Entity, Intent, Analytics, Plotly) |
| **O**pen/Closed | Hybrid classification extensible without modifying core |
| **L**iskov Substitution | Smart defaults preserve expected behavior |
| **I**nterface Segregation | Minimal interfaces between services |
| **D**ependency Inversion | Services injected, not hardcoded |

---

## Key Configuration Files

| File | Purpose |
|------|---------|
| `config/metrics.yaml` | Metric definitions, aliases, types |
| `config/visualizations.yaml` | Chart configurations |
| `config/bankadvisor.yaml` | Runtime settings (PRIMARY_BANK, etc.) |
| `.env` | Environment variables (DB, LLM API keys) |

---

## Performance Characteristics

| Query Type | p50 | p95 | Notes |
|------------|-----|-----|-------|
| Ratios (IMOR, ICAP) | 16ms | 26ms | Rules-first, no LLM |
| Timelines | 112ms | 206ms | DB query |
| Calculated metrics | 1.6s | 1.7s | Requires LLM interpretation |

See `docs/performance_baseline.json` for full benchmark data.
