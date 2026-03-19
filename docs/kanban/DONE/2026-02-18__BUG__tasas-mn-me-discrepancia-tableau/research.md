# Research: Discrepancia TASA PROMEDIO MN/ME

## Hipótesis Evaluadas

### H1: Promedio simple vs ponderado — DESCARTADA
- Tanto Tableau como nuestro backfill usan promedio ponderado por Total Portfolio
- Tableau XML (línea 11550): `SUM([Total Portfolio]*[Tasa Todos])/sum([Total Portfolio])`
- Backfill (línea 178-190): `SUM(Average Rate * Total Portfolio) / SUM(Total Portfolio)`

### H2: Filtro "créditos comerciales" ausente — DESCARTADA
- El CSV `CorporateLoan_CNBVDB.csv` YA contiene exclusivamente créditos comerciales (corporate loans)
- No hay filtro adicional necesario — el dataset fuente es el mismo

### H3: Diferente manejo de filas con tasa = 0 — **VALIDADA NUMÉRICAMENTE** ✅
- **Tableau**: convierte tasa=0 a NULL via `if [Average Rate] = 0 THEN NULL ELSE [Average Rate]/100 END`
  - NULL × Portfolio = NULL → excluido de SUM del numerador
  - Pero Portfolio SÍ se suma en denominador (`SUM([Total Portfolio])` incluye todas las filas)
- **Nuestro backfill**: filtra `Average Rate > 0` y `Total Portfolio > 0` → esas filas desaparecen de AMBOS numerador y denominador
- **Efecto**: `denom_Tableau > denom_nuestro` → `tasa_Tableau < tasa_nuestra`

### H4: Join duplicado o mapeo incorrecto de bank_id — DESCARTADA
- `Institution Code` en CSV mapea correctamente: `040152` → BANCREA
- No hay ambigüedad en el mapeo

### H5: Moneda mal asignada (MN vs ME cruzadas) — DESCARTADA
- Filtro por columna `Currency` es claro: "Moneda nacional" vs "Moneda extranjera"
- No hay cruce

### H6: NULL→0 en frontend (serie temporal) — PENDIENTE
- Caso C del reporte original: serie temporal muestra caídas a 0 cuando debería ser NULL
- Esto es un bug SEPARADO que probablemente existe en el frontend o en el pipeline de datos
- No afecta los valores puntuales de enero 2025 pero sí la visualización temporal

## Evidencia Numérica

### Reproducción Exacta — ENERO 2025

Usando el mismo CSV (`CorporateLoan_CNBVDB.csv`, 1.67M filas), filtrado a `Monitoring Term = 1/31/25`:

**Método Tableau** (denominador incluye filas con tasa=0):
```
Tasa = SUM(Portfolio_i × max(Rate_i,0)/100) / SUM(Portfolio_i para TODAS las filas con Portfolio>0)
```

**Método Nuestro** (denominador excluye filas con tasa=0):
```
Tasa = SUM(Portfolio_i × Rate_i) / SUM(Portfolio_i) solo donde Rate_i > 0 AND Portfolio_i > 0
```

### MN — Bancos discrepantes

| Banco | Nuestro % | Tableau % | Tableau Ref % | Filas tasa=0 | Portfolio tasa=0 |
|-------|-----------|-----------|---------------|-------------|-----------------|
| BANCREA | 13.5627 | 13.5266 | 13.5266 | 4 | $80.8M |
| VE POR MAS | 13.4778 | 13.4341 | 13.4341 | 2 | $103.9M |
| BANCO BASE | 13.3453 | 13.1707 | 13.1707 | 11 | $99.7M |
| SABADELL | 13.0253 | 13.0253 | 13.0253 | 0 | $0 |
| MONEX | 12.7519 | 12.6951 | 12.6951 | 5 | $98.1M |

**Nota**: SABADELL coincide porque no tiene filas con tasa=0. Las diferencias se explican al 100% por este mecanismo.

### ME — Bancos discrepantes

| Banco | Nuestro % | Tableau % | Tableau Ref % | Filas tasa=0 | Portfolio tasa=0 |
|-------|-----------|-----------|---------------|-------------|-----------------|
| BANCREA | 7.8000 | 2.9481 | 2.95 | 10 | $102.3M |
| BANCO BASE | 7.6554 | 7.4674 | 7.47 | 13 | $87.1M |
| INVEX | 9.3147 | 9.0477 | 9.05 | 1 | $70.0M |
| MONEX | 7.1415 | 7.1170 | 7.12 | 14 | $63.9M |
| SABADELL | 7.3642 | 7.3642 | 7.36 | 0 | $0 |

**BANCREA ME es caso extremo**: 10 filas tasa=0 suman $102M de portfolio, vs 1 sola fila con tasa=7.8% y $62M. El denominador de Tableau es ~2.6× mayor que el nuestro → tasa cae 62%.

## Análisis de Filas con Tasa = 0

Estas filas representan registros donde el banco tiene portfolio asignado en una combinación estado/tamaño/moneda pero no reporta tasa. Posibles causas:
- Créditos nuevos sin tasa efectiva calculada aún
- Registros de respaldo/fideicomiso sin interés
- Errores de reporte de la institución a CNBV

## Criterio de Validación

**Fuente de verdad**: Tableau. Los valores de las capturas son el target inmediato.

**Escenario OK**: Tras aplicar el fix, nuestros valores coinciden con los de las capturas (±0.02pp por redondeo de display).

**Escenario hipótesis alternativa**: Si post-fix algún valor NO coincide con la captura, la hipótesis plausible es que las capturas usan un data refresh diferente al CSV disponible en el repo. En ese caso:
1. Verificar si el CSV en PROD difiere del CSV en `drive-download-20260212T024209Z-1-001/`
2. Verificar si Tableau tiene filtros adicionales no detectados en el XML
3. Documentar la discrepancia residual con evidencia

## Estado Actual de Reproducción

Con el CSV del repo y el método Tableau, **todos los 10 valores de referencia de las capturas coinciden** (error < 0.02pp, atribuible a redondeo de display `p0.00%`):

| Valor | Captura | Reproducido | Match |
|-------|---------|-------------|-------|
| BANCREA MN | 13.5266% | 13.5266% | ✅ exacto |
| VE POR MAS MN | 13.4341% | 13.4341% | ✅ exacto |
| BANCO BASE MN | 13.1707% | 13.1707% | ✅ exacto |
| SABADELL MN | 13.0253% | 13.0253% | ✅ exacto |
| MONEX MN | 12.6951% | 12.6951% | ✅ exacto |
| BANCREA ME | 2.95% | 2.9481% | ✅ (redondeo) |
| BANCO BASE ME | 7.47% | 7.4674% | ✅ (redondeo) |
| INVEX ME | 9.05% | 9.0477% | ✅ (redondeo) |
| MONEX ME | 7.12% | 7.1170% | ✅ (redondeo) |
| SABADELL ME | 7.36% | 7.3642% | ✅ (redondeo) |

Esto da alta confianza en H3 pero no es prueba definitiva — el fix en PROD confirmará.

## Conclusión

La hipótesis principal (H3: denominador asimétrico por filas tasa=0) es **numéricamente consistente al 100%** con los valores de las capturas. Procedemos con el fix adoptando el método Tableau como fuente de verdad.
