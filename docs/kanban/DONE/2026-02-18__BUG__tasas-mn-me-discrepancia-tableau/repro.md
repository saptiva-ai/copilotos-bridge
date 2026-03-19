# Reproducción: Discrepancia TASA PROMEDIO MN/ME

## Requisitos

- Python 3.11+
- pandas >= 2.0
- Acceso al CSV: `plugins/bank-advisor-private/data/raw/incoming/drive-download-20260212T024209Z-1-001/CorporateLoan_CNBVDB.csv`

## Paso 1: Verificar datos crudos

```bash
# Contar filas enero 2025
grep -c "1/31/25" plugins/bank-advisor-private/data/raw/incoming/drive-download-20260212T024209Z-1-001/CorporateLoan_CNBVDB.csv
# Esperado: ~68,728 filas (total), ~137,972 con variantes de fecha
```

## Paso 2: Reproducir cálculo (Python)

```python
import pandas as pd
import numpy as np

CSV = 'plugins/bank-advisor-private/data/raw/incoming/drive-download-20260212T024209Z-1-001/CorporateLoan_CNBVDB.csv'

df = pd.read_csv(CSV,
    usecols=['Currency', 'Institution Code', 'Monitoring Term', 'Total Portfolio', 'Average Rate'],
    dtype={'Institution Code': str, 'Currency': str, 'Monitoring Term': str, 'Total Portfolio': str},
    low_memory=False
)

df['Total Portfolio'] = pd.to_numeric(df['Total Portfolio'].str.replace(',', '', regex=False), errors='coerce')
jan25 = df[df['Monitoring Term'].str.contains('1/31/25', na=False)].copy()
jan25['Average Rate'] = pd.to_numeric(jan25['Average Rate'], errors='coerce').fillna(0)
jan25['Total Portfolio'] = jan25['Total Portfolio'].fillna(0)

# Filtrar BANCREA + ME
bancrea_me = jan25[
    (jan25['Institution Code'].str.strip() == '040152') &
    (jan25['Currency'] == 'Moneda extranjera')
]

# Mostrar todas las filas
print(bancrea_me[['Average Rate', 'Total Portfolio']].to_string())

# Método NUESTRO (excluir tasa=0 de ambos)
valid = bancrea_me[(bancrea_me['Average Rate'] > 0) & (bancrea_me['Total Portfolio'] > 0)]
our = (valid['Average Rate'] * valid['Total Portfolio']).sum() / valid['Total Portfolio'].sum()
print(f"Nuestro: {our:.4f}%")

# Método TABLEAU (tasa=0→NULL en numerador, portfolio cuenta en denominador)
has_port = bancrea_me[bancrea_me['Total Portfolio'] > 0]
has_rate = has_port[has_port['Average Rate'] > 0]
tab_num = (has_rate['Average Rate'] / 100 * has_rate['Total Portfolio']).sum()
tab_den = has_port['Total Portfolio'].sum()
tab = tab_num / tab_den * 100
print(f"Tableau: {tab:.4f}%")
```

**Salida esperada:**
```
Nuestro: 7.8000%
Tableau: 2.9481%
```

## Paso 3: Verificar fórmula de Tableau

```bash
# Extraer fórmula del XML del workbook
grep -A2 "Tasa Todos" plugins/bank-advisor-private/data/raw/incoming/drive-download-20260212T024209Z-1-001/tableau_extract/Invex_Tablero_V3.twb | head -5
```

Buscar:
```xml
<calculation class='tableau' formula='if [Average Rate] = 0 THEN NULL ELSE [Average Rate]/100 END' />
```

Y la fórmula de "Tasa Prom Pond":
```xml
<calculation class='tableau' formula='SUM ([Total Portfolio]*[Calculation_700591262736248833])/sum([Total Portfolio])' />
```

Donde `Calculation_700591262736248833` es "Tasa Todos" — aquí está la asimetría: NULL×Portfolio=NULL en SUM (excluido), pero SUM(Portfolio) en denominador incluye TODAS las filas.

## Paso 4: Verificar valores en DB producción

```sql
-- Via SSH tunnel (ssh -L 18000:localhost:8000 ${PROD_USER}@${PROD_HOST} -N -f)
SELECT banco_norm, tasa_mn, tasa_me,
       tasa_mn * 100 AS tasa_mn_pct,
       tasa_me * 100 AS tasa_me_pct
FROM bank_fact_kpis_mensual
WHERE periodo_id = 202501
  AND banco_norm IN ('BANCREA', 'VE POR MAS', 'BANCO BASE', 'SABADELL', 'MONEX', 'INVEX')
ORDER BY banco_norm;
```

Valores actuales en DB (almacenados como ratio, calculados con método actual que excluye tasa=0):
- BANCREA MN: 0.135627 (13.56%)
- BANCREA ME: 0.078000 (7.80%)

Valores que deberían estar (método Tableau):
- BANCREA MN: 0.135266 (13.53%)
- BANCREA ME: 0.029481 (2.95%)

## Paso 5: Verificar el fix (post-corrección)

Después de aplicar el fix, re-ejecutar el paso 4 y verificar que los valores coincidan con la columna "Tableau" de la tabla comparativa en research.md.
