# Research: tasa_mn Column Missing from PostgreSQL

## Investigation Summary

### 1. Test Failure Analysis

**Test 33 from Happy Path Suite:**
```
Query: "¿Cuál es la tasa de crédito corporativo en moneda nacional?"
Expected: chart
Actual: empty (no data points)
```

Debug output showed:
```
DEBUG [33]: Type=empty, Plotly Data Len=0, SQL=SELECT fecha, banco_norm, tasa_mn AS v...
```

The SQL is correct but returns no data because the column doesn't exist.

### 2. Database Schema Analysis

**Current monthly_kpis columns (16 total):**
```
id, fecha, institucion, banco_norm, cartera_total, cartera_comercial_total,
cartera_consumo_total, cartera_vivienda_total, entidades_gubernamentales_total,
entidades_financieras_total, empresarial_total, cartera_vencida, imor, icor,
reservas_etapa_todas, created_at
```

**Missing columns (defined in model but not in DB):**
- `tasa_mn` - Corporate loan rate in MXN
- `tasa_me` - Corporate loan rate in foreign currency
- `icap_total` - Capital adequacy ratio
- `tda_cartera_total` - Total portfolio TDA

### 3. Model Definition

File: `plugins/bank-advisor-private/src/bankadvisor/models/kpi.py`
```python
class MonthlyKPI(Base):
    # ... existing columns ...
    tasa_mn = Column(Float, nullable=True)  # Line 59
    tasa_me = Column(Float, nullable=True)  # Line 60
    icap_total = Column(Float, nullable=True)
    tda_cartera_total = Column(Float, nullable=True)
```

### 4. Data Source

File: `data/raw/CorporateLoan_CNBVDB.csv`
- Contains historical corporate loan interest rates
- Data by bank (institucion) and month
- Separate rates for MN (Moneda Nacional) and ME (Moneda Extranjera)

### 5. ETL Pipeline

**Corporate Rates Processor:** `src/bankadvisor/corporate_rates_processor.py`
```python
def process_corporate_rates(csv_path: str) -> pd.DataFrame:
    """
    Returns DataFrame with columns: [fecha, institucion, tasa_mn, tasa_me]
    """
```

**Unified ETL Loader:** `etl/core/loaders_unified.py`
- Lines 501-602 handle corporate rate loading
- Normalizes rates from percentage (0-100) to ratio (0-1) scale

### 6. Migration File

File: `migrations/001_add_missing_columns.sql`
```sql
ALTER TABLE monthly_kpis
ADD COLUMN IF NOT EXISTS tasa_mn DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS tasa_me DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS icap_total DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS tda_cartera_total DOUBLE PRECISION;

COMMENT ON COLUMN monthly_kpis.tasa_mn IS 'Tasa promedio ponderada para créditos corporativos en Moneda Nacional (%)';
```

### 7. SAFE_METRIC_COLUMNS Mapping

File: `src/bankadvisor/services/analytics_service.py:97`
```python
SAFE_METRIC_COLUMNS = {
    # ... other columns ...
    "tasa_mn": MonthlyKPI.tasa_mn,
    "tasa_me": MonthlyKPI.tasa_me,
}
```

The application code is ready - only the database schema needs updating.

## Root Cause

The migration `001_add_missing_columns.sql` was never executed on the GCP production database. The columns exist in the SQLAlchemy model but not in the actual PostgreSQL table.

## Resolution Path

1. Connect to GCP PostgreSQL production
2. Run the migration to add columns
3. Execute ETL to populate data from CSV
4. Verify with test query
5. Re-run Happy Path Suite to confirm Test 33 passes

## Estimated Data Volume

Based on ETL documentation:
- Expected ~205 records with tasa_mn data
- Coverage: INVEX (~102 records) + SISTEMA (~103 records)
- Date range: Historical data matching other metrics
