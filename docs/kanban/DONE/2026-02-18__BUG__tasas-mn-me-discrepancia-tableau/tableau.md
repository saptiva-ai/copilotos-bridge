# Análisis del Workbook Tableau

## Ubicación del Workbook

- **Packaged (.twbx)**: `plugins/bank-advisor-private/data/raw/incoming/drive-download-20260212T024209Z-1-001/Invex_Tablero_202406_v2021.4.twbx` (24MB, contiene extract embebido)
- **XML directo (.twb)**: `plugins/bank-advisor-private/data/raw/incoming/drive-download-20260212T024209Z-1-001/Invex_Tablero_V3.twb` (3.5MB)
- **Extraído**: `plugins/bank-advisor-private/data/raw/incoming/drive-download-20260212T024209Z-1-001/tableau_extract/Invex_Tablero_V3.twb`

## Descompresión del .twbx

El `.twbx` es un archivo ZIP. Estructura interna:
```
tableau_extract/
├── Invex_Tablero_V3.twb          (3.6MB XML — workbook)
└── Data/
    └── INVEX ANALITICS/
        ├── CorporateLoan_CNBVDB.csv  (86MB — extract embebido, datos hasta ~Jun 2024)
        ├── CNBV_Cartera_Bancos_V2.xlsx
        ├── CASTIGOS.xlsx
        ├── Castigos Comerciales.xlsx
        ├── ICAP_Bancos.xlsx
        ├── Instituciones.xlsx
        ├── TDA.xlsx
        └── TE_Invex_Sistema.xlsx
```

**NOTA**: El CSV embebido (86MB) tiene datos hasta ~Jun 2024. El CSV actualizado en la raíz del download (270MB) tiene datos hasta Ene 2025+. Tableau en producción probablemente se conecta al CSV actualizado.

## Datasources en el Workbook

1. **CorporateLoan_CNBVDB.csv+ (Varias conexiones)** — fuente principal de tasas
2. **Sheet1+ (Varias conexiones)** — CNBV_Cartera_Bancos, Instituciones, Castigos
3. **ICAP_Bancos** — datos de capitalización
4. **TE_Invex_Sistema** — tasa efectiva sistema/INVEX consumo
5. **TDA** — Tasa de Deterioro Acumulada

## Fórmulas de Cálculo de Tasas (VERBATIM del XML)

### "Tasa Todos" (campo base)
**XML línea ~11562** — `Calculation_700591262736248833`:
```
if [Average Rate] = 0 THEN NULL ELSE [Average Rate]/100 END
```
- Convierte tasa 0 a NULL (no a cero)
- Convierte porcentaje a ratio (/100)
- Este campo se usa como multiplicando en los cálculos ponderados

### "Tasa Prom Pond" (promedio ponderado del peer group)
**XML línea ~11550** — `Calculation_1914452103250329600`:
```
SUM ([Total Portfolio]*[Calculation_700591262736248833])/sum([Total Portfolio])
```
- Numerador: SUM(Portfolio × Tasa_ratio) — NULLs excluidos por SUM
- Denominador: SUM(Portfolio) — incluye TODAS las filas con portfolio
- **Este es el valor que aparece como "Tasa Promedio" en la tabla de Tableau**

### "TASA INVEX" (solo INVEX)
**XML línea ~11559** — `Calculation_700591262732902400`:
```
IF [DESCRIPCION]='INVEX' THEN [Calculation_700591262736248833] ELSE NULL END
```

### "Tasa Pond Invex" (ponderado solo INVEX)
**XML línea ~11556** — `Calculation_1914452103259058181`:
```
sum( [Calculation_1914452103252750340]*[Calculation_700591262732902400]) / sum([Calculation_1914452103252750340])
```
Donde `Calculation_1914452103252750340` ("SALDO INVEX"):
```
IF [DESCRIPCION] = 'INVEX' THEN [Total Portfolio] else 0 END
```

### "SALDO INVEX"
**XML línea ~11553** — `Calculation_1914452103252750340`:
```
IF [DESCRIPCION] = 'INVEX' THEN [Total Portfolio] else 0 END
```

## Filtros en Worksheets de Tasas

### Worksheet "Tasa x Tiempo MN"
1. **Currency**: `member='Moneda nacional'` (exclusivo)
2. **Bank filter** ("Descripcion conjunto"): ACTINVER, AFIRME, BANCA MIFEL, BANCO BASE, BANCO DEL BAJÍO, BANCREA, BANREGIO, BANSÍ, CIBANCO, INVEX, MONEX, MULTIVA, SABADELL, VE POR MÁS (14 bancos)
3. **Date range**: `min=#2020-02-03#`
4. **State**: todos

### Worksheet "Tasa x Tiempo ME"
1. **Currency**: `member='Moneda extranjera'` (exclusivo)
2. Mismos 14 bancos
3. Misma fecha mínima

### Worksheets "Tasas vs Promedio MN/ME"
- Usan las mismas fórmulas y filtros
- Variantes (2) existen para layouts diferentes

## Manejo de NULL

| Patrón | Uso |
|--------|-----|
| `if X = 0 THEN NULL ELSE X END` | Tasa Todos — convierte tasa 0 a NULL |
| `IF banco='INVEX' THEN X ELSE NULL END` | Filtro por banco (Tasa INVEX, SALDO INVEX) |
| `IF banco='INVEX' THEN X ELSE 0 END` | Filtro por banco con default 0 |
| `ZN(SUM(...))` | Trend calculations — convierte NULL de SUM a 0 |

## Redondeo

**No se encontraron funciones ROUND() explícitas** en ningún campo calculado.
El redondeo visible es por formato de display: `p0.00%` (porcentaje con 2 decimales).

## La Asimetría Clave

En `SUM(A * B) / SUM(A)` donde B puede ser NULL:
- `SUM(A * B)`: Tableau propaga NULL → filas con B=NULL no contribuyen
- `SUM(A)`: Tableau suma A de TODAS las filas, incluyendo aquellas donde B=NULL
- Esto crea un denominador mayor que el numerador conceptualmente "merece"
- Es un patrón conocido en Tableau y no es un bug de Tableau per se, sino una decisión de diseño
