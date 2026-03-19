# TASK: Integrar Handlers MV en el FSM del Bank Advisor

## Metadata
- **ID**: TASK-2026-01-23__integrate-mv-handlers-fsm
- **Status**: DONE ✅
- **Priority**: HIGH
- **Effort**: M (4-8 horas)
- **Created**: 2026-01-23
- **Completed**: 2026-01-23
- **Author**: Claude + Jaziel

## Problema

El plugin Bank Advisor tiene **10 Materialized Views** con datos pre-agregados y **5 handlers especializados** para consultas granulares, pero **ninguno se invoca** desde el FSM principal.

### Flujo Actual (Roto)
```
User Query → FSM → Validation → Intent → Entities → Routing
                                                      ↓
                                        can_use_fast_path?
                                        ↓ YES        ↓ NO
                                   AnalyticsAgent   NL2SQLAgent
                                        ↓               ↓
                                   AnalyticsService  Placeholder
                                        ↓
                                   ❌ HANDLERS NUNCA SE INVOCAN
```

### Impacto
- Queries como "comparativo regional 2024 vs 2025" van a NL2SQL (placeholder)
- Queries como "cartera por actividad económica" no aprovechan los MVs
- 15MB de datos pre-agregados sin utilizar
- Handlers con visualizaciones ricas (grouped_bar, pie, line) nunca se usan

## Solución: Opción A - Integrar Handlers en AnalyticsAgent

Modificar `AnalyticsAgent.execute()` para invocar handlers antes de caer al fallback.

### Flujo Propuesto
```
User Query → FSM → ... → Routing
                           ↓
                    AnalyticsAgent.execute()
                           ↓
              ┌────────────────────────────┐
              │  1. Intentar Handlers MV   │
              │     ├─ CarteraRegion       │
              │     ├─ CarteraActividad    │
              │     ├─ CarteraTamano       │
              │     ├─ CarteraDestino      │
              │     └─ ViviendaPerfil      │
              └────────────────────────────┘
                           ↓
                    ¿Handler matcheó?
                    ↓ YES         ↓ NO
              Return data    Fallback AnalyticsService
```

## Inventario de MVs Disponibles

### 1. Cartera Comercial - Dimensiones Granulares

| MV | Rows | Columnas Clave | Handler Existente |
|----|------|----------------|-------------------|
| `bank_mv_cartera_por_actividad` | ~50K | actividad_id, sector_economico, grupo_actividad, imor_calculado | ✅ CarteraActividadHandler |
| `bank_mv_cartera_por_tamano` | ~30K | tamano_id, grupo_tamano, es_mipyme, imor_calculado | ✅ CarteraTamanoHandler |
| `bank_mv_cartera_por_destino` | ~25K | destino_id, categoria_destino, imor_calculado | ✅ CarteraDestinoHandler |
| `bank_mv_cartera_por_estado` | ~57K | estado_id, region, zona_economica, imor_calculado | ✅ CarteraRegionHandler |

### 2. Cartera Vivienda

| MV | Rows | Columnas Clave | Handler Existente |
|----|------|----------------|-------------------|
| `bank_mv_vivienda_por_perfil` | ~40K | genero, intervalo_ingreso, tipo_acreditado, intervalo_edades | ✅ ViviendaPerfilHandler |
| `bank_mv_vivienda_por_producto` | ~20K | producto_hipotecario, destino_credito, segmento_vivienda | ✅ ViviendaPerfilHandler |

### 3. Comparativas y Rankings (Sin Handler Dedicado)

| MV | Rows | Columnas Clave | Handler Necesario |
|----|------|----------------|-------------------|
| `bank_mv_comparativa_bancos` | ~5K | market_share_pct, ranking_cartera, pct_etapa_1/2/3 | ⚠️ ComparativaBancosHandler |
| `bank_mv_evolucion_cartera_banco` | ~80K | crecimiento_yoy_pct, crecimiento_mom_pct, imor_variacion_yoy_pp | ⚠️ EvolucionHandler |
| `bank_mv_ranking_cartera_mensual` | ~500 | ranking_*, pct_sistema | ⚠️ RankingMensualHandler |
| `bank_mv_resumen_sistema` | ~300 | cartera_total_sistema, concentracion_top5_pct | ⚠️ ResumenSistemaHandler |

