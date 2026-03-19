# Arquitectura: Visión General

> **Cuándo leer**: Para entender qué es Bank Advisor v1.2 y su filosofía.

## Objetivo del Sistema

Bank Advisor v1.2 NO es "hacer RAG". Es un **Sistema Cognitivo Bancario** que:

| Capacidad | Descripción | Ejemplo |
|-----------|-------------|---------|
| **Entender** | Distinguir conocimiento vs ejecución | "¿Qué es IMOR?" vs "Dame IMOR de INVEX" |
| **Aterrizar** | Mapear conceptos a datos reales | Ontología → columna SQL |
| **Ejecutar** | Consultar con guardrails fuertes | Solo SELECT, whitelist, budget |
| **Abstenerse** | No inventar cuando falta grounding | Pedir clarificación |

---

## Filosofía: Plugin-First (Micro-Kernel)

```
                    ┌─────────────────────────────────────┐
                    │           Frontend (3000)            │
                    │         Next.js 14 + React           │
                    └─────────────┬───────────────────────┘
                                  │ HTTP + SSE
                    ┌─────────────▼───────────────────────┐
                    │         Backend Core (8000)          │
                    │    FastAPI - Auth, Chat, Routing     │
                    └──────┬─────────────┬────────────────┘
              HTTP Client  │             │  MCP Protocol
           ┌───────────────▼───┐   ┌─────▼─────────────────┐
           │ File Manager (8001)│   │ Bank Advisor (8002)   │
           │  Storage + Extract │   │  NL2SQL + Analytics   │
           └───────────────────┘   └───────────────────────┘
```

**Principio**: Core es ligero; la lógica de negocio vive en plugins.

---

## Cambio v1.0 → v1.2

| Aspecto | v1.0 (Anterior) | v1.2 (Actual) |
|---------|-----------------|---------------|
| Flujo | Lineal NL2SQL | Orquestación multi-agente |
| Intents | Sin separación | 4 intents diferenciados |
| Weaviate | Chunks genéricos | Ontology_Terms estructurado |
| Sinónimos | Hardcodeados en código | En BD, versionados con ETL |
| Validación | Básica | 3 capas + modo abstención |
| Contrato | Sin especificación | QuerySpec con JSON Schema |

---

## Stack Técnico

### Backend
- **Framework**: FastAPI + Python 3.11 (Puerto 8002)
- **LLM**: SAPTIVA API (Turbo model)
- **Base de Datos**: PostgreSQL 14 en GCP
- **Vector Store**: Weaviate (Ontology_Terms)
- **ETL**: Polars + pandas

### Frontend
- **Framework**: Next.js 14 + React 18 (Puerto 3000)
- **Visualizaciones**: Plotly.js
- **Estado**: Zustand + React Query

### Infraestructura
- **Contenedores**: Docker + Docker Compose
- **Orquestación**: Make-based dev workflow

---

## Riesgos Principales y Mitigaciones

| Riesgo | Síntoma | Mitigación |
|--------|---------|------------|
| QuerySpec Fantasía | JSON inválido, columnas inventadas | JSON Schema + few-shot examples + PoC ≥90% |
| Falta Grounding | SQL incorrecto por retrieval sucio | Ontología estructurada + Linker explícito |
| Sinónimos Hardcoded | Redeploy por cambios de negocio | Sinónimos en BD, versionados |
| Datos Inaccesibles | 721/23M registros accesibles | ETL ontológico + manual_overrides |

---

## Documentos Relacionados

| Para profundizar en... | Lee |
|------------------------|-----|
| Diseño de agentes | [AGENTS.md](AGENTS.md) |
| Schema y datos | [DATA.md](DATA.md) |
| Seguridad | [SECURITY.md](SECURITY.md) |
| Operaciones | [OPERATIONS.md](OPERATIONS.md) |
| Roadmap | [ROADMAP.md](ROADMAP.md) |

---

**Versión**: 1.2.1 | **Fuente**: `docs/tex/Arquitectura.tex` secciones 1-3
