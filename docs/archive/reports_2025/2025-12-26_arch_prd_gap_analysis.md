# Análisis de Gaps: Arquitectura v1.2 → PRD

**Fecha:** 26 Diciembre 2025
**Versión:** 1.0
**Propósito:** Identificar temas técnicos de Arquitectura.tex que faltan en PRD.tex

---

## Resumen Ejecutivo

**Estado actual:**
- ✅ Historias de Usuario (HU1-HU5) actualizadas con detalles arquitectónicos
- ⚠️ Riesgos arquitectónicos críticos NO están en Matriz de Riesgos del PRD
- ⚠️ Gates arquitectónicos (PoC QuerySpec Día 6) NO están en Criterios Go/No-Go
- ⚠️ Entregables técnicos específicos (Ontology_Terms, Validator, etc.) NO están explícitos
- ⚠️ Sprint Plan menciona ETL genérico, NO ETL Ontológico específico

---

## 1. RIESGOS ARQUITECTÓNICOS FALTANTES

### En Arquitectura.tex (Sección: Riesgos Reales y Mitigaciones)

**Riesgo 1: QuerySpec Fantasía** ⚠️ **CRÍTICO - FALTA EN PRD**
- **Problema:** Definir QuerySpec es fácil; lograr que un LLM lo llene con precisión desde Excel + PDF es difícil
- **Síntomas:** JSON inválido, métricas inventadas, columnas inexistentes
- **Mitigación obligatoria:**
  - JSON Schema / function calling + reparación automática
  - Librería de few-shot examples curados (versionada)
  - **PoC con métrica: ≥ 90% QuerySpec válidos y alineados (GATE DÍA 6)**

**Riesgo 2: Falta de Grounding RAG → SQL** ⚠️ **CRÍTICO - FALTA EN PRD**
- **Problema:** "Buscar IMOR y ya" no basta. Si el retrieval devuelve texto sucio, el SQL será una ruleta
- **Mitigación:**
  - Ontología estructurada (no chunks genéricos)
  - Linker explícito (PDF concepto ↔ Excel columna)
  - QuerySpec construido SOLO a partir de entidades ontológicas

**Riesgo 3: Sinónimos Hardcodeados** ⚠️ **IMPORTANTE - FALTA EN PRD**
- **Problema:** Si los sinónimos viven en `weaviate_service.py`, cada cambio de negocio = redeploy
- **Mitigación:**
  - Sinónimos viven en `Ontology_Terms.synonyms`
  - Se versionan con el ETL

**Riesgo 4: Datos Inaccesibles (721 de 23M)** ⚠️ **CRÍTICO - FALTA EN PRD**
- **Problema:** Solo 721 registros son accesibles vía NL2SQL de 23M cargados
- **Causa raíz:** Sin mapeo explícito PDF↔Excel (Linker)
- **Mitigación:**
  - ETL ontológico con Linker automático + manual_overrides.yml
  - Target v1.2: accesibilizar ~7,000 registros (10 bancos)

### En PRD.tex (Sección: Matriz de Riesgos)

**Riesgos actuales** (genéricos, NO arquitectónicos):
- Datos de bancos con formato diferente
- ICAP sin solución posible
- Dev 2 curva de aprendizaje
- Bugs críticos en producción
- Performance se degrada
- Scope creep (features extra)
- Datos fuente CNBV cambian
- Enfermedad/emergencia

### ⚠️ ACCIÓN REQUERIDA:

Agregar 4 riesgos arquitectónicos críticos a la Matriz de Riesgos del PRD:

| Riesgo | Prob. | Impacto | Mitigación |
|--------|-------|---------|------------|
| QuerySpec fantasía (LLM alucina) | **Alta** | **Crítico** | PoC Día 6 con ≥90% precisión (GATE), few-shot examples, JSON Schema |
| Grounding RAG → SQL deficiente | **Alta** | **Crítico** | Ontology_Terms estructurado, Linker PDF↔Excel, validación 3 capas |
| Sinónimos hardcodeados | **Media** | **Alto** | Sinónimos en Ontology_Terms.synonyms, versionados con ETL |
| Datos inaccesibles (721 de 23M) | **Alta** | **Crítico** | ETL Ontológico + Linker + manual_overrides.yml |

