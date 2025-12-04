# BankAdvisor - Developer Guide

Quick reference for extending and operating the system.

---

## Quick Start

```bash
cd plugins/bank-advisor-private

# Run tests
pytest tests/ -v

# Run smoke test (requires running container)
python scripts/smoke_demo_bank_analytics.py --port 8002

# Validate ETL health
python scripts/ops_validate_etl.py --port 8002

# Run performance benchmark
python scripts/benchmark_performance_http.py --port 8002
```

---

## Common Tasks

### Add a New Metric

1. **Add to `config/metrics.yaml`**:

```yaml
metrics:
  nueva_metrica:
    display_name: "Nueva Métrica"
    column: "nueva_metrica"  # DB column name
    type: "currency"  # currency | ratio | count
    aliases:
      - "alias 1"
      - "alias 2"
    description: "What this metric measures"
```

2. **Add DB column** (if new):

```sql
ALTER TABLE monthly_kpis ADD COLUMN nueva_metrica DECIMAL(18,2);
```

3. **Update ETL** (if source data exists):

Edit `src/bankadvisor/etl_runner.py` to map the new column.

4. **Add test**:

```python
# tests/test_new_metric.py
def test_nueva_metrica_query():
    response = query("nueva métrica de INVEX")
    assert response["data"]["type"] == "data"
```

---

### Add a New Alias

1. **Edit `config/metrics.yaml`**:

```yaml
metrics:
  imor:
    aliases:
      - "imor"
      - "índice de morosidad"
      - "morosidad"  # ← Add new alias here
```

2. **Test**:

```bash
python -c "
from bankadvisor.config_service import get_config
config = get_config()
print(config.find_metric('morosidad'))
"
# Should print: imor
```

---

### Add a New Visualization Mode

1. **Add to `config/visualizations.yaml`**:

```yaml
visualizations:
  nueva_metrica:
    modes:
      - timeline
      - comparison
    default_mode: timeline
    chart_config:
      timeline:
        type: line
        color: "#E45756"
      comparison:
        type: bar
        colors: ["#E45756", "#AAB0B3"]
```

2. **Update `VisualizationService`** if custom logic needed:

```python
# src/bankadvisor/services/visualization_service.py
def build_plotly_config_enhanced(data, section_config, intent):
    if section_config.get("custom_handler"):
        return _handle_custom_visualization(data, section_config)
    # ... existing logic
```

---

### Add a New Intent

1. **Add to `IntentService._classify_with_rules()`**:

```python
# src/bankadvisor/services/intent_service.py

# Add new rule
FORECAST_KEYWORDS = ["proyección", "forecast", "predicción"]

@classmethod
def _classify_with_rules(cls, query: str, entities: Any) -> ParsedIntent:
    query_lower = query.lower()

    # Rule N: Forecast keywords
    if any(kw in query_lower for kw in FORECAST_KEYWORDS):
        return ParsedIntent(
            intent=Intent.FORECAST,  # Add to Intent enum
            confidence=0.95,
            explanation="Detected forecast keyword"
        )
```

2. **Add to `Intent` enum**:

```python
# src/bankadvisor/models/intent.py
class Intent(Enum):
    EVOLUTION = "evolution"
    COMPARISON = "comparison"
    RANKING = "ranking"
    POINT_VALUE = "point_value"
    FORECAST = "forecast"  # ← New intent
```

3. **Handle in `AnalyticsService`**:

```python
# src/bankadvisor/services/analytics_service.py
if intent == "forecast":
    return AnalyticsService._format_forecast(rows, metric_id, config)
```

---

### Add a New Bank

1. **Ensure data exists in DB**:

```sql
SELECT DISTINCT banco_norm FROM monthly_kpis;
-- Should include the new bank
```

2. **Add to EntityService bank detection** (if needed):

```python
# src/bankadvisor/entity_service.py
KNOWN_BANKS = ["INVEX", "SISTEMA", "BANORTE", "NUEVO_BANCO"]
```

3. **Update tests**:

```python
def test_nuevo_banco_query():
    response = query("IMOR de NUEVO_BANCO en 2024")
    assert "NUEVO_BANCO" in str(response)
```

---

## Project Structure

