# Plan: CVC/CC — Cartera Vencida Comercial sin Castigos

## Phase 0: Migracion SQL + ORM (PARCIAL — ORM listo, migracion sin desplegar)

### Objetivo
Agregar columna `cvc_cc` a `bank_fact_kpis_mensual` y actualizar MVs.

### Estado
- ORM: `cvc_cc = Column(Float, nullable=True)` ya existe en `models/kpi.py:47`
- SQL: `migrations/059_add_cvc_cc.sql` ya escrita (344 lineas)
  - Paso 1: ALTER TABLE ADD COLUMN cvc_cc
  - Paso 2: Recrear MV evolucion (+ cvc_cc YoY/MoM)
  - Paso 3: Recrear MV ranking (+ ranking_cvc_cc)
  - Paso 4: Recrear MV comparativa (+ cvc_cc)
  - Paso 5: ANALYZE + verificacion

### Pendiente
- Desplegar migracion en PROD via `scripts/deploy_059_cvc_cc.py`

### Validacion
- `SELECT column_name FROM information_schema.columns WHERE table_name = 'bank_fact_kpis_mensual' AND column_name = 'cvc_cc'`


## Phase 1: Loader — computar CVC/CC (PENDING)

### Objetivo
Agregar formula CVC/CC al loader existente y re-ejecutar carga.

### Archivos
- `plugins/bank-advisor-private/etl/core/loaders/loaders_imor_comercial.py`

### Detalle

1. Agregar funcion pura:
   ```python
   def compute_cvc_cc(e1_sg: float, e2_sg: float, e3_sg: float) -> float | None:
       """CVC/CC Sin Gobierno: E3_SG / (E1_SG + E2_SG + E3_SG). Sin castigos."""
       denom = e1_sg + e2_sg + e3_sg
       if denom <= 0:
           return None
       return e3_sg / denom
   ```

2. En `load_xlsx_sg()`, agregar despues de linea 162:
   ```python
   agg["cvc_cc"] = agg.apply(
       lambda r: compute_cvc_cc(r["e1_sg"], r["e2_sg"], r["e3_sg"]),
       axis=1,
   )
   ```

3. Actualizar return para incluir `cvc_cc`:
   ```python
   return agg[["institucion_code", "periodo", "imor_comercial", "cvc_cc"]]
   ```

4. En `upsert_to_db()`, agregar cvc_cc al UPDATE/INSERT.

### Validacion
- `python3.11 -m pytest -q plugins/bank-advisor-private/tests/unit/domain/test_cvc_cc_computation.py`
- Dry run: `python3.11 -m etl.core.loaders.loaders_imor_comercial --xlsx PATH --castigos PATH --db-url URL --dry-run`


## Phase 2: Tests unitarios (PARCIAL — archivo existe, contenido pendiente)

### Objetivo
TDD: tests de formula CVC/CC con datos de referencia de Tableau.

### Archivos
- `plugins/bank-advisor-private/tests/unit/domain/test_cvc_cc_computation.py` (EXISTE)

### Detalle

Tests a incluir:
1. `test_cvc_cc_formula_basic` — E3/(E1+E2+E3) sin castigos
2. `test_cvc_cc_zero_denominator` — retorna None
3. `test_cvc_cc_is_ratio` — resultado entre 0 y 1
4. `test_cvc_cc_ignores_castigos` — mismo resultado con o sin castigos
5. `test_cvc_cc_vs_imora_differ_when_castigos` — CVC/CC < IMORA cuando castigos > 0
6. Parametrized: 10 bancos x Tableau reference match (01/2025)

Datos de referencia (Tableau 01/2025):
```python
TABLEAU_CVC_CC = {
    40042: 1.23,   # BANCA MIFEL
    40059: 2.36,   # INVEX
    40060: 5.67,   # BANSI
    40062: 4.43,   # AFIRME
    40112: 1.58,   # MONEX
    40113: 3.51,   # VE POR MAS
    40132: 4.33,   # MULTIVA
    40145: 2.87,   # BANCO BASE
    40152: 0.80,   # BANCREA
    40156: 2.58,   # SABADELL
}
```


## Phase 3: Routing + MetricNormalizer (DONE)

### Estado: COMPLETADO (en branch develop, sin commit)

Ya implementado en los siguientes archivos:

| Archivo | Cambio | Linea |
|---------|--------|-------|
| `template_sql_generator.py` | `"hip_cvc_cc": {"table": "bank_fact_kpis_mensual", ...}` | :56 |
| `metric_normalizer.py` | `hip_cvc_cc` en lista de ratio metrics | :53 |
| `comparison_tools.py` | `hip_cvc_cc` en enum del LLM tool | :234 |
| `evolucion_banco_handler.py` | 9 keyword mappings → `hip_cvc_cc` | :155-164 |
| `evolution.py` (use case) | `_HIP_TO_COLUMN["hip_cvc_cc"] = "cvc_cc"` | :586 |
| `peer_average.py` (use case) | `hip_cvc_cc` mapping + display name | :23, :357 |