---

## 2. GATES ARQUITECTÓNICOS FALTANTES

### En Arquitectura.tex (Sección: PoC Bloqueante QuerySpec)

**Día 6 - PoC QuerySpec (GATE CRÍTICO - BLOQUEANTE):**
- ✓ ≥ 90% QuerySpec válidos (JSON bien formado)
- ✓ ≥ 90% QuerySpec alineados con ontología (no columnas inventadas)
- ✓ 0% SQL destructivo (solo SELECT; validado)

**Si NO se cumplen:** STOP y replantear arquitectura

### En PRD.tex (Sección: Criterios Go/No-Go)

**Criterios GO actuales** (NO mencionan PoC QuerySpec):
- [$\square$] 10+ bancos consultables via NL2SQL
- [$\square$] Query success rate $\geq$ 85\% (medido en staging)
- [$\square$] Latencia p50 $<$ 3 segundos
- [$\square$] UI Clarificacion funcional
- [$\square$] Comparacion multi-banco (3+ bancos) funcional
- [$\square$] 0 bugs criticos abiertos
- [$\square$] Sistema aprobado por 2+ usuarios
- [$\square$] Documentacion publicada
- [$\square$] Rollback plan probado

### ⚠️ ACCIÓN REQUERIDA:

Agregar criterios arquitectónicos críticos:

**Nuevos Criterios GO (Arquitectura v1.2):**
- [$\square$] **PoC QuerySpec aprobado (Día 6)**: ≥90% QuerySpec válidos + alineados, 0% SQL destructivo
- [$\square$] **Ontology_Terms poblada**: ≥100 términos con mapeo SQL explícito
- [$\square$] **Validación 3 capas activa**: Intent, QuerySpec JSON Schema, SQL Validator
- [$\square$] **Guardrails SQL funcionando**: Solo SELECT, whitelist tablas, 30s timeout, 5000 rows max
- [$\square$] **ETL Ontológico ejecutado**: PDF Parser + Excel Parser + Linker + manual_overrides.yml
- [$\square$] **Few-shot examples versionados**: ≥20 ejemplos curados en Query_Examples
- [$\square$] **Modo abstención funcional**: Confidence < 0.7 → clarificación (NO inventa respuestas)

---

## 3. ENTREGABLES TÉCNICOS ESPECÍFICOS FALTANTES

### En Arquitectura.tex (Sección: Plan de Ejecución 2 Semanas)

**Entregables arquitectónicos específicos:**

**Día 1-2: Preparación**
- Schema `Ontology_Terms` definido
- Skeleton ETL
- Eliminar sinónimos hardcodeados

**Día 3-5: ETL Ontológico**
- Excel loader
- PDF loader
- Linker básico (string + embeddings)
- `manual_overrides.yml` para top 20 términos
- Upsert a Weaviate

**Día 6: PoC QuerySpec (GATE)**
- Script PoC
- Dataset de pruebas (30 queries)
- Métrica: ≥90% QuerySpec correcto
- **GO/NO-GO decision**

**Día 7-8: SQL Agent + Validación**
- Templates SQL
- Validator (3 capas)
- Guardrails (budget, whitelist)
- Modo abstención básico

**Día 9: Visualización**
- Chart builder (Plotly)
- Integración con QuerySpec

**Día 10: Testing + Deploy**
- Testing E2E de queries demo
- Deploy a staging
- Handoff documentation

### En PRD.tex (Sección: Lista de Entregables)

**Entregables actuales** (genéricos):
- E1: NL2SQL funcionando con 10+ bancos (60h)
- E2: UI de clarificacion para queries ambiguas (24h)
- E3: Multi-metrica ("IMOR y ICOR de BBVA") (20h)
- E4: Visualizaciones comparativas multi-banco (16h)
- E5: RAG con CUB + Anexo 36 + Banxico (20h)
- E6: Tests E2E automatizados (80%+ coverage) (24h)
- E7: Documentacion usuario final (12h)

### ⚠️ ACCIÓN REQUERIDA:

**Opción 1: Agregar nuevos entregables arquitectónicos específicos (E8-E13):**

