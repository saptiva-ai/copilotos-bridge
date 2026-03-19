# Research: Estado Actual del FSM y Handlers

## Fecha: 2026-01-23

---

## 1. Inventario Completo de MVs

### Datos Pre-Agregados Disponibles

| MV | Size | Periodos | Dimensiones | Métricas |
|----|------|----------|-------------|----------|
| `bank_mv_cartera_por_actividad` | 1.6 MB | 2022-2025 | banco, actividad, sector | saldo, créditos, IMOR |
| `bank_mv_cartera_por_destino` | 472 KB | 2022-2025 | banco, destino, categoría | saldo, créditos, IMOR |
| `bank_mv_cartera_por_estado` | 10 MB | 2022-2025 | banco, estado, región, zona | saldo, créditos, IMOR, etapas |
| `bank_mv_cartera_por_tamano` | 448 KB | 2022-2025 | banco, tamaño, es_mipyme | saldo, créditos, IMOR |
| `bank_mv_comparativa_bancos` | 16 KB | 2016-2025 | banco | cartera, IMOR, ICAP, market_share |
| `bank_mv_evolucion_cartera_banco` | 2.4 MB | 2016-2025 | banco | YoY%, MoM%, variaciones |
| `bank_mv_ranking_cartera_mensual` | 8 KB | último mes | banco | rankings múltiples |
| `bank_mv_resumen_sistema` | 64 KB | 2016-2025 | sistema | totales, concentración |
| `bank_mv_vivienda_por_perfil` | 1.3 MB | 2022-2025 | banco, género, ingreso, edad | saldo, créditos |
| `bank_mv_vivienda_por_producto` | 336 KB | 2022-2025 | banco, producto, segmento | saldo, originación |

**Total**: ~15 MB de datos pre-agregados para consultas instantáneas.

---

## 2. Handlers Existentes y Su Estado

### Handlers MV (Nuevos - 2026-01-23)

| Handler | MV que usa | Queries soportados | Estado |
|---------|-----------|-------------------|--------|
| CarteraActividadHandler | `bank_mv_cartera_por_actividad` | "cartera por actividad", "manufactura", "comercio" | ✅ Funcional, no conectado |
| CarteraTamanoHandler | `bank_mv_cartera_por_tamano` | "cartera a PyMEs", "por tamaño empresa" | ✅ Funcional, no conectado |
| CarteraDestinoHandler | `bank_mv_cartera_por_destino` | "capital de trabajo", "activo fijo" | ✅ Funcional, no conectado |
| ViviendaPerfilHandler | `bank_mv_vivienda_por_*` | "hipotecas por género", "por ingreso" | ✅ Funcional, no conectado |
| CarteraRegionHandler | `bank_mv_cartera_por_estado` | "cartera por región", "comparativo regional" | ✅ Funcional, no conectado |

### Handlers Legacy

| Handler | Uso | Estado |
|---------|-----|--------|
| MultiMetricHandler | Gráficos stacked para múltiples métricas | ✅ Conectado via main.py |
| ComparativeRatioHandler | Ratios financieros | ✅ Conectado via main.py |
| MarketShareHandler | Market share | ✅ Conectado via main.py |
| SegmentHandler | Segmentos | ✅ Conectado via main.py |
| InstitutionRankingHandler | Rankings | ✅ Conectado via main.py |

---

## 3. Análisis del FSM

### Archivo: `fsm/machine.py`

**Routing Decision** (línea 573-580):
```python
def _determine_routing_transition(self, model: QueryModel) -> str:
    if model.is_knowledge_query:
        return "route_to_knowledge"
    elif model.can_use_fast_path:
        return "route_to_analytics"
    else:
        return "route_to_nl2sql"
```

**can_use_fast_path** (línea 182-196):
```python
@property
def can_use_fast_path(self) -> bool:
    if not self.entities:
        return False
    has_metric = self.entities.metric_id is not None
    has_banks = len(self.entities.banks) > 0
    return has_metric and (has_banks or self.is_ranking_query)
```

**Problema**: Queries sin `metric_id` van a NL2SQL aunque un handler pueda procesarlas.

---

## 4. Análisis del AnalyticsAgent

### Archivo: `fsm/agents/__init__.py` (líneas 400-480)

```python
class AnalyticsAgent(BaseAgent):
    async def execute(self, model: QueryModel) -> QueryModel:
        service = AnalyticsService()
        metric_id = model.entities.metric_id

        if model.intent == "ranking":
            data = await service.get_ranking(...)
        else:
            data = await service.get_filtered_data(...)
```

**Problema**: Solo usa `AnalyticsService`, nunca invoca handlers.

---

## 5. Test de Handler Matching

Ejecutado 2026-01-23:

```
Query: comparativo regional 2024 vs 2025
Matched handler: cartera_region
Visualization: grouped_bar
Result: ✅ Datos correctos con variación YoY

Query: cartera por región
Matched handler: cartera_region
Visualization: horizontal_bar
Result: ✅ Ranking por región

Query: cartera de INVEX en el Norte
Matched handler: cartera_region
Visualization: pie
Result: ✅ Breakdown por estado
```

---

## 6. Gaps Identificados

### Sin Handler (Oportunidad)

| Query Pattern | MV Disponible | Handler Faltante |
|---------------|---------------|------------------|
| "market share de X vs Y" | `bank_mv_comparativa_bancos` | ComparativaBancosHandler |
| "crecimiento YoY de X" | `bank_mv_evolucion_cartera_banco` | EvolucionBancoHandler |
| "top 10 bancos" | `bank_mv_ranking_cartera_mensual` | RankingMensualHandler |
| "resumen del sistema" | `bank_mv_resumen_sistema` | ResumenSistemaHandler |

### Columnas MV No Utilizadas

**bank_mv_evolucion_cartera_banco**:
- `crecimiento_yoy_pct` - Para queries de crecimiento
- `crecimiento_mom_pct` - Para queries mensuales
- `imor_variacion_yoy_pp` - Para variación de morosidad

**bank_mv_comparativa_bancos**:
- `pct_etapa_1/2/3` - Para distribución de etapas
- `ranking_cartera` - Para rankings directos

---

## 7. Dimensiones de la Data

```
Instituciones bancarias: 122
Estados geográficos: 40
Regiones: 7 (Norte, Centro, Centro-Occidente, Sureste, Sur, Noroeste, Noreste)
Actividades económicas: 24
Destinos de crédito: 28
Tamaños de empresa: 5 (Micro, Pequeña, Mediana, Grande, Sin Clasificar)
Periodos mensuales: 313 (2000-2026)
Periodos con datos: ~48 (últimos 4 años)
```

---

## 8. Conclusión

El plugin tiene **toda la infraestructura necesaria** (MVs + Handlers + Services) pero la **conexión FSM → Handlers está rota**. La solución más directa es modificar `AnalyticsAgent.execute()` para invocar handlers antes del fallback.
