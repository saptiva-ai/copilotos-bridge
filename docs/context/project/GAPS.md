# Gaps Consolidados: Arquitectura → PRD

> **Propósito**: Trazabilidad de gaps técnicos por épica para priorización

## Estado General

| Métrica | Valor |
|---------|-------|
| Compliance "Done v1.2" | **67%** (8/12 criterios) |
| P0 Blockers | ✅ Completados |
| P1 Tasks Pendientes | 3 |
| P2 Nice-to-have | 3 |

---

## P0 - Blockers (COMPLETADOS)

### P0-1: QuerySpec PoC Validation
| Campo | Valor |
|-------|-------|
| Status | ✅ COMPLETADO |
| Resultado | 100% accuracy |
| Commit | `0ed25aee` (29-dic) |
| Épicas | Todas |

### P0-2: SQL Guardrails + Validator
| Campo | Valor |
|-------|-------|
| Status | ✅ COMPLETADO |
| Componentes | QueryBudget, SqlValidator, AuditTrailService |
| Tests | 57 (45 unit, 12 integration) |
| Commit | `5f8c03cb` (28-dic) |
| Épicas | HU1, HU2 |

---

## P1 - Importantes (PENDIENTES)

### P1-1: Modo Abstención Robusto

| Campo | Valor |
|-------|-------|
| Status | ⚠️ PARCIAL |
| Esfuerzo | 1 día |
| Impacto | UX degradada si query ambiguo |
| Épicas Afectadas | **HU3** (UI Clarificación) |

**Qué falta**:
- Confidence threshold < 0.7 → mostrar opciones
- UI para selección de clarificación
- Logging de clarificaciones para mejora

**Criterios de Aceptación**:
- [ ] Query ambigua muestra opciones clickeables
- [ ] Usuario puede seleccionar opción
- [ ] Sistema no inventa respuesta

---

### P1-2: Chart Builder (Plotly)
**Status**: ✅ RESOLVED (2026-01-02)
**Metric**: Backend logic completed with 17 tests.

**Qué falta**:
- Plotly.js templates (line, bar, table)
- Integración QuerySpec → Chart config
- Export a PNG/CSV

**Criterios de Aceptación**:
- [ ] Gráfica de líneas para tendencia temporal
- [ ] Gráfica de barras para comparación
- [ ] Tabla resumen con max/min/promedio
- [ ] Leyenda clara con colores diferenciados

---

### P1-3: Testing E2E (10 Queries Demo)

| Campo | Valor |
|-------|-------|
| Status | ⚠️ PARCIAL |
| Esfuerzo | 1-2 días |
| Impacto | Riesgo de regresiones |
| Épicas Afectadas | **HU1**, **HU2** |

**Qué falta**:
- Suite de 10 queries representativas
- E2E tests con DB real (PostgreSQL)
- Validación de resultados esperados
- Smoke tests para regression prevention

**Queries Demo Requeridas**:
1. ¿Qué es IMOR? (KNOWLEDGE)
2. Dame IMOR de INVEX 2024 (SQL_QUERY)
3. Compara IMOR INVEX vs BBVA (SQL_QUERY + VIZ)
4. ICAP de todos los bancos (SQL_QUERY + VIZ)
5. ¿Qué banco tiene menor IMOR? (SQL_QUERY)
6. Tendencia cartera vencida (SQL_QUERY + VIZ)
7. ¿Cómo se calcula ICOR? (KNOWLEDGE)
8. Definición Capital Básico (KNOWLEDGE)
9. IMOR y ICOR Banorte 12 meses (SQL_QUERY + VIZ)
10. Cartera total HSBC desde 2020 (SQL_QUERY)

---

## P2 - Nice-to-have

### P2-1: Migrar Sinónimos a Ontology_Terms

| Campo | Valor |
|-------|-------|
| Status | ❌ NO IMPLEMENTADO |
| Esfuerzo | 1 día |
| Impacto | BAJO (funciona con METRIC_MAP) |
| Épicas Afectadas | HU4 |

### P2-2: Observability Avanzada

| Campo | Valor |
|-------|-------|
| Status | ❌ NO IMPLEMENTADO |
| Esfuerzo | 2-3 días |
| Impacto | BAJO (no bloqueante) |
| Épicas Afectadas | Operaciones |

### P2-3: Linker Automático PDF↔Excel

| Campo | Valor |
|-------|-------|
| Status | ❌ DEPRIORITIZADO |
| Esfuerzo | 3-4 días |
| Impacto | MEDIO (cobertura datos) |
| Épicas Afectadas | ETL |

---

## Matriz Épica → Gaps

| Épica | P1-1 | P1-2 | P1-3 | P2-1 |
|-------|------|------|------|------|
| HU1: Query Multi-Banco | - | - | ✓ | - |
| HU2: Comparación | - | ✓ | ✓ | - |
| HU3: UI Clarificación | ✓ | - | - | - |
| HU4: RAG Glosario | - | - | - | ✓ |
| HU5: Feedback | - | - | - | - |

---

## Roadmap de Resolución

### Semana 1 (30 Dic - 3 Ene)
- [ ] P1-3: Testing E2E (2 días)
- [ ] P1-1: Modo abstención (1 día)

### Semana 2 (6 Ene - 15 Ene)
- [ ] P1-2: Chart Builder (2 días)
- [ ] Deploy staging (1 día)
- [ ] Smoke tests finales (1 día)

---

**Target v1.2**: 75-80% compliance (9-10/12 criterios)
