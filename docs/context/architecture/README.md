# Arquitectura Bank Advisor v1.2

> **Navegación inteligente para humanos y agentes IA**

## Propósito

Esta carpeta organiza la arquitectura multi-agente de Bank Advisor v1.2 en módulos enfocados para:
- **Reducir carga cognitiva**: Cada documento cubre un aspecto específico
- **Facilitar búsqueda**: Índice con hints de cuándo leer cada módulo
- **Evitar context rot**: Documentos pequeños (<150 líneas) fáciles de mantener

---

## Índice de Navegación

### Para entender el sistema rápidamente
| Necesitas... | Lee | Líneas |
|--------------|-----|--------|
| Visión general de la arquitectura | [OVERVIEW.md](OVERVIEW.md) | ~80 |
| Qué agentes existen y qué hacen | [AGENTS.md](AGENTS.md) | ~120 |

### Para implementar o modificar
| Necesitas... | Lee | Líneas |
|--------------|-----|--------|
| Schema de datos, ETL, QuerySpec | [DATA.md](DATA.md) | ~150 |
| Validación, seguridad, guardrails | [SECURITY.md](SECURITY.md) | ~130 |

### Para operar o monitorear
| Necesitas... | Lee | Líneas |
|--------------|-----|--------|
| SLAs, métricas, observabilidad | [OPERATIONS.md](OPERATIONS.md) | ~120 |
| Roadmap, scope, contingencias | [ROADMAP.md](ROADMAP.md) | ~180 |

### Datos de cobertura
| Necesitas... | Lee | Líneas |
|--------------|-----|--------|
| Bancos, métricas, queries demo | [COVERAGE.md](COVERAGE.md) | ~100 |

---

## Guía Rápida por Rol

### Desarrollador nuevo
1. [OVERVIEW.md](OVERVIEW.md) - Filosofía y diagrama general
2. [AGENTS.md](AGENTS.md) - Entender los agentes
3. [DATA.md](DATA.md) - Schema y QuerySpec

### Revisor de seguridad
1. [SECURITY.md](SECURITY.md) - Validación completa
2. [OPERATIONS.md](OPERATIONS.md) - Métricas de trust

### Product Manager
1. [OVERVIEW.md](OVERVIEW.md) - Resumen ejecutivo
2. [ROADMAP.md](ROADMAP.md) - Timeline y scope
3. [COVERAGE.md](COVERAGE.md) - Qué está soportado

### Agente IA explorando codebase
1. Lee este README primero
2. Según la pregunta, ve al módulo específico
3. Si necesitas todo el contexto: lee en orden OVERVIEW → AGENTS → DATA

---

## Mapa de Conceptos Clave

```
Usuario pregunta NL
        │
        ▼
┌───────────────────┐
│      Router       │ ──────────────────────────────────┐
│   (Orchestrator)  │                                   │
└─────────┬─────────┘                                   │
          │                                             │
    ┌─────┴─────┬───────────────┐                       │
    ▼           ▼               ▼                       │
KNOWLEDGE   SQL_QUERY      VISUALIZATION               │
    │           │               │                       │
    ▼           ▼               ▼                       │
Synthesizer  QuerySpec      Chart                       │
    │        Builder        Builder                     │
    │           │               │                       │
    │           ▼               │                       │
    │       SQL Agent           │                       │
    │           │               │                       │
    ▼           ▼               ▼                       │
Weaviate    PostgreSQL      Plotly.js                  │
(Ontology)  (Datos)         (Gráficas)                 │
    │           │               │                       │
    └───────────┴───────────────┴───────────────────────┘
                        │
                        ▼
              Respuesta con trazabilidad
```

---

## Referencias Cruzadas

| Documento | Relacionado con |
|-----------|-----------------|
| [OVERVIEW.md](OVERVIEW.md) | CLAUDE.md (contexto de negocio) |
| [AGENTS.md](AGENTS.md) | `plugins/bank-advisor-private/src/` |
| [DATA.md](DATA.md) | Weaviate collections, ETL scripts |
| [SECURITY.md](SECURITY.md) | SQL validators, guardrails |
| [OPERATIONS.md](OPERATIONS.md) | Logs, métricas, dashboards |
| [ROADMAP.md](ROADMAP.md) | SPRINT_CURRENT.md, PRD |
| [COVERAGE.md](COVERAGE.md) | Datos cargados en PostgreSQL |

---

## Versión y Mantenimiento

| Campo | Valor |
|-------|-------|
| Versión | 1.2.1 |
| Última actualización | Diciembre 2025 |
| Fuente original | `docs/tex/Arquitectura.tex` |
| Mantenedor | Jaziel Flores |

> **Nota**: Los archivos `.tex` en `docs/tex/` son la fuente canónica para PDFs formales. Estos markdown son la versión navegable para desarrollo diario.
