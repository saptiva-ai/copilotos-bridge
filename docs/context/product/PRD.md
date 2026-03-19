# Bank Advisor PRD

**Release:** 15 Enero 2026
**Version:** 1.2
**Autor:** Jaziel Flores - Forward Deployed Engineer
**Organización:** Saptiva / OctaviOS Chat
**Actualizado:** 2025-12-30

---

## Resumen Ejecutivo

**Objetivo:** Plataforma de inteligencia bancaria que permite consultar métricas financieras de instituciones mexicanas usando lenguaje natural.

**Usuarios:** C-Level, directores de riesgo, compliance.

**Problemas que resuelve:**
- Acceso fragmentado a datos de 50+ bancos
- Queries manuales SQL → lenguaje natural
- Benchmarking tedioso → comparaciones instantáneas

---

## Métricas de Éxito (BRD)

### North Star + Métricas Clave

| Métrica | Baseline | Target | Cómo Medir |
|---------|----------|--------|------------|
| **WAU** (North Star) | 0 | ≥ 5 usuarios/semana | Logs por user_id |
| **TTI** | TBD | < 5 segundos | Time to first token |
| **ARR** | 0 | USD 30k/cliente | Contratos firmados |

**Objetivo comercial:** USD 30k/cliente × 3+ clientes = USD 90k+ ARR

---

## Status de Implementación

| Componente | Status | Commit/Fecha |
|------------|--------|--------------|
| PoC QuerySpec (100% pass rate) | ✅ **DONE** | 0ed25aee (29-dic) |
| SQL Guardrails (3 capas) | ✅ **DONE** | 5f8c03cb (28-dic) |
| ICAP funcional (datos julio 2025) | ✅ **DONE** | 8bb4246f (26-dic) |
| Weaviate + Ontology_Terms | ✅ **DONE** | 364be292 (28-dic) |
| ETL Ontológico v2 | ✅ **DONE** | b6d6d9d7 (29-dic) |
| UI Clarificación | ⚠️ **EN PROGRESO** | Sprint 4 |
| Multi-banco comparativo | ⚠️ **EN PROGRESO** | Sprint 4 |
| Sistema Feedback (thumbs) | ⚠️ **EN PROGRESO** | Sprint 4 |

---

## Historias de Usuario

### HU1: Query Multi-Banco [P0 - DONE]

**Como** analista, **quiero** consultar métricas de cualquier banco **para** hacer benchmarking.

**Criterios:**
- 10+ bancos disponibles (INVEX, BBVA, Santander, Banorte, HSBC, etc.)
- Datos coinciden con CNBV (±0.01%)
- Latencia < 3s
- Respuesta incluye fecha de corte

**Status:** ✅ Implementado - QuerySpec + SQL Agent funcionando.

---

### HU2: Comparación Multi-Banco [P0 - EN PROGRESO]

**Como** C-Level, **quiero** comparar "IMOR de INVEX vs BBVA vs Santander" **para** entender posición competitiva.

**Criterios:**
- Hasta 5 bancos simultáneos
- Gráfica con leyenda clara
- Tabla resumen con max/min/promedio

**Status:** ⚠️ Sprint 4 - Backend listo, UI pendiente.

---

### HU3: UI Clarificación [P1 - EN PROGRESO]

**Como** usuario, **quiero** que el sistema pregunte cuando mi query es ambigua **para** obtener resultados precisos.

**Criterios:**
- Query ambigua muestra opciones clickeables
- Funciona para: banco, métrica, período
- Confidence < 0.7 → clarificación (NO inventa)

**Status:** ⚠️ Sprint 4 - Modo abstención implementado, UI pendiente.

---

### HU4: RAG con Glosario [P1 - DONE]

**Como** usuario no-experto, **quiero** preguntar "¿qué es ICOR?" **para** entender términos.

**Criterios:**
- Definiciones de CUB + Anexo 36 + Banxico
- Incluye fórmula si aplica
- Cita fuente específica

**Status:** ✅ Implementado - Ontology_Terms en Weaviate con 3,500+ términos.

---

### HU5: Sistema Feedback [P1 - EN PROGRESO]

**Como** usuario, **quiero** indicar si una respuesta es correcta **para** mejorar el sistema.

**Criterios:**
- Botones thumbs up/down en cada mensaje
- Comentario opcional en thumbs down
- Almacenamiento en MongoDB

**Status:** ⚠️ Sprint 4 - Backend endpoint listo, UI pendiente.

---

## Limitaciones v1.0

**OUT OF SCOPE:**
1. Análisis de Drivers ("¿Por qué subió IMOR?") - requiere ML
2. Forecasting/Predicción - requiere modelos
3. Alertas Proactivas - v1.1+
4. Export PDF - solo CSV en v1.0
5. Multi-tenancy completo - solo preparación arquitectónica

---

## Arquitectura Implementada

| Componente | Tecnología |
|------------|-----------|
| Intent Router | LLM classification (4 intents) |
| QuerySpec Builder | JSON Schema + Saptiva Turbo |
| SQL Agent | PostgreSQL + guardrails 3 capas |
| Ontology Store | Weaviate (hybrid: 70% vector + 30% BM25) |
| Knowledge Base | 3,500+ términos regulatorios |
| Visualizations | Plotly.js |

**Guardrails SQL (implementados):**
- Solo SELECT permitido
- Whitelist de tablas
- Timeout 30s, max 5000 rows
- Validación 3 capas: Intent → QuerySpec → SQL

---

## Riesgos y Mitigación

| Riesgo | Prob | Status | Mitigación |
|--------|------|--------|------------|
| QuerySpec fantasía | Alta | ✅ Mitigado | PoC 100% pass, JSON Schema |
| Grounding deficiente | Alta | ✅ Mitigado | Ontology_Terms estructurado |
| ICAP sin datos | Alta | ✅ Resuelto | Datos julio 2025 cargados |
| Performance | Media | ✅ OK | Latencia p50 < 2s |

---

## Criterios Go/No-Go (15 Enero)

### GO (todos deben cumplirse)

- [ ] 10+ bancos consultables
- [ ] TTI < 5 segundos
- [ ] UI Clarificación funcional
- [ ] 0 bugs críticos
- [ ] Documentación publicada

### NO-GO (cualquiera bloquea)

- Menos de 8 bancos consultables
- Datos incorrectos vs CNBV
- Bug de seguridad identificado
- Sistema inestable (> 1 crash/24h)

---

## Roadmap Post-v1.0

| Version | Foco | Features |
|---------|------|----------|
| v1.1 | Multi-tenancy | RLS completo, dashboard observabilidad |
| v1.2 | Analytics | Driver analysis, feedback loops automatizados |
| v1.3 | Proactivo | Forecasting, alertas, export PDF |

---

## Alineación

Este PRD v1.2 está alineado con BRD v1.1 y Arquitectura v1.2.1.

**Documentos relacionados:**
- `docs/tex/BRD.tex`
- `docs/tex/Arquitectura.tex`
