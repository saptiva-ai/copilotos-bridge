# Plan: Fases 2-5 — Tableau Gap Backfill

**Fecha:** 2026-02-12
**Prerequisito:** Fase 0+1 completadas

---

## Resumen de impacto por fase

| Fase | Fuente | Worksheets desbloqueados | Prioridad |
|------|--------|-------------------------|-----------|
| 2 | CASTIGOS.xlsx | 6 (Quebrantos + IMORA fix) | ALTA |
| 3 | TDA.xlsx | 1 | MEDIA |
| 4 | CorporateLoan CSV + TE XLSX | 8 (Tasas + TE) | MEDIA |
| 5 | Schema additions | 4 (Reservas SG) | BAJA |

---

## Fase 2: CASTIGOS.xlsx (ALTA prioridad)

### Objetivo
Backfill `quebrantos_comerciales` y calcular castigos acumulados para corregir IMORA.

### Archivos fuente
- `CASTIGOS.xlsx` — castigos generales
- `Castigos Comerciales.xlsx` — detalle comercial con quitas

### Columnas a poblar
| Columna BD | Formula | Tipo |
|-----------|---------|------|
| `quebrantos_comerciales` | LIB_CASTIGOS_COMERC + QUITAS_COMER | currency |
| `castigos_acum` (nueva) | Running sum de castigos por banco | currency |
| `imora_tableau` (nueva) | (ET3_SG + castigos_acum) / (ET1+ET2+ET3)_SG | ratio |

### Pasos
1. EDA de CASTIGOS.xlsx — mapear columnas, periodos, instituciones
2. EDA de Castigos Comerciales.xlsx — identificar quitas por tipo
3. Crear `scripts/data/backfill_castigos.py`
4. Evaluar si `imora` existente debe sobreescribirse o crear columna separada
5. Dry-run + ejecucion + verificacion

### Riesgo
- Formula IMORA Tableau excluye gobierno y usa castigos acumulados. Nuestra IMORA actual es distinta.
- Decision: sobreescribir `imora` o crear `imora_tableau` separado.

---

## Fase 3: TDA.xlsx (MEDIA prioridad)

### Objetivo
Backfill `tda_cartera_total` y sub-segmentos.

### Pasos
1. EDA de TDA.xlsx — mapear columnas
2. Crear `scripts/data/backfill_tda.py`
3. Agregar viz config `tda` a `visualizations.yaml`
4. Evaluar si handler existente puede servir o necesita handler nuevo

### Notas
- TDA = Tasa De Activos. Es un ratio (no currency).
- TDA.xlsx contiene TDA por segmento (comercial, consumo, vivienda).
- Solo 1 worksheet Tableau depende de esto.

---

## Fase 4: Tasas (MEDIA prioridad)

### Objetivo
Backfill tasas MN/ME y tasa efectiva. Desbloquea 8 worksheets (el grupo mas grande pendiente).

### 4a. CorporateLoan_CNBVDB.csv
- **Estado**: Archivo NO confirmado en drive downloads disponibles
- **Accion**: Solicitar al equipo o buscar en otros directorios
- Columnas: `tasa_mn`, `tasa_me` (tasas promedio ponderadas MN/ME)
- 7 worksheets dependen de esto

### 4b. TE_Invex_Sistema.xlsx
- **Estado**: Archivo disponible en `tableau_extract/Data/INVEX ANALITICS/`
- Columnas: `tasa_sistema`, `tasa_invex_consumo`
- 1 worksheet depende de esto

### Pasos
1. Localizar CorporateLoan CSV
2. EDA de ambas fuentes
3. Crear scripts de backfill
4. Agregar viz configs y evaluar handlers nuevos

---

## Fase 5: Schema additions (BAJA prioridad)

### Objetivo
Agregar columnas nuevas a BD para metricas que no existen.

### Columnas nuevas necesarias
| Columna | Tipo | Formula | Fuente |
|---------|------|---------|--------|
| `res_empresarial` | currency | CNBV col 35 | CNBV XLSX |
| `res_consumo` | currency | CNBV col 38 | CNBV XLSX |
| `res_vivienda` | currency | CNBV col 39 | CNBV XLSX |
| `res_gubernamental` | currency | CNBV col 37 | CNBV XLSX |
| `ct_etapa_vr` | ratio | col6 / CT total | CNBV XLSX |
| `pe_sg` | ratio | -(Res - Res_Con - Res_Gub) / (CT - Con - Gub) | Calcular |
| `icor_sg` | ratio | (Res - Res_Con - Res_Gub) / CV | Calcular |

### Prerequisitos
- ALTER TABLE para agregar columnas
- Extender `backfill_cartera_total.py` con cols 35-39
- Datos ya descubiertos por EDA (cols 35-39, 99.9% cobertura)

### Worksheets desbloqueados
- RES_SG_Comparativo, RESSG_Mes, Res_Comparativo (SG), Res_Comparativo (G) sin gub

---

## Orden de ejecucion recomendado

```
Fase 2 (CASTIGOS) → mayor ROI: 6 worksheets + IMORA fix
  |
  v
Fase 3 (TDA) → rapido, 1 worksheet
  |
  v
Fase 4a (CorporateLoan) → depende de localizar CSV
  |
Fase 4b (TE_Invex) → independiente, archivo disponible
  |
  v
Fase 5 (Schema) → ultimo, depende de validacion Fases 2-4
```