| # | Entregable | Horas Est. | Owner | Descripción Técnica |
|---|------------|------------|-------|---------------------|
| E8 | Schema Ontology_Terms + Skeleton ETL | 8h | Jaziel | Definir schema Weaviate, eliminar sinónimos hardcodeados |
| E9 | ETL Ontológico (PDF + Excel + Linker) | 24h | Jaziel | Parser CUB/Banxico, Parser Excel, Linker básico |
| E10 | manual_overrides.yml (top 20 términos) | 4h | Jaziel | Mapeos manuales IMOR, ICOR, ICAP, etc. |
| E11 | PoC QuerySpec (GATE Día 6) | 12h | Jaziel | Dataset 30 queries, métrica ≥90%, GO/NO-GO |
| E12 | Validator 3 capas + Guardrails SQL | 16h | Jaziel | Intent, JSON Schema, SQL Validator, whitelist, budget |
| E13 | Few-shot Query_Examples versionados | 6h | Jaziel | ≥20 ejemplos curados para QuerySpec Builder |

**Opción 2: Expandir E1 y E5 con detalles arquitectónicos:**

- **E1 (expandido):** NL2SQL con arquitectura multi-agente (Router → QuerySpec Builder → SQL Agent + Validator 3 capas + Guardrails)
- **E5 (expandido):** RAG con Ontology_Terms estructurado (ETL Ontológico: PDF Parser + Excel Parser + Linker + manual_overrides.yml)

---

## 4. SPRINT PLAN - TAREAS ARQUITECTÓNICAS FALTANTES

### En Arquitectura.tex (Sección: Timeline Comprimido)

**Tareas específicas por día:**
- Día 1-2: Schema Ontology_Terms, Skeleton ETL, Eliminar sinónimos hardcodeados
- Día 3-5: Excel loader, PDF loader, Linker básico, manual_overrides.yml, Upsert Weaviate
- **Día 6: PoC QuerySpec (GATE)**
- Día 7-8: Templates SQL, Validator 3 capas, Guardrails, Modo abstención
- Día 9: Chart builder Plotly
- Día 10: Testing E2E, Deploy staging

### En PRD.tex (Sección: Sprint Plan)

**Sprint 1 (26-29 Dic) - Tareas actuales:**
- 1.1: Setup ambiente Dev 2 + onboarding codebase (4h)
- 1.2-1.4: ETL: Agregar BBVA, Santander, Banorte (20h)
- 1.5-1.6: Validación de datos vs CNBV (8h)
- 1.7-1.8: UI: Revisar componentes, identificar gaps (8h)
- 1.9: Iniciar investigación ICAP (4h)
- 1.10: Smoke test queries nuevos bancos (2h)

**Sprint 2 (30 Dic - 2 Ene) - Tareas actuales:**
- 2.1-2.7: UI Clarificación, ICAP RCA, Validación, Tests

**Sprint 3 (3-6 Ene) - Tareas actuales:**
- 3.1-3.10: Multi-métrica, RAG, Comparación multi-banco, Tests E2E

### ⚠️ ACCIÓN REQUERIDA:

**Agregar tareas arquitectónicas específicas al Sprint Plan:**

**Sprint 1 (añadir):**
- 1.11: **Schema Ontology_Terms definido** (4h, Jaziel)
- 1.12: **Skeleton ETL Ontológico** (4h, Jaziel)
- 1.13: **Eliminar sinónimos hardcodeados de código** (2h, Jaziel)

**Sprint 2 (añadir):**
- 2.8: **PDF Parser (CUB + Banxico)** (8h, Jaziel)
- 2.9: **Excel Parser (esquema DB)** (6h, Jaziel)
- 2.10: **Linker básico (string + embeddings)** (10h, Jaziel)
- 2.11: **manual_overrides.yml (top 20 términos)** (4h, Jaziel)
- 2.12: **Upsert Ontology_Terms a Weaviate** (4h, Jaziel)

