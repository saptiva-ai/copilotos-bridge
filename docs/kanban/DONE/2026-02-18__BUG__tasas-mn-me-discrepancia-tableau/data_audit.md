# Auditoría de Datos: CorporateLoan_CNBVDB.csv

## Ubicación

```
plugins/bank-advisor-private/data/raw/incoming/drive-download-20260212T024209Z-1-001/CorporateLoan_CNBVDB.csv
```

- Tamaño: 270MB
- Filas totales: 1,668,931
- Filas Enero 2025 (`Monitoring Term = 1/31/25`): 68,728

## Esquema

| # | Columna | Tipo | Ejemplo | Notas |
|---|---------|------|---------|-------|
| 1 | Currency type | string | "Pesos", "UDIS" | Tipo de moneda macro |
| 2 | Corporate Size | string | "PyME", "Grande", "Fideicomiso" | Tamaño empresa |
| 3 | State | string | "CIUDAD DE MEXICO" | Estado geográfico |
| 4 | State Code | int | 9 | Código de estado |
| 5 | Currency | string | "Moneda nacional", "Moneda extranjera" | **Discriminador MN/ME** |
| 6 | Currecy Code | int | 14 (MN), 15 (ME) | Código moneda (typo en header) |
| 7 | Institution | string | "Invex", "Bancrea" | Nombre del banco |
| 8 | Institution Code | string | "040059", "040152" | **Código CNBV** (6 dígitos) |
| 9 | Monitoring Term | string | "1/31/25" | Fecha fin de mes (M/DD/YY) |
| 10 | Funded | string | "Sin apoyo", "Con apoyo" | Tipo de fondeo |
| 11 | Total Portfolio | string | "62,168,870" | Saldo cartera (con comas) |
| 12 | Perrformin Portfolio | string | | Cartera vigente (typo) |
| 13 | Non Performing Portfolio | string | | Cartera vencida |
| 14 | IMOR | float | | Índice de morosidad |
| 15 | Number of Customers | int | | Número de clientes |
| 16 | Number of loans | int | | Número de créditos |
| 17 | Average Rate | float | 7.8, 13.56, 0 | **Tasa promedio (%)** |
| 18 | Average Term | float | | Plazo promedio |
| 19 | Draw down Amount | float | | Monto dispuesto |
| 20 | Average Rate Median | float | | Mediana de tasa |
| 21 | Average Term Median | float | | Mediana de plazo |
| 22-25 | Etapa 1-3, Valor Razonable | float | | IFRS9 stages |

## Calidad de Datos — Enero 2025

### Distribución por Currency
| Currency | Filas | % |
|----------|-------|---|
| Moneda nacional | 49,035 | 71.3% |
| Moneda extranjera | 19,489 | 28.4% |
| (UDIS/otros) | 204 | 0.3% |

### Filas con Average Rate = 0 (pero Total Portfolio > 0)

Son filas donde hay saldo asignado pero no se reporta tasa. Esto es normal en datos CNBV — ocurre para combinaciones estado/tamaño donde el banco tiene cartera pero no se calcula tasa efectiva (ej: fideicomisos sin interés, líneas de crédito sin disposición activa).

**MN — Enero 2025:**
| Banco | Filas tasa=0 | Portfolio acumulado |
|-------|-------------|-------------------|
| BANCO BASE | 11 | $99,702,539 |
| VE POR MAS | 2 | $103,871,871 |
| MONEX | 5 | $98,055,003 |
| BANCREA | 4 | $80,795,578 |
| MULTIVA | 2 | $4,653,441 |
| CIBANCO | 2 | $43,302,503 |
| BAJIO | 16 | $1,230,518 |

**ME — Enero 2025:**
| Banco | Filas tasa=0 | Portfolio acumulado |
|-------|-------------|-------------------|
| BANCREA | 10 | $102,315,418 |
| BANCO BASE | 13 | $87,137,524 |
| INVEX | 1 | $70,019,171 |
| MONEX | 14 | $63,927,252 |
| CIBANCO | 4 | $30,623,474 |

**BANCREA ME**: Caso más extremo. Solo 1 fila con tasa (7.8%, $62M) vs 10 filas sin tasa ($102M). La proporción tasa-válida/total = 38%.

### Fechas con errores
- Se encontró "11/31/22" (noviembre no tiene 31 días) — se maneja con `errors='coerce'` en parsing
- No afecta enero 2025

### Institution Codes mapeados
- 40+ bancos en el CSV
- 33 bancos en el mapeo `CODE_TO_BANCO` del backfill
- Bancos sin mapeo son descartados (instituciones muy pequeñas o ya fusionadas)

## Archivos Relacionados en incoming/

| Archivo | Tamaño | Contenido |
|---------|--------|-----------|
| CorporateLoan_CNBVDB.csv | 270MB | **Dataset principal** — créditos comerciales CNBV |
| CNBV_Cartera_Bancos_V2.xlsx | 3.4MB | Cartera por tipo de crédito (más granular) |
| Instituciones.xlsx | 11KB | Catálogo de instituciones |
| TASAS DATOS.csv | 2KB | Resumen de tasas (un solo periodo, sin enero 2025) |
| CorporateLoan_BM.R | 2.5KB | Script R para transformar datos de Benchmark |
| Catera Analitica Benchmark v2.xlsx | 49MB | Benchmark analítico |
| 040_R04A_419.csv | 64MB | Datos regulatorios (conceptos contables) |

## Conclusión

Los datos crudos son consistentes y correctos. La discrepancia NO proviene de errores en el CSV sino de la interpretación de filas con `Average Rate = 0` en la fórmula de agregación.
