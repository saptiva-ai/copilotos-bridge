# Sprint Actual (v1.2.1)

> Actualizado: 06 ene 2026

## Período

**27 dic 2025 - 15 ene 2026** (10 días hábiles)

## Equipo

| Rol | Persona | Horas/día |
|-----|---------|-----------|
| Lead | Jaziel | 10-12h |
| Dev 2 | Parcial | 6-8h |

**Capacidad total**: 287h productivas

## HUs Activas

| HU | Descripción | Owner | Status |
|----|-------------|-------|--------|
| HU1 | Query Multi-Banco (10 bancos) | Jaziel | Completed |
| HU2 | Comparación Multi-Banco | Jaziel | Completed |
| HU3 | UI Clarificación | Dev 2 | Pending |
| HU7 | Sistema Feedback (thumbs) | Jaziel | Pending |

## Métricas Target

| Métrica | Baseline | Target |
|---------|----------|--------|
| Query success rate | TBD | ≥85% |
| Latencia p50 | 740ms | <2s |
| grounding_rate | TBD | ≥95% |
| Bancos consultables | 2 | ≥10 |

## Gates Completados

- [x] **PoC QuerySpec (Día 6)** - 100% PASSED
  - Unit tests: 100/100 queries
  - E2E smoke: 91.7% (11/12)
  - Latencia: 0.1ms

## Próximos Gates

- [ ] UAT con 2+ usuarios
- [ ] Deploy producción (15 ene)

## Riesgos Activos

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| LLM fallback lento (2-3s) | Media | Optimizar en v1.3 |
| Datos ICAP incompletos | Media | manual_overrides.yml |

## Entregables Críticos

| Entregable | Horas | Status |
|------------|-------|--------|
| NL2SQL 10+ bancos | 60h | Completed |
| UI clarificación | 24h | Pending |
| RAG con CUB | 20h | Completed |
| Tests E2E | 24h | Pending |

## Documentos Relacionados

| Documento | Markdown | LaTeX (PDF) |
|-----------|----------|-------------|
| BRD | [BRD.md](BRD.md) | `docs/tex/BRD.tex` |
| Arquitectura | [architecture/](architecture/) | `docs/tex/Arquitectura.tex` |
| PRD | (pendiente) | `docs/tex/PRD.tex` |

> Para arquitectura modular: [architecture/README.md](architecture/README.md)
