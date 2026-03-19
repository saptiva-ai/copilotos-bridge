# Saptiva OctaviOS Chat

> Copiloto IA para ejecutivos de banca que convierte preguntas en insights accionables.

## El Problema

Ejecutivos de banca múltiple dependen de equipos especializados de data para:
- Acceder a métricas regulatorias (IMOR, ICAP, cartera)
- Generar visualizaciones comparativas
- Interpretar datos fragmentados entre sistemas

**Resultado**: Decisiones lentas, costos operativos altos, dependencia de intermediarios.

## La Solución

Un chat simple que responde en lenguaje natural con:
- **Datos institucionales** con trazabilidad completa
- **Visualizaciones automáticas** (comparativas, timeline, ranking)
- **Benchmarks competitivos** (INVEX vs Sistema vs competidores)
- **Terminología regulatoria mexicana** (CUB, Anexo 36, Banxico)

```
Usuario: "¿Cómo está mi IMOR vs el sistema en 2024?"

Respuesta: Gráfica comparativa + interpretación + fuente de datos
```

## Métricas de Éxito

| Métrica | Target |
|---------|--------|
| **TTI** (Time-To-Insight) | < 5 segundos |
| **Query Success Rate** | ≥ 85% |
| **Bancos consultables** | 10+ |
| **Precisión de datos** | ≥ 95% (grounding_rate) |

## Quick Start

```bash
make setup              # Setup interactivo
make dev                # Iniciar stack completo
make create-demo-user   # Usuario: demo / Demo1234
```

**Accesos**:
- Frontend: http://localhost:3000
- API: http://localhost:8000/api
- MinIO: http://localhost:9001

**Verificar**: `make health`

## Stack

| Capa | Tecnología |
|------|------------|
| Frontend | Next.js 14 + React 18 |
| Backend | FastAPI + Python 3.11 |
| Vector DB | Weaviate |
| Storage | MongoDB + Redis + MinIO |
| Analytics | Bank Advisor Plugin (NL2SQL) |

## Documentación

### Para Agentes IA
- [CLAUDE.md](CLAUDE.md) - Índice de contexto para agentes

### Para Desarrolladores
- [.claude/skills/](.claude/skills/) - Skills on-demand (explore, plan, code, test)
- [docs/context/](docs/context/) - Contexto de dominio (Arquitectura, Bank Advisor, Sprint)

### Documentos Estratégicos
| Documento | Markdown (desarrollo) | LaTeX (PDF formal) |
|-----------|----------------------|---------------------|
| BRD | [docs/context/BRD.md](docs/context/BRD.md) | `docs/tex/BRD.tex` |
| Arquitectura | [docs/context/architecture/](docs/context/architecture/) | `docs/tex/Arquitectura.tex` |
| PRD | (pendiente) | `docs/tex/PRD.tex` |

## Comandos Frecuentes

```bash
make dev                    # Iniciar
make logs S=backend         # Ver logs
make test T=api             # Tests backend
make init-bank-advisor      # Inicializar datos bancarios
make help                   # Todos los comandos
```

## Arquitectura

```
Frontend (3000) → Backend Core (8000) → Plugins
                                        ├── File Manager (8001)
                                        └── Bank Advisor (8002) ← NL2SQL
```

**Filosofía**: Core ligero + plugins especializados. Ver [docs/context/architecture/](docs/context/architecture/).

## Contribuir

```bash
git checkout -b feature/mi-cambio
make dev
make test T=api && make lint
# Commits: feat:, fix:, docs:
```

---

**Apache 2.0** · [Saptiva Inc](https://saptiva.com)
