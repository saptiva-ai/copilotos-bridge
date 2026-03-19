# Arquitectura: Roadmap v1.2

> **Cuándo leer**: Para entender timeline, scope y plan de contingencia.

## Timeline

| Campo | Valor |
|-------|-------|
| **Inicio** | 27 Diciembre 2025 |
| **Fin** | 15 Enero 2026 |
| **Días hábiles** | 10 días |

---

## Plan de Ejecución

| Día | Fase | Entregables |
|-----|------|-------------|
| 1-2 | **Preparación** | Schema Ontology_Terms + Skeleton ETL + Eliminar sinónimos hardcodeados |
| 3-5 | **ETL Ontológico** | Excel loader + PDF loader + Linker básico + manual_overrides.yml + Upsert Weaviate |
| 6 | **PoC QuerySpec** 🚨 | Script PoC + 30 queries test + ≥90% precisión + **GO/NO-GO** |
| 7-8 | **SQL Agent** | Templates SQL + Validator 3 capas + Guardrails + Modo abstención |
| 9 | **Visualización** | Chart builder Plotly + Integración QuerySpec |
| 10 | **Deploy** | Testing E2E + Deploy staging + Documentación |

---

## Gates Críticos

### Día 6: PoC QuerySpec (BLOQUEANTE)

| Criterio | Target | Status |
|----------|--------|--------|
| QuerySpec válidos (JSON) | ≥ 90% | Obligatorio |
| QuerySpec alineados con ontología | ≥ 90% | Obligatorio |
| SQL destructivo | 0% | Obligatorio |

> ⚠️ **Si NO se cumplen**: STOP y replantear arquitectura

### Día 10: Release

| Criterio | Target | Status |
|----------|--------|--------|
| Ontology_Terms poblada | ≥ 100 términos | Obligatorio |
| Queries demo E2E | 10 funcionando | Obligatorio |
| Validación + guardrails | Activos | Obligatorio |
| Modo abstención | Funcional | Obligatorio |

---

## Scope IN (v1.2)

| Componente | Detalle |
|------------|---------|
| Arquitectura multi-agente | Router, Knowledge, QuerySpec, SQL, Chart |
| Ontology_Terms | Top 100 términos mapeados |
| ETL ontológico | Linker básico + manual_overrides.yml |
| PoC QuerySpec | ≥90% precisión |
| Validación | 3 capas + modo abstención |
| Guardrails SQL | Budget, whitelist, RLS básico |
| Visualización | Plotly básico |
| Cobertura | 10 bancos |
| **[NUEVO]** Feedback | Thumbs up/down + texto |
| **[NUEVO]** Trazabilidad | Fecha corte + source_refs |
| **[NUEVO]** Métricas trust | grounding_rate, abstention_rate |
| **[NUEVO]** Multi-tenancy | tenant_id en schemas (nullable) |

---

## Scope OUT (v1.3+)

| Componente | Razón |
|------------|-------|
| DriverAnalysis completo | Requiere 12-24 meses histórico |
| Feedback loops automatizados | Clustering de fallos |
| UI de corrección mapeos | Se usa YAML manual |
| Predicción/forecasting | ML models |
| Alertas proactivas | "Avísame cuando..." |
| Export PDF | Solo CSV en v1.2 |
| Multi-tenancy completo | RLS por organización |
| Dashboard observabilidad UI | Solo logs en v1.2 |

---

## Plan de Contingencia

### Si PoC QuerySpec Falla (Día 6)

#### Opción A: Pivot a Templates (+2-3 días)
- Abandonar generación dinámica
- 20-30 templates SQL hardcodeados
- Router → selecciona template → llena parámetros
- **Trade-off**: Menor flexibilidad, 100% control

#### Opción B: Human-in-the-Loop (+1 semana)
- QuerySpec va a revisión antes de ejecutar
- Usuario confirma o corrige
- Correcciones alimentan few-shot
- **Trade-off**: UX degradada, datos valiosos

#### Opción C: Reducir Scope (+0 días)
- Solo BANK_KNOWLEDGE en v1.2
- SQL_QUERY pasa a v1.3
- **Trade-off**: Demo menos impactante, entrega a tiempo

### Si Datos Insuficientes

| Problema | Mitigación |
|----------|------------|
| < 100 términos mapeables | Priorizar top 50 críticos |
| Bancos sin datos | Reducir a 6 bancos |
| Fecha de corte antigua | Disclaimer visible |
| Columnas no mapeables | Modo abstención |

### Si Timeline se Extiende

| Extensión | Acción |
|-----------|--------|
| +1-2 días | Aceptable, comprimir testing |
| +3-5 días | Escalar stakeholders, reducir VIZ |
| +1 semana | Replantear como v1.2-alpha |

---

## Definición de Done

### 1. Ontología Estructurada
- [x] Ontology_Terms existe y poblada
- [x] Mapeo PDF↔Excel con reporte unmatched
- [x] Sinónimos NO en código

### 2. QuerySpec Validado
- [x] PoC pasa gating (≥90%)
- [x] JSON Schema + reparación automática

### 3. Ejecución Segura
- [x] SQL guardraileado
- [x] Modo abstención funcional

### 4. Demos Operativas
- [x] 10 queries demo E2E
- [x] 10 bancos cubiertos

---

## Bancos Target v1.2

| # | Banco | Status |
|---|-------|--------|
| 1 | INVEX | ✅ Completo |
| 2 | SISTEMA (Agregado) | ✅ Completo |
| 3 | BBVA México | ✅ Target |
| 4 | Santander México | ✅ Target |
| 5 | Banorte | ✅ Target |
| 6 | HSBC México | ✅ Target |
| 7 | Citibanamex | ✅ Target |
| 8 | Scotiabank | ✅ Target |
| 9 | Banco Azteca | ✅ Target |
| 10 | Inbursa | ✅ Target |

---

## Contactos

| Rol | Contacto |
|-----|----------|
| Lead Developer | Jaziel Flores |
| Repositorio | `octavios-chat-bajaware_invex` |
| Branch | `feature/message-feedback-system` |
| Documentación | `plugins/bank-advisor-private/docs/` |

---

**Versión**: 1.2.1 | **Fuente**: `docs/tex/Arquitectura.tex` secciones 12-15, 20
