# Research: Análisis de MVs y Tablas Fact/Dim

## Resumen Ejecutivo

**Hallazgo Principal**: Los datos regionales **SÍ EXISTEN** en `bank_mv_cartera_por_estado`, pero el sistema no los utiliza correctamente. El LLM alucinó datos regionales cuando debía usar la MV.

---

## 1. Inventario de Vistas Materializadas

| MV | Tamaño | Propósito | Estado |
|----|--------|-----------|--------|
| `bank_mv_cartera_por_estado` | 10 MB | **Desglose regional/estado** | ✅ Existe, **subutilizada** |
| `bank_mv_cartera_por_actividad` | 1.6 MB | Por actividad económica | ✅ Funcional |
| `bank_mv_vivienda_por_perfil` | 1.3 MB | Por demografía vivienda | ✅ Funcional |
| `bank_mv_evolucion_cartera_banco` | 1.2 MB | Series temporales | ✅ Funcional |
| `bank_mv_cartera_por_destino` | 472 kB | Por destino crédito | ✅ Funcional |
| `bank_mv_cartera_por_tamano` | 448 kB | Por tamaño empresa | ✅ Funcional |
| `bank_mv_vivienda_por_producto` | 336 kB | Por producto hipotecario | ✅ Funcional |
| `bank_mv_metricas_financieras` | 64 kB | ROA, ROE, etc. | ✅ Funcional |
| `bank_mv_resumen_sistema` | 64 kB | Totales sistema | ✅ Funcional |
| `bank_mv_comparativa_bancos` | 16 kB | Comparativos | ✅ Funcional |
| `bank_mv_ranking_cartera_mensual` | 8 kB | Rankings mensuales | ✅ Funcional |

---

## 2. Inventario de Tablas Fact/Dim

### Tablas Fact (grandes)

| Tabla | Tamaño | Propósito |
|-------|--------|-----------|
| `bank_fact_cartera_comercial` | **2.5 GB** | Detalle crédito comercial |
| `bank_fact_cartera_vivienda` | 627 MB | Detalle crédito vivienda |
| `bank_fact_cartera_comercial_marginal` | 626 MB | Variaciones marginales |
| `bank_fact_kpis_mensual` | 1.9 MB | KPIs agregados mensuales |
| `bank_fact_cartera_segmentada` | 744 kB | Segmentos de cartera |

### Tablas Dim (dimensiones)

- `bank_dim_institucion` - 121 instituciones
- `bank_dim_periodo` - Periodos temporales
- `bank_dim_estado` - Entidades federativas + regiones
- `bank_dim_actividad_economica` - Actividades económicas
- `bank_dim_tamano_empresa` - Tamaños de empresa
- `bank_dim_destino_credito` - Destinos de crédito
- 5 más...

---

## 3. Problema Identificado: Alucinación Regional

### Datos Reales vs Alucinados (INVEX Oct 2025)

**Datos REALES en `bank_mv_cartera_por_estado`:**

| Región | Saldo (MDP) | % |
|--------|-------------|---|
| Centro | 5,944.93 | 40.5% |
| Centro-Occidente | 3,156.34 | 21.5% |
| Sureste | 2,928.82 | 19.9% |
| Norte | 2,653.88 | 18.1% |
| **Total** | **14,684** | **100%** |

**Datos ALUCINADOS por el LLM:**

| Región | Saldo (MDP) | % |
|--------|-------------|---|
| Centro | 7,745.10 | 47.2% |
| Occidente | 4,471.86 | 27.3% |
| Norte | 3,249.78 | 19.8% |
| Sur | 1,935.84 | 11.8% |
| Sureste | 1,243.88 | 7.6% |
| **Total** | **18,646** | **113.7%** |

**Errores:**
- Total: +27% de diferencia (18.6B vs 14.7B real)
- Porcentajes suman 113.7% (imposible)
- Regiones inventadas ("Occidente", "Sur")
- 5 regiones vs 4 reales

---

## 4. Análisis de Causa Raíz

### Flujo Actual

```
Usuario: "Saldo por entidad federativa a Oct 2025"
    │
    ├── QueryRouter.route()
    │   ├── check_fundamental_ambiguity() → No match
    │   ├── handlers[0].matches() → MultiMetricHandler → No
    │   ├── handlers[1].matches() → MetricasFinancieras → No
    │   ├── ...
    │   └── handlers[8].matches() → CarteraRegionHandler → ???
    │
    └── FSM: _determine_routing_transition()
        ├── is_knowledge_query → No
        ├── can_use_fast_path → ???
        └── route_to_nl2sql ← PROBLEMA
```

### Posibles Causas

1. **Handler no matchea la query**:
   - `CarteraRegionHandler.matches()` usa regex con word boundaries
   - "entidad federativa" DEBERÍA matchear, pero hay que verificar

2. **`can_use_fast_path` retorna False**:
   - Si no detecta métrica + banco, no usa fast path
   - "Saldo" no es una métrica conocida

3. **NL2SQL no conoce la MV**:
   - El SQL generado usa `monthly_kpis`, no `bank_mv_cartera_por_estado`
   - El LLM no tiene el schema de la MV regional

### Evidencia del Metadata

```json
{
  "sql_generated": "SELECT fecha, banco_norm, cartera_comercial_total AS value
                    FROM monthly_kpis WHERE banco_norm IN ('INVEX')",
  "intent": "evolution"
}
```

- Intent detectado: `evolution`, no `regional`
- Tabla usada: `monthly_kpis`, no `bank_mv_cartera_por_estado`

