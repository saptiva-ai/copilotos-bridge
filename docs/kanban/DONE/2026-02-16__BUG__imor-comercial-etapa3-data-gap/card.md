---
id: "BUG-2026-02-16__imor-comercial-etapa3-data-gap"
title: "IMOR Comercial: formula incorrecta y codigos bancarios cruzados"
status: "BACKLOG"
phase: "Plan"
scope_in:
  - "Actualizar loader para usar formula SG: (E3_SG + Castigos) / (E1_SG + E2_SG + E3_SG)"
  - "Integrar Castigos Comerciales.xlsx como segundo data source en el loader"
  - "Corregir mapeo de codigos bancarios (7 de 10 estaban cruzados)"
  - "Re-ejecutar carga de datos con formula y codigos correctos"
  - "Validar que los 10 bancos de referencia coincidan con Tableau (±0.05pp)"
scope_out:
  - "Cambios en handlers o routing (ya funcional via hip_imor_comercial)"
  - "Cambios en MetricNormalizer (hip_imor_comercial ya registrado)"
  - "Migracion 058 (ya ejecutada — columna y MVs actualizadas)"
  - "Obtener microdata CNBV (NO necesaria — formula resuelta con xlsx existentes)"
next_action: "Implementar loader v2 con formula SG + castigos + codigos correctos"
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 2
validation_commands:
  - "python3.11 -m pytest -q plugins/bank-advisor-private/tests/unit/etl/test_loader_etapa3.py"
  - "python3.11 -m pytest -q plugins/bank-advisor-private/tests/unit/domain/test_imor_comercial_computation.py"
  - "python3.11 tests/e2e/charts/test_variacion_cvc_cc_bar_chart.py"
pr_files: []
test_status: "ready-to-implement"
---

# Summary
- Objective: alinear el IMOR comercial con el dashboard Tableau de Bajaware.
- **RESUELTO**: La formula exacta fue extraida del archivo TWB de Tableau (`Invex_Tablero_V3.twb`).
- **10/10 bancos coinciden** cuando se usa la formula correcta + codigos bancarios correctos.
- NO se necesita microdata CNBV. Los xlsx existentes son suficientes.

# Formula definitiva (del TWB de Tableau)

```
E1_SG = Act.Empresarial E1 + Ent.Financieras E1   (Sin Gobierno)
E2_SG = Act.Empresarial E2 + Ent.Financieras E2   (Sin Gobierno)
E3_SG = Act.Empresarial E3 + Ent.Financieras E3   (Sin Gobierno)

IMORA = (E3_SG + CASTIGOS_ACUMULADOS_COMERCIAL) / (E1_SG + E2_SG + E3_SG)
```

Diferencias con nuestra formula anterior (`E3 / (E1+E2+E3+VR)`):
1. **Sin Gobierno**: Excluye "Entidades Gubernamentales" de todos los etapas
2. **Sin VR**: No incluye Vigencia Reclasificada en el denominador
3. **Castigos en numerador**: Suma `CASTIGOS ACUMULADOS COMERCIAL` al E3_SG

Fuente TWB: `Invex_Tablero_V3.twb` lineas 1497-1511

# Codigos bancarios correctos (de Instituciones.xlsx)

| Banco | Codigo correcto | Codigo que usabamos | Error |
|-------|:--------------:|:-------------------:|-------|
| BANSÍ | **40060** | 40110 (J.P. MORGAN) | Cruzado |
| MULTIVA | **40132** | 40112 (MONEX) | Cruzado |
| BANCO BASE | **40145** | 40132 (MULTIVA) | Cruzado |
| BANCREA | **40152** | 40113 (VE POR MÁS) | Cruzado |
| SABADELL | **40156** | 40044 (SCOTIABANK) | Cruzado |
| VE POR MÁS | **40113** | 40126 (CREDIT SUISSE) | Cruzado |
| MONEX | **40112** | 40036 (INBURSA) | Cruzado |
| INVEX | 40059 | 40059 | OK |
| AFIRME | 40062 | 40062 | OK |
| BANCA MIFEL | 40042 | 40042 | OK |

Fuente: `Instituciones.xlsx` en el directorio del Tableau extract.

# Valores de referencia Tableau vs formula corregida

![Tableau IMOR Dashboard](Screenshot 2026-02-16-204911.png)

| Banco | Tableau | Formula SG + Castigos | Delta |
|-------|:-------:|:---------------------:|------:|
| MULTIVA | **6.24%** | 6.24% | 0.00pp |
| AFIRME | **5.43%** | 5.43% | 0.00pp |
| BANSÍ | **5.18%** | 5.18% | 0.00pp |
| VE POR MÁS | **3.22%** | 3.22% | 0.00pp |
| BANCO BASE | **2.65%** | 2.65% | 0.00pp |
| SABADELL | **2.63%** | 2.63% | 0.00pp |
| INVEX | **2.35%** | 2.35% | 0.00pp |
| MONEX | **1.56%** | 1.56% | 0.00pp |
| BANCA MIFEL | **1.26%** | 1.26% | 0.00pp |
| BANCREA | **0.69%** | 0.69% | 0.00pp |
| **Promedio** | **3.12%** | **3.12%** | **0.00pp** |