**Sprint 3 (añadir - DÍA CRÍTICO):**
- 3.11: **PoC QuerySpec con dataset 30 queries** (8h, Jaziel) - **BLOQUEANTE**
- 3.12: **Validar métrica ≥90% QuerySpec válidos** (2h, Jaziel) - **GO/NO-GO**
- 3.13: **Templates SQL deterministas** (6h, Jaziel)
- 3.14: **Validator 3 capas (Intent, JSON, SQL)** (8h, Jaziel)
- 3.15: **Guardrails SQL (whitelist, budget, timeout)** (6h, Jaziel)
- 3.16: **Modo abstención (confidence < 0.7)** (4h, Jaziel)
- 3.17: **Few-shot Query_Examples (≥20 ejemplos)** (4h, Jaziel)

---

## 5. CONCEPTOS ARQUITECTÓNICOS NO MENCIONADOS EN PRD

### Conceptos clave de Arquitectura.tex que NO están explícitos en PRD:

**1. Intents (Router/Orchestrator):**
- BANK_KNOWLEDGE
- SQL_QUERY
- VISUALIZATION
- DRIVER_ANALYSIS (OUT v1.2)

**2. Componentes Multi-Agente:**
- Router/Orchestrator
- Knowledge Synthesizer
- QuerySpec Builder
- SQL Agent
- Chart Builder

**3. Ontology_Terms (Weaviate):**
- Schema estructurado (term_id, definition, formula_text, sql_column, source_refs, synonyms)
- Separación: Ontology_Terms (global) vs RAG_Documents_Temp (efímero)
- Target: ≥100 términos mapeados

**4. ETL Ontológico:**
- PDF Parser (CUB + Anexo 36 + Banxico)
- Excel Parser (esquema DB)
- Linker (Entity Resolution PDF ↔ Excel)
- manual_overrides.yml (top 20 términos críticos)
- Idempotente y versionado

**5. QuerySpec (Contrato):**
- JSON Schema estricto
- Campos: intent, bank, metric_code, metric_term_id, sql{table, column, filters}, confidence
- Reparación automática si posible
- Abstención si irreparable (confidence < 0.7)

**6. Validación 3 Capas:**
- Layer 1: Intent/Bank/Metric Validation
- Layer 2: QuerySpec JSON Schema
- Layer 3: SQL Validator (whitelist, budget, safety)

**7. Guardrails SQL:**
- Solo SELECT (whitelist estricta)
- Vistas seguras / RLS (Row-Level Security)
- Query budget: max 30s, 5000 rows, 2 joins
- Audit trail: QuerySpec → SQL fingerprint

**8. Few-shot Examples (Query_Examples):**
- Versionados en Weaviate
- ≥20-30 ejemplos curados de queries comunes
- Mandatorio para evitar que LLM se caiga

**9. Modo Abstención:**
- Confidence threshold: 0.7
- Ambiguity flags: missing_bank, missing_metric, missing_period
- Candidatos desde Ontology_Terms (top-k)
- **Regla crítica:** Sistema NO inventa respuestas

**10. PoC QuerySpec (Gate Día 6):**
- Dataset de pruebas: 30 queries representativas
- Métrica de éxito: ≥90% QuerySpec válidos + alineados
- GO/NO-GO decision: Si falla, replantear arquitectura

### ⚠️ ACCIÓN REQUERIDA:

**Opción 1: Agregar sección "Arquitectura Técnica v1.2" al PRD**
- Incluir diagrama de componentes
- Describir flujo: Usuario → Router → Agentes → BD → Respuesta
- Explicar Ontology_Terms, QuerySpec, Validación 3 capas

**Opción 2: Agregar glosario técnico al final del PRD**
- Definir conceptos clave: Intent, QuerySpec, Ontology_Terms, etc.
- Referencias cruzadas a Arquitectura.tex

---

## 6. RECOMENDACIONES

### Prioridad Alta (Crítico para v1.2):

1. **Agregar 4 riesgos arquitectónicos** a Matriz de Riesgos
   - QuerySpec fantasía
   - Grounding RAG → SQL deficiente
   - Sinónimos hardcodeados
   - Datos inaccesibles (721 de 23M)

2. **Agregar gate PoC QuerySpec Día 6** a Criterios Go/No-Go
   - Criterio bloqueante: ≥90% precisión
   - GO/NO-GO decision explícita

3. **Agregar entregables arquitectónicos específicos**
   - E8-E13: Schema, ETL Ontológico, PoC, Validator, etc.
   - O expandir E1 y E5 con detalles técnicos

