# Plan: ETL Data Documentation & Refresh Pipeline

**Date**: 2026-02-18
**Phases**: 5

---

## Phase 1: Documentacion del Esquema (Diagrama ER) — DONE

### Objetivo
Generar documentacion visual del modelo de datos: diagrama ER, catalogo de tablas, y mapeo fuente->tabla.

### Entregables
1. `docs/data/schema.md` — Catalogo completo del esquema con descripciones
2. `docs/data/er_diagram.mermaid` — Diagrama ER en Mermaid (renderizable en GitHub/Figma)
3. `docs/data/source_mapping.md` — Mapeo fuente cruda -> tabla destino

### Tareas
- [x] Extraer DDL de todas las tablas con `\d+` (ya explorado en research)
- [x] Generar diagrama ER en Mermaid con relaciones FK
- [x] Documentar cada tabla: columnas, tipos, indices, FKs, cardinalidad
- [x] Documentar cobertura temporal por tabla (ultimo periodo disponible)
- [x] Mapear cada archivo crudo (Google Drive) a su tabla destino

### Archivos creados
```
docs/data/
├── schema.md               ← Catalogo de tablas
├── er_diagram.mermaid      ← Diagrama ER (Mermaid)
├── source_mapping.md       ← Fuente → Tabla
└── etl_flow.mermaid        ← Diagrama de flujo ETL
```

---

## Phase 2: ETL Refresh Orchestrator (`make etl-refresh`) — DONE

### Objetivo
Crear un comando unico que actualice todos los datos a un periodo nuevo.

### Componentes creados
1. **`etl/core/refresh_orchestrator.py`** — Orquestador con 7 fases
   - `RefreshOrchestrator.run()` — pipeline completo
   - CLI: `python -m etl.core.refresh_orchestrator --incoming <dir> [--dry-run] [--min-periodo YYYYMM]`
2. **`etl/core/period_detector.py`** — Deteccion de gaps
   - `PeriodDetector.detect_gaps(target)` -> `GapReport`
   - `PeriodDetector.check_freshness()` — auto-detect target
3. **Makefile targets**: `etl-refresh`, `etl-freshness`

### Tareas
- [x] Crear `refresh_orchestrator.py` con las 7 fases
- [x] Crear `period_detector.py` para deteccion de gaps
- [x] Agregar target `etl-refresh` al Makefile
- [x] Agregar `--min-periodo` flag para carga incremental
- [ ] Tests unitarios para deteccion de periodos (pendiente para validacion)

---

## Phase 3: Loaders Incrementales para Tablas Grandes — DONE

### Objetivo
Los loaders de tablas grandes ahora soportan `min_periodo` para carga incremental.

### Loaders modificados (7/7)
1. [x] `loaders_analisis_general.py` — `min_periodo` + `filter_min_periodo` + `incremental_delete`
2. [x] `loaders_banca_multiple.py` — idem
3. [x] `loaders_cartera_comercial.py` — idem (6 tablas)
4. [x] `loaders_cartera_vivienda.py` — idem
5. [x] `loaders_reportes_reg.py` — idem (R04A + R12A)
6. [x] `loaders_benchmark.py` — idem (periodo INTEGER)
7. [x] `loaders_tda_etapas.py` — idem (cve_periodo INTEGER)

### Helpers creados
- `helpers.py:filter_min_periodo()` — filtra LazyFrame por periodo >= X
- `helpers.py:filter_min_periodo_df()` — filtra DataFrame por periodo >= X
- `helpers.py:incremental_delete()` — DELETE WHERE periodo >= X

### Tareas
- [x] Agregar `min_periodo` a cada loader
- [x] Crear helpers `filter_min_periodo` e `incremental_delete`
- [x] Conectar orquestador -> loaders via `min_periodo`
- [ ] Crear helper `ensure_partition_exists(table, year)` (pendiente — particiones 2026 se crean manual por ahora)

---

## Phase 4: Migracion de Scripts R -> SQL — DONE

### CorporateLoan_BM.R -> Ya cubierto
- `loaders_unified.py:load_corporate_loan()` reemplaza completamente el script R
- Documentado en `source_mapping.md`

### Castigos_BM.R -> Vista SQL
- Creada migracion `060_create_view_castigos_comerciales.sql`
- **`bank_view_castigos_comerciales`**: formato largo (13 conceptos x institucion x periodo)
- **`bank_view_castigos_netos_comerciales`**: castigos - recuperaciones agregados
- Usa columnas reales de la tabla: `institucion`, `importe_pesos`, `moneda` (INTEGER)

### Tareas
- [x] Documentar que CorporateLoan_BM.R esta cubierto por ETL existente
- [x] Crear vista SQL `bank_view_castigos_comerciales` (migracion 060)
- [x] Crear vista agregada `bank_view_castigos_netos_comerciales`
- [ ] Ejecutar migracion 060 en GCP (requiere `psql -f`)
- [ ] Test de equivalencia: comparar output del script R vs vista SQL

---

## Phase 5: Validacion y Documentacion Final — DONE (docs)

### Objetivo
Documentar el pipeline completo y crear guia operativa.

### Tareas
- [ ] Dry-run del refresh orchestrator con datos de Dic 2025
- [ ] Ejecutar carga real de periodos faltantes (Nov-Dic 2025)
- [ ] Verificar MVs actualizadas y freshness OK
- [ ] Completar `validate.md` con resultados
- [x] Actualizar `docs/data/source_mapping.md` con estado actualizado de scripts R
- [x] Crear `docs/data/etl_runbook.md` — guia operativa para agregar datos

---

## Resumen de Estado

| Phase | Descripcion | Estado | Pendiente |
|-------|-------------|--------|-----------|
| 1 | Documentacion ER | DONE | — |
| 2 | Refresh Orchestrator | DONE | Tests unitarios |
| 3 | Loaders Incrementales | DONE | Particiones 2026+ |
| 4 | Migracion R -> SQL | DONE | Ejecutar 060 en GCP, test equivalencia |
| 5 | Validacion y Docs | PARTIAL | Dry-run, carga real, validate.md |

## Para Completar la Tarea

1. Ejecutar migracion 060 en GCP: `psql $DATABASE_URL -f migrations/060_create_view_castigos_comerciales.sql`
2. Crear particiones 2026 si hay datos nuevos (ver runbook)
3. `make etl-refresh DRY=1` para verificar pipeline
4. `make etl-refresh INCOMING=<dir> PERIODO=<target>` para carga real
5. `make etl-freshness` para verificar resultado
6. Completar `validate.md` con resultados