Keywords registrados en handler:
- "razon de cartera vencida sobre cartera comercial" → hip_cvc_cc
- "cartera vencida sobre cartera comercial" → hip_cvc_cc
- "razon de cartera vencida comercial" → hip_cvc_cc
- "cartera vencida comercial" → hip_cvc_cc
- "cartera vencida sobre comercial" → hip_cvc_cc
- "razon de cartera vencida" → hip_cvc_cc
- "vencida comercial" → hip_cvc_cc
- "cvc/cc" → hip_cvc_cc
- "cvc cc" → hip_cvc_cc


## Phase 4: Prompts onboarding (PENDING)

### Objetivo
Reescribir los 2 prompts de "Cartera Vencida Comercial" para calzar con las
vistas de Tableau.

### Archivos
- `apps/web/src/components/chat/help-onboarding-content.ts` (lineas 261-286)

### Detalle

#### Preset 1: Ranking CVC/CC (id: cartera-vencida-comercial-ranking)

**Antes** (MAL — pide variacion entre dos periodos, ruta a `_handle_period_delta`):
```
Toma como periodo inicial enero 2024 y como periodo actual enero 2025.
Compara la razon de cartera vencida comercial entre la cartera comercial...
Done la variacion es = (periodo actual / periodo inicial -1)
Haz una grafica de barras... tabla con: Banco | CVC/CC 2024 | CVC/CC 2025 | % Variacion
```

**Despues** (BIEN — snapshot un solo periodo, ruta a `_handle_hip_snapshot`):
```
Muestra la razon de cartera vencida comercial entre la cartera comercial
para enero 2025 para los bancos:
MONEX, INVEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI,
VE POR MAS Y BANCO BASE.
Haz una grafica de barras horizontales ordenadas de mayor a menor y marca
a INVEX de color rojo.
Incluye una tabla con: Banco | CVC/CC 01/2025
```

**Por que funciona**: Al no tener "periodo inicial... periodo actual", el parser
`_parse_period_comparison()` no matchea, y el flujo cae en la rama `hip_` (linea 404)
que llama a `_handle_hip_snapshot()` con el periodo_id extraido del query.

#### Preset 2: INVEX vs Promedio (id: cartera-vencida-comercial-invex-promedio)

**Antes** (parcialmente bien, pero periodo incorrecto):
```
Crea una grafica donde se compare la razon de cartera vencida sobre cartera comercial
de INVEX contra el promedio de los bancos: ...
De enero 2024 hasta el dato mas reciente que tengas.
```

**Despues** (periodo corregido a 10/2022 como en Tableau):
```
Crea una grafica donde se compare razon de cartera vencida comercial entre
la cartera comercial de INVEX contra el promedio de los bancos:
MONEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI,
VE POR MAS Y BANCO BASE.
De octubre 2022 hasta el dato mas reciente que tengas.
```

**Cambios clave**:
1. "cartera vencida sobre cartera comercial" → "cartera vencida comercial entre la cartera comercial" (calza mejor con keywords del handler)
2. "enero 2024" → "octubre 2022" (para capturar historia completa como en Tableau)


## Phase 5: Carga de datos + validacion E2E (PENDING)

### Objetivo
Re-ejecutar carga para poblar `cvc_cc` en todos los periodos y validar E2E.

### Detalle

1. Ejecutar loader con `--dry-run` primero
2. Ejecutar carga real (UPSERT agrega cvc_cc a rows existentes)
3. `REFRESH MATERIALIZED VIEW CONCURRENTLY bank_mv_evolucion_cartera_banco`
4. `REFRESH MATERIALIZED VIEW CONCURRENTLY bank_mv_ranking_cartera_mensual`
5. `REFRESH MATERIALIZED VIEW CONCURRENTLY bank_mv_comparativa_bancos`
6. Correr E2E:
   - `python3.11 tests/e2e/charts/test_cvc_cc_snapshot_bar_chart.py`
   - `python3.11 tests/e2e/charts/test_peer_avg_cvc_cc_chart.py`
   - Verificar que los 10 bancos aparecen con valores correctos

### Validacion final
- 10/10 bancos match Tableau (±0.01pp)
- Promedio = 2.94%
- BANCA MIFEL = 1.23% (no 1.25% que daria IMORA)
- VE POR MAS = 3.51% (no 3.52% que daria IMORA)
- Preset ranking: barras horizontales, snapshot, INVEX rojo
- Preset INVEX vs promedio: time series desde 10/2022, 2 lineas


## Orden de ejecucion

```
Phase 0 (deploy migracion)
    ↓
Phase 1 (loader + carga) ← Phase 2 (unit tests) en paralelo
    ↓
Phase 4 (prompts onboarding) — puede hacerse en paralelo con Phase 1
    ↓
Phase 5 (E2E validacion)
```

Phase 3 ya esta DONE.


## Dependencias

- **Requiere**: BUG-2026-02-16__imor-comercial-etapa3-data-gap completado (ya done)
- **No bloquea**: otros tickets (cambio aditivo)

## Riesgos

- **Bajo**: Cambiar el mapping de "cartera vencida comercial" de hip_imor_comercial a hip_cvc_cc
  podria afectar queries existentes que esperan IMORA. Mitigacion: hip_imor_comercial sigue
  existiendo para "imor comercial" / "imora".
- **Bajo**: Sin datos cargados, los prompts se rutean correctamente pero devuelven
  "No se encontraron datos". La carga es prerequisito para que funcione end-to-end.