4. **Actualizar Sprint Plan con tareas arquitectónicas**
   - Sprint 1: Schema Ontology_Terms, Skeleton ETL
   - Sprint 2: ETL Ontológico (Parser + Linker + manual_overrides)
   - Sprint 3: PoC QuerySpec (GATE), Validator 3 capas

### Prioridad Media (Importante para claridad):

5. **Agregar sección "Arquitectura Técnica v1.2"** al PRD
   - Diagrama de componentes
   - Flujo técnico end-to-end
   - Descripción de Ontology_Terms, QuerySpec, Validación

6. **Agregar criterios arquitectónicos** a Criterios Go/No-Go
   - Ontology_Terms poblada (≥100 términos)
   - Validación 3 capas activa
   - Guardrails SQL funcionando
   - Few-shot examples versionados

### Prioridad Baja (Nice to have):

7. **Agregar glosario técnico** al PRD
   - Definir: Intent, QuerySpec, Ontology_Terms, Linker, etc.

8. **Referencias cruzadas** entre PRD y Arquitectura.tex
   - "Ver Arquitectura.tex sección X para detalles"

---

## 7. COMPARACIÓN LADO A LADO

### Riesgos:

| Tema | Arquitectura.tex | PRD.tex | Gap |
|------|------------------|---------|-----|
| QuerySpec fantasía | ✅ Riesgo 1 detallado | ❌ No mencionado | **CRÍTICO** |
| Grounding RAG → SQL | ✅ Riesgo 2 detallado | ❌ No mencionado | **CRÍTICO** |
| Sinónimos hardcodeados | ✅ Riesgo 3 detallado | ❌ No mencionado | **IMPORTANTE** |
| Datos inaccesibles (721 de 23M) | ✅ Riesgo 4 detallado | ❌ No mencionado | **CRÍTICO** |

### Gates:

| Gate | Arquitectura.tex | PRD.tex | Gap |
|------|------------------|---------|-----|
| PoC QuerySpec Día 6 (≥90%) | ✅ Gate bloqueante | ❌ No mencionado | **CRÍTICO** |
| Ontology_Terms poblada (≥100) | ✅ Definición de Done | ❌ No mencionado | **IMPORTANTE** |
| Validación 3 capas activa | ✅ Requerido | ❌ No mencionado | **IMPORTANTE** |
| Guardrails SQL funcionando | ✅ Requerido | ❌ No mencionado | **IMPORTANTE** |

### Entregables:

| Entregable | Arquitectura.tex | PRD.tex | Gap |
|------------|------------------|---------|-----|
| Schema Ontology_Terms | ✅ Día 1-2 | ❌ No explícito | **IMPORTANTE** |
| ETL Ontológico (Parser + Linker) | ✅ Día 3-5 | ⚠️ Genérico "RAG" | **IMPORTANTE** |
| manual_overrides.yml | ✅ Día 3-5 | ❌ No mencionado | **IMPORTANTE** |
| PoC QuerySpec | ✅ Día 6 (GATE) | ❌ No explícito | **CRÍTICO** |
| Validator 3 capas | ✅ Día 7-8 | ❌ No explícito | **IMPORTANTE** |
| Guardrails SQL | ✅ Día 7-8 | ❌ No explícito | **IMPORTANTE** |
| Few-shot Query_Examples | ✅ Requerido | ❌ No mencionado | **IMPORTANTE** |

---

## 8. PRÓXIMOS PASOS SUGERIDOS

1. **Revisar este documento** con el equipo
2. **Priorizar gaps** (Críticos primero)
3. **Actualizar PRD.tex** con:
   - Riesgos arquitectónicos (Matriz de Riesgos)
   - Gate PoC QuerySpec (Criterios Go/No-Go)
   - Entregables arquitectónicos (Lista de Entregables)
   - Tareas arquitectónicas (Sprint Plan)
4. **Validar alineación** PRD ↔ Arquitectura ↔ BRD
5. **Comunicar cambios** al equipo antes del Sprint 1

---

**Última actualización:** 26 Diciembre 2025
**Próxima revisión:** Antes del inicio del Sprint 1 (27 Dic)
