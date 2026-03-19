# Research: ICAP Decimal Shift Bug

## Data Verification

### PostgreSQL Query Results (2026-01-30)

```sql
-- BBVA 2025
SELECT fecha, icap_total FROM bank_fact_kpis_mensual
WHERE banco_norm = 'BBVA' AND fecha >= '2025-01-01';

 fecha       | icap_total
-------------|------------
 2025-01-01  |    19.1934
 2025-02-01  |     20.449
 2025-03-01  |    20.1826
 2025-04-01  |    20.2035
 2025-05-01  |    20.6447
 2025-06-01  |    20.0687
 2025-07-01  |    19.9734
 2025-08-01  |    20.4228
 2025-09-01  |    19.9711
 2025-10-01  |    20.0594
```

### Bug Manifestation

| Dato Real | Dato Mostrado | Factor |
|-----------|---------------|--------|
| 20.0594%  | 2005.94%      | x100   |
| 19.97%    | 1997%         | x100   |

## Areas to Investigate

### 1. Pipeline NL2SQL Response Builder

Revisar:
- `plugins/bank-advisor/src/pipelines/`
- `plugins/bank-advisor/src/services/`

Buscar transformaciones de tipo:
```python
value * 100  # Conversion ratio -> porcentaje
```

### 2. Chart Templates

Revisar:
- `plugins/bank-advisor/src/templates/`
- Formateo de valores en Plotly config

### 3. Statistics Summary Generator

Revisar donde se genera el texto:
```
"BBVA tiene un valor actual de 2005.94%"
```

## Next Steps

1. Grep por `* 100` en bank-advisor
2. Revisar metric_type = 'ratio' handling
3. Verificar si el bug es en chart data o en text response