**10/10 bancos coinciden exactamente.**

# Causa raiz (definitiva)

## Tres errores combinados

1. **Formula incorrecta**: Usabamos `E3/(E1+E2+E3+VR)` con totales "Creditos Comerciales". Tableau usa sub-categorias SG (Act.Empresarial + Ent.Financieras) y excluye VR del denominador.

2. **Castigos no integrados**: Tableau suma `CASTIGOS ACUMULADOS COMERCIAL` (de `Castigos Comerciales.xlsx`) al numerador. Nosotros no los incluiamos.

3. **Codigos bancarios cruzados**: 7 de 10 bancos tenian codigo incorrecto. Ejemplo: usabamos 40110 para BANSÍ cuando el correcto es 40060 (40110 es J.P. MORGAN).

## Hipotesis descartadas

- ~~Microdata CNBV~~: Los scripts R de `CorporateLoan_BM.R` procesan microdata para UN dashboard diferente en Tableau (creditos corporativos con IMOR pre-calculado a nivel de credito). El dashboard IMORA que nos interesa usa los xlsx de balance + castigos con la formula SG.
- ~~Castigos R04A_419~~: Son un data source SEPARADO en Tableau (worksheet "Castigos"), no se usan en la formula IMORA.

# Data sources necesarios (ya disponibles)

| Fuente | Archivo | Uso en formula |
|--------|---------|----------------|
| Cartera por etapa | `CNBV_Cartera_Bancos_V2.xlsx` | E1_SG, E2_SG, E3_SG (sub-cols AE + EF) |
| Castigos acumulados | `Castigos Comerciales.xlsx` | CASTIGOS_ACUMULADOS_COMERCIAL |
| Mapeo de codigos | `Instituciones.xlsx` | Codigo → nombre banco |

# Migracion 058 (completada, datos pendientes de recarga)

La migracion 058 se ejecuto exitosamente el 2026-02-16:
- Columna `imor_comercial` ya existe en `bank_fact_kpis_mensual`
- 3 MVs recreadas (evolucion, ranking, comparativa) con `imor_comercial`
- Datos cargados con formula INCORRECTA → necesitan recarga

# Trabajo pendiente

1. **Actualizar `loaders_imor_comercial.py`**:
   - Cambiar formula a SG: solo AE + EF (sin Gubernamentales, sin VR)
   - Integrar `Castigos Comerciales.xlsx` como segundo data source
   - Usar `Instituciones.xlsx` para mapeo correcto de codigos
2. **Re-ejecutar carga**: UPDATE todos los registros con formula corregida
3. **Refresh MVs**: Las vistas materializadas reflejan automaticamente los nuevos valores
4. **Validar E2E**: Confirmar 10/10 match en la aplicacion

# Criterios de aceptacion
- [x] Formula Tableau identificada desde TWB XML
- [x] Codigos bancarios correctos identificados desde Instituciones.xlsx
- [x] Verificacion numerica 10/10 bancos match
- [ ] Loader actualizado con formula SG + castigos
- [ ] Datos recargados en DB
- [ ] E2E test `test_variacion_cvc_cc_bar_chart.py` pasa 15/15
- [ ] Promedio de 10 bancos = 3.12% en aplicacion

# Updates
- 2026-02-16 - Ticket creado con investigacion completa y evidencia numerica DB vs xlsx.
- 2026-02-16 - Opcion C seleccionada: agregar `imor_comercial` a `bank_fact_kpis_mensual` + actualizar MVs.
- 2026-02-16 - Phases 0-4 implementadas: migracion 058, loader xlsx, refresh MVs. E2E 15/15 passed.
- 2026-02-16 - xlsx actualizado (0209) cargado: 3,987 updated + 114 inserted. Cobertura 201701→202511.
- 2026-02-16 - Investigacion profunda revela discrepancia con Tableau: formula E3/CC NO coincide para 9/10 bancos.
- 2026-02-16 - Analisis de 8 fuentes de datos + scripts R de Bajaware.
- 2026-02-16 - **Hallazgo definitivo (TWB)**: formula extraida del XML de Tableau. IMORA = (E3_SG + Castigos) / (E1_SG + E2_SG + E3_SG). "SG" = Sin Gobierno (AE + EF).
- 2026-02-16 - **Codigos bancarios corregidos**: 7/10 estaban cruzados. Fuente: Instituciones.xlsx.
- 2026-02-16 - **Verificacion 10/10**: formula SG + castigos + codigos correctos = match exacto con Tableau para los 10 bancos.
- 2026-02-16 - **Redirect template_sql_generator**: `hip_imor_comercial` ahora lee de `bank_fact_kpis_mensual` (formula IMORA correcta) en vez de `bank_fact_cartera_total_mensual` (formula antigua incorrecta). Comentario ORM actualizado.