```
plugins/bank-advisor-private/
├── src/
│   └── bankadvisor/
│       ├── __init__.py
│       ├── entity_service.py      # Extract entities from NL
│       ├── config_service.py      # Load metrics/viz config
│       ├── etl_runner.py          # ETL pipeline
│       ├── models/
│       │   ├── intent.py          # Intent enum
│       │   └── entities.py        # ExtractedEntities
│       └── services/
│           ├── intent_service.py      # Classify intent
│           ├── analytics_service.py   # DB queries + formatting
│           ├── plotly_generator.py    # HU3 → Plotly adapter
│           └── visualization_service.py # Build Plotly JSON
├── config/
│   ├── metrics.yaml               # Metric definitions
│   └── visualizations.yaml        # Chart configurations
├── scripts/
│   ├── smoke_demo_bank_analytics.py   # Pre-demo validation
│   ├── ops_validate_etl.py            # ETL health check
│   └── benchmark_performance_http.py  # Performance testing
├── tests/
│   ├── test_9_priority_visualizations.py
│   ├── test_e2e_demo_flows.py
│   └── test_nl_variants.py        # NL phrase variations
├── docs/
│   ├── ARCHITECTURE.md            # System design
│   ├── DEVELOPER_GUIDE.md         # This file
│   ├── LIMITATIONS.md             # Known constraints
│   └── DEMO_SCRIPT_2025-12-03.md  # Demo runbook
└── main.py                        # FastAPI server
```

---

## Testing Strategy

### Unit Tests
```bash
pytest tests/ -v --ignore=tests/test_e2e_demo_flows.py
```

### E2E Tests (requires DB)
```bash
pytest tests/test_e2e_demo_flows.py -v
```

### Smoke Test (requires running container)
```bash
python scripts/smoke_demo_bank_analytics.py --port 8002
```

### Performance Benchmark
```bash
python scripts/benchmark_performance_http.py --port 8002
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `SAPTIVA_API_KEY` | LLM API key for fallback classification | Optional |
| `PRIMARY_BANK` | Default bank for queries | `INVEX` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

---

## Debugging

### Check intent classification

```python
from bankadvisor.services.intent_service import IntentService
from bankadvisor.entity_service import EntityService

query = "IMOR de INVEX en 2024"
entities = EntityService.extract(query)
intent = await IntentService.classify(query, entities)

print(f"Intent: {intent.intent}")
print(f"Confidence: {intent.confidence}")
print(f"Explanation: {intent.explanation}")
```

### Check entity extraction

```python
from bankadvisor.entity_service import EntityService

query = "cartera comercial sin gobierno de INVEX vs sistema"
entities = EntityService.extract(query)

print(f"Metric: {entities.metric_id}")
print(f"Banks: {entities.banks}")
print(f"Date range: {entities.date_start} - {entities.date_end}")
```

### View container logs

```bash
docker logs -f bank-advisor-mcp 2>&1 | grep "bank_analytics"
```

---

## Common Issues

### "Metric not found"

1. Check alias exists in `config/metrics.yaml`
2. Check spelling matches exactly (case-insensitive)
3. Run: `python -c "from bankadvisor.config_service import get_config; print(get_config().metrics.keys())"`

### "No data returned"

1. Check date range has data: `SELECT COUNT(*) FROM monthly_kpis WHERE fecha BETWEEN '...' AND '...'`
2. Check bank exists: `SELECT DISTINCT banco_norm FROM monthly_kpis`
3. Check ETL ran: `python scripts/ops_validate_etl.py --port 8002`

### "LLM timeout"

1. Check `SAPTIVA_API_KEY` is set
2. System will fallback to rules-based classification
3. Check logs for: `intent_service.llm_fallback`

---

## Release Checklist

Before deploying:

```bash
# 1. Run all tests
pytest tests/ -v

# 2. Run smoke test
python scripts/smoke_demo_bank_analytics.py --port 8002

# 3. Validate ETL
python scripts/ops_validate_etl.py --port 8002

# 4. Run benchmark (optional)
python scripts/benchmark_performance_http.py --port 8002

# 5. Check for secrets
git diff --cached | grep -iE "(api_key|password|secret)"
```

All checks should pass before merge to `main`.
