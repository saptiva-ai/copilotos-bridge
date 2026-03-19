# Bank Advisor Plugin (Port 8002)

> Plugin de NL2SQL para métricas bancarias mexicanas (CNBV).

## Propósito

Permite consultar métricas financieras regulatorias en lenguaje natural:
- "¿Cuál es el IMOR de INVEX?"
- "Compara cartera comercial de INVEX vs sistema"
- "Evolución del ICAP en 2024"

## Tool MCP

```python
bank_analytics(
    metric_or_query: str,   # Query en lenguaje natural
    mode: str = "dashboard" # "dashboard", "executive", "debug"
) -> Dict
```

**Respuesta:**
```json
{
  "status": "success",
  "metric": "IMOR",
  "data": [...],
  "chart_config": {...},  // Plotly spec
  "interpretation": "..."
}
```

## Métricas Soportadas

| Métrica | Columna | Tipo | Aliases |
|---------|---------|------|---------|
| IMOR | `imor` | % | morosidad, mora |
| ICOR | `icor` | % | cobertura |
| ICAP | `icap_total` | % | capitalización |
| Cartera Total | `cartera_total` | MXN | préstamos |
| Cartera Vencida | `cartera_vencida` | MXN | vencida |

→ Lista completa: `config/synonyms.yaml`

## Archivos de Configuración

| Archivo | Propósito |
|---------|-----------|
| `config/bankadvisor.yaml` | Runtime settings |
| `config/synonyms.yaml` | Aliases de métricas |
| `config/manual_overrides.yml` | Entity linking rules |
| `config/visualizations.yaml` | Chart templates |

## Pipeline NL2SQL

```
Query NL → Security Check → Entity Resolution → Ontology Lookup
    → QuerySpec → SQL Generation → Validation → Execution → Viz
```

### Entity Linking

Conecta términos del PDF (glosarios) con columnas del Excel (datos):

```yaml
# config/manual_overrides.yml
term_to_field:
  - pdf_term: "Capital Básico"
    excel_field: "CAPITAL_BASICO"
    confidence: 1.0
```

**Precedencia**: Manual override > Semantic search > Heurístico

## SQL Security (5 Capas)

1. **Keyword blacklist** - No DDL/DML
2. **Table whitelist** - Solo `monthly_kpis`, `vw_*`
3. **Pattern detection** - Anti-injection
4. **LIMIT enforcement** - Max 10,000 rows
5. **RLS ready** - Filtros por tenant

## Archivos Clave

| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `src/main.py` | ~2K | MCP server, tool routing |
| `services/analytics_service.py` | ~2.8K | Dashboard logic |
| `services/query_spec_parser.py` | ~800 | NL → QuerySpec |
| `services/sql_validator.py` | ~300 | Security validation |

## Visualizaciones

9 modos de gráficas (definidos en `visualizations.yaml`):

| Modo | Tipo | Uso |
|------|------|-----|
| dashboard_month_comparison | Bar | INVEX vs SISTEMA |
| timeline_with_summary | Line | Histórico 12+ meses |
| dual_mode | Auto | Switch inteligente |
| ranking | Horiz Bar | Top 20 bancos |
| market_share | Pie | Participación mercado |

## Comandos

```bash
make init-bank-advisor          # Init DB + ETL
make logs S=bank-advisor        # Ver logs
make shell S=bank-advisor       # Shell en container
```

## Testing

```bash
# Smoke test
cd plugins/bank-advisor-private
python scripts/smoke_demo_bank_analytics.py --port 8002

# Pytest
make test T=api TEST_FILE="plugins/bank-advisor-private/tests/"
```

## Troubleshooting

| Problema | Solución |
|----------|----------|
| "No data returned" | Verificar fecha válida (no futura) |
| "Ambiguous query" | Sistema pide clarificación (correcto) |
| Timeout | Query muy compleja, simplificar |
| SQL error | Revisar `services/sql_validator.py` logs |