## Queries que Debería Soportar

### Ya Implementados (Handlers Existentes)
```
✅ "comparativo regional 2024 vs 2025 de INVEX"
✅ "cartera por actividad económica"
✅ "top sectores por morosidad"
✅ "cartera a PyMEs de INVEX"
✅ "distribución por tamaño de empresa"
✅ "cartera para capital de trabajo"
✅ "activo fijo vs reestructura"
✅ "hipotecas por género"
✅ "vivienda por nivel de ingreso"
✅ "cartera en el Norte"
✅ "evolución de cartera en Nuevo León"
```

### Nuevos (Requieren Handlers Adicionales)
```
⚠️ "market share de INVEX vs BBVA"
⚠️ "ranking de bancos por cartera"
⚠️ "crecimiento YoY de INVEX"
⚠️ "concentración del sistema bancario"
⚠️ "evolución del IMOR del sistema"
⚠️ "top 10 bancos por cartera comercial"
```

## Archivos a Modificar

| Archivo | Cambio |
|---------|--------|
| `fsm/agents/__init__.py` | Modificar `AnalyticsAgent.execute()` para invocar handlers |
| `fsm/machine.py` | (Opcional) Extender `can_use_fast_path` para detectar handler matches |
| `handlers/__init__.py` | Agregar nuevos handlers si se requieren |
| `services/analytics_service.py` | (Ya tiene los métodos) |

## Criterios de Aceptación

1. [x] Queries regionales funcionan end-to-end via FSM
2. [x] Queries por actividad económica funcionan via FSM
3. [x] Queries por tamaño empresa funcionan via FSM
4. [x] Queries por destino crédito funcionan via FSM
5. [x] Queries vivienda por perfil funcionan via FSM
6. [x] Fallback a AnalyticsService sigue funcionando
7. [x] Tests unitarios para la integración (43 tests: 24 unit + 19 integration)
8. [x] Logging estructurado de handler invocations
9. [x] **BONUS**: MetricasFinancierasHandler para ROA/ROE

## Riesgos

- **Bajo**: Cambios localizados en AnalyticsAgent
- **Mitigación**: Fallback preserva comportamiento actual

---

## Gap Resuelto: Métricas Financieras (ROA/ROE) ✅

### Fuente: `bank_mv_metricas_financieras` (MV nueva)

| Métrica | Disponible | En MV | En Handler |
|---------|------------|-------|------------|
| ROA (Return on Assets) | ✅ 162 rows | ✅ | ✅ |
| ROE (Return on Equity) | ✅ | ✅ | ✅ |
| Activo Total | ✅ | ✅ | ✅ |
| Capital Contable | ✅ | ✅ | ✅ |
| Resultado Neto | ✅ | ✅ | ✅ |
| Captación Total | ✅ | ✅ | ✅ |

### Queries habilitados con MetricasFinancierasHandler:
```
✅ "¿Cuál es el ROA de BBVA?"
✅ "Comparar rentabilidad de bancos"
✅ "Top 10 bancos por ROE"
✅ "Activos totales de INVEX"
✅ "Capital contable de Santander"
```

### Completado (2026-01-23):
- [x] Migración 049: Crear MV `bank_mv_metricas_financieras`
- [x] Migración 050: Cleanup `monthly_kpis` → VIEW compatibilidad
- [x] Handler: `MetricasFinancierasHandler` (registrado en posición 2)
- [x] Tests: 24/24 passed

**Nota**: Datos cubren Sept 2024 - Sept 2025 (3 periodos, 53 bancos, 105 con ROA/ROE)
