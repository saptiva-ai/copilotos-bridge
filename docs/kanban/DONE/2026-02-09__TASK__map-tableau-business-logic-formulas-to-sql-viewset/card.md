# TASK: Map Tableau business logic formulas to SQL views/ETL transforms

**Prioridad:** P2
**Fecha:** 2026-02-09
**Status:** DONE

---

## Resumen

## Problem

The Tableau workbook `Invex_Tablero_V3.twb` contains ~60 calculated fields that define how Bajaware/Invex computes key banking metrics (IMORA, ICOR, PE, TDA, Quebrantos, Etapa composition). These are the **canonical business rules** but they exist only in the Tableau XML — our ETL and analytics_service compute some of these independently, risking formula divergence.

## Research

### Key formulas extracted from Tableau

**Risk metrics:**
- `IMORA = (Comercial_ET3_SG + Castigos_Acum) / (ET1_SG + ET2_SG + ET3_SG)` — "SG" means Sin Gobierno (excl. government)
- `ICOR = Reservas_SG / Cartera_Vencida` (coverage ratio)
- `PE Total = Reservas_Todas × (-1) / Cartera_Total`
- `PE Total SG = (Reservas - Res_Gub - Res_Consumo) × (-1) / Cartera_Total`

**Portfolio aggregations:**
- `Cartera Comercial Total = Empresarial + Ent_Financieras + Ent_Gubernamentales`
- `Cartera Comercial SG = Empresarial + Ent_Financieras` (excl. Gubernamentales)
- `Cartera Total = Comercial + Consumo + Vivienda`
- Each segment sums 4 Etapas: `Empresarial = ET1 + ET2 + ET3 + VR`

**Etapa composition (% of total):**
- `CT_Etapa1 = (Comercial_ET1 + Consumo_ET1 + Vivienda_ET1) / Cartera_Total`
- Similar for Etapa 2, 3

**Quebrantos:**
- `Quebrantos CC = LIB_CASTIGOS_COMERC + QUITAS_COMER`
- `Castigos Acumulados = RUNNING_SUM(SUM(LIB_CASTIGOS_COMERC))`

**Rates (CorporateLoan):**
- `Tasa Prom Pond = SUM(Portfolio × Rate) / SUM(Portfolio)` (weighted average)
- `TDA = Non_Performing / Total_Portfolio`

**Invex-specific pattern:**
- Every metric has `IF DESCRIPCION = 'INVEX' THEN <metric> ELSE 0/NULL END`

### Differences vs current ETL
- Our `analytics_service` computes `imor` as `cartera_vencida / cartera_total` but Tableau uses the IMORA formula (includes castigos acumulados in numerator and excludes Gubernamentales)
- "Sin Gobierno" segmentation (excluding Ent_Gubernamentales) is a key Tableau pattern not reflected in our current transforms
- PE (Pérdida Esperada) has two variants in Tableau: PE Total and PE Total SG — we only compute one
- Etapa composition uses the same denominators but our transforms may not match exactly

## Plan

1. Create a reference document `docs/context/TABLEAU_FORMULAS.md` mapping each Tableau calc → our SQL/Python equivalent
2. Identify divergences between Tableau formulas and `analytics_service` computations
3. Create SQL views or transform functions that match Tableau formulas exactly
4. Priority: IMORA and PE formulas (most user-facing metrics)

## Testing

- Cross-validate: run Tableau formula manually against prod data for INVEX 2025-06 and compare with analytics_service output
- Unit tests for each formula implementation

---

## Criterios de Aceptación

- [ ] TODO

---

## Referencias

- N/A