---

## 5. Handler Existente: CarteraRegionHandler

**Ubicación**: `plugins/bank-advisor-private/src/bankadvisor/handlers/cartera_region_handler.py`

**Keywords que matchea**:
```python
REGION_KEYWORDS = {
    "por región": None,
    "regional": None,
    "por estado": None,
    "por entidad": None,
    "entidad federativa": None,  # ← DEBERÍA MATCHEAR
    "entidades federativas": None,
    "norte": "Norte",
    "sur": "Sur",
    "centro": "Centro",
    ...
}
```

**Métodos de AnalyticsService disponibles**:
- `get_cartera_por_region_ranking()` - Ranking por región
- `get_cartera_region_breakdown()` - Desglose por región
- `get_cartera_region_comparison()` - Comparativo YoY
- `get_cartera_estado_evolution()` - Evolución por estado

---

## 6. Recomendaciones

### Opción A: Fix del Handler Matching (Recomendado)

1. **Verificar que el handler matchea correctamente**:
   - Agregar test específico para "Saldo por entidad federativa"
   - Verificar regex con word boundaries

2. **Mejorar detección de intent regional**:
   - Agregar "saldo por" + keyword regional = intent regional
   - No depender solo de keywords aislados

### Opción B: Mejorar NL2SQL

1. **Agregar schema de MV regional al prompt**:
   - Incluir `bank_mv_cartera_por_estado` en el context
   - Instruir al LLM a usar esta MV para queries regionales

2. **Validar SQL generado**:
   - Si query pide regional pero SQL no usa MV regional → error

### Opción C: Grounding Constraint (Anti-alucinación)

1. **Validar respuesta vs datos disponibles**:
   - Si LLM genera datos que no existen en la respuesta del bank-advisor → rechazar
   - Forzar respuesta: "Datos regionales no disponibles"

---

## 7. Queries SQL Útiles

```sql
-- Verificar datos regionales para un banco
SELECT
    region,
    SUM(saldo_total)/1e6 as saldo_mdp,
    ROUND((SUM(saldo_total) / SUM(SUM(saldo_total)) OVER() * 100)::numeric, 1) as pct
FROM bank_mv_cartera_por_estado
WHERE UPPER(banco) = 'INVEX' AND fecha = '2025-10-01'
GROUP BY region
ORDER BY saldo_mdp DESC;

-- Verificar cobertura temporal
SELECT MIN(fecha), MAX(fecha) FROM bank_mv_cartera_por_estado;

-- Verificar bancos disponibles
SELECT DISTINCT banco FROM bank_mv_cartera_por_estado ORDER BY banco;
```

---

## 8. Verificación de Routing

### Test de Handler Matching

```python
# La query "Saldo por entidad federativa a Oct 2025" matchea correctamente
import re
REGION_KEYWORDS = {"entidad federativa": None, "por entidad": None, ...}
query = "Saldo por entidad federativa a Oct 2025"

for keyword in REGION_KEYWORDS.keys():
    pattern = r'\b' + re.escape(keyword) + r'\b'
    if re.search(pattern, query.lower()):
        print(f"Match: {keyword}")  # Output: "Match: por entidad"
```

**El handler SÍ matchea la query.** Entonces, ¿por qué no se usó?

### Flujo de Decisión en FSM

```
QueryModel.can_use_fast_path:
  ├── Option 1: entities.metric_id + (banks OR ranking)
  │   └── "Saldo" no es una métrica conocida → metric_id = None → FAIL
  │
  └── Option 2: _has_matching_handler()
      └── CarteraRegionHandler.matches() → True → DEBERÍA funcionar
```

### Hipótesis del Bug

El FSM llama `_has_matching_handler()` pero el handler podría estar siendo importado incorrectamente o hay un error silencioso:

```python
def _has_matching_handler(self) -> bool:
    try:
        from bankadvisor.handlers import get_specific_handlers
        handlers = get_specific_handlers()
        for handler in handlers:
            try:
                if handler.matches(self.query, ...):  # <- Podría fallar silenciosamente
                    return True
            except Exception:
                continue  # <- Swallows all errors!
        return False
    except ImportError:
        return False  # <- También swallow errors
```

**Problema potencial:** Los errores se swallow silenciosamente.

---

## 9. Conclusión

### Problema Confirmado

**La infraestructura está completa:**
- `bank_mv_cartera_por_estado` tiene los datos correctos (14,684 MDP para INVEX Oct 2025)
- `CarteraRegionHandler` existe y matchea queries con "entidad federativa"

**El problema es de routing:**
- Las queries regionales no están llegando al `CarteraRegionHandler`
- En su lugar van a NL2SQL, que genera SQL para `monthly_kpis` (sin datos regionales)
- El LLM entonces alucina datos regionales

### Causa Raíz Probable

1. `_has_matching_handler()` swallow errors silenciosamente
2. El contexto de sesión podría estar influenciando el routing
3. El orden de handlers no garantiza que CarteraRegionHandler se evalúe

### Recomendaciones

| Prioridad | Acción | Impacto |
|-----------|--------|---------|
| **P0** | Agregar logging en `_has_matching_handler()` | Debug inmediato |
| **P1** | Fix error handling - no swallow exceptions | Evita bugs ocultos |
| **P2** | Test E2E: "Saldo por entidad federativa de INVEX" | Regression prevention |
| **P3** | Mover CarteraRegionHandler antes en la lista | Prioridad correcta |

**Prioridad General:** Alta - Este bug causa pérdida de confianza en usuarios expertos.
