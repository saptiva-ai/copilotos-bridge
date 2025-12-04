# BankAdvisor MCP Server

[![Status](https://img.shields.io/badge/Status-Production%20Ready-success)]()
[![Version](https://img.shields.io/badge/Version-1.2.0-blue)]()
[![Protocol](https://img.shields.io/badge/Protocol-MCP-orange)]()

**BankAdvisor** es un sistema de analítica bancaria avanzada que permite consultar métricas de la CNBV mediante lenguaje natural, generando visualizaciones interactivas en tiempo real.

---

## 🚀 Capacidades Principales

### 📊 5 Preguntas de Negocio Críticas (Production Ready)
El sistema responde con precisión y visualizaciones específicas a las siguientes preguntas de negocio (y sus variantes):

1.  **IMOR INVEX vs Mercado**: *"¿Cuál es el IMOR de INVEX vs el mercado?"*
    *   ✅ Gráfica comparativa dual (Líneas + Sombreado).
    *   ✅ Cálculo de spread (puntos porcentuales) y análisis de tendencia.
2.  **Market Share (PDM)**: *"¿Cómo está mi PDM medido por cartera total?"*
    *   ✅ Gráfica de Pay (Pie Chart) + Evolución temporal.
    *   ✅ Ranking automático en el sistema.
3.  **Evolución Cartera Consumo**: *"¿Cómo ha evolucionado la cartera de consumo en el último trimestre?"*
    *   ✅ Gráfica de Cascada (Waterfall) mostrando variaciones mensuales.
    *   ✅ Análisis de crecimiento porcentual QoQ (Quarter-over-Quarter).
4.  **IMOR Automotriz**: *"¿Cómo está mi IMOR en cartera automotriz frente al mercado?"*
    *   ✅ Detección de segmentos específicos.
    *   ✅ Manejo inteligente de datos faltantes (ej. INVEX no tiene cartera automotriz).
5.  **Ranking por Activos**: *"¿Cuál es el tamaño de los bancos por activos?"*
    *   ✅ Gráfica de Barras Horizontales (Top 20).
    *   ✅ Cálculo de % del sistema y % del mercado privado.

### 🧠 Inteligencia Híbrida NL2SQL
*   **Pipeline Unificado**: 100% de queries procesadas por NL2SQL (Q1 2025 - pipeline legacy eliminado).
*   **Clasificación Híbrida**: 80% de las queries se resuelven con reglas determinísticas (<20ms), usando LLM solo para desambiguación.
*   **RAG Feedback Loop**: Sistema de aprendizaje continuo que indexa queries exitosas en Qdrant para mejorar la precisión futura.
*   **Multilingual Support**: Entiende consultas en español e inglés ("IMOR de INVEX", "Show me the IMOR").

### 🔄 RAG Feedback Loop (Q1 2025)
El sistema aprende automáticamente de las consultas exitosas:

```
Usuario → Query → NL2SQL → SQL → Éxito → Log (query_logs)
                                           ↓
                              Job Horario → Embeddings → Qdrant
                                           ↓
                              Próxima Query Similar → +20% boost RAG
```

*   **Automatic Learning**: Queries exitosas se indexan automáticamente cada hora.
*   **Confidence Scoring**: Solo queries con confianza >= 0.7 se indexan.
*   **Performance Boost**: -30% latencia, +40% hit rate después de 100 queries aprendidas.

### 🏭 Arquitectura de Datos Robusta
*   **Dual ETL System**:
    *   **Legacy Pipeline**: Procesa históricos 2017-2025 para métricas tradicionales (`monthly_kpis`).
    *   **Normalized Pipeline**: Procesa reportes complejos (BE_BM_202509) para balances, estados de resultados y segmentación detallada.
*   **Data Quality**: Validaciones automáticas de integridad referencial y rangos de valores.

---

## 📈 Catálogo de Métricas Disponibles

BankAdvisor soporta un amplio rango de indicadores financieros y de riesgo:

| Métrica | Queries de Ejemplo |
|---------|-------------------|
| **Cartera Comercial CC** | `"Cartera comercial de INVEX"`, `"Evolución cartera comercial 2024"` |
| **Cartera Comercial Sin Gob** | `"Cartera comercial sin gobierno"`, `"CC sin entidades gubernamentales"` |
| **Pérdida Esperada Total** | `"Pérdida esperada de INVEX"`, `"PE total del sistema"` |
| **Reservas Totales** | `"Reservas totales de INVEX"`, `"Reservas del sistema 2024"` |
| **Reservas Totales (Variación)** | `"Variación de reservas INVEX"`, `"Cambio en reservas vs mes anterior"` |
| **IMOR** | `"IMOR de INVEX"`, `"Índice de morosidad vs sistema"` |
| **Cartera Vencida** | `"Cartera vencida de INVEX"`, `"Evolución cartera vencida 2024"` |
| **ICOR** | `"ICOR de INVEX"`, `"Índice de cobertura vs sistema"` |
| **Etapas de Deterioro (Sistema)** | `"Etapas de deterioro del sistema"`, `"Distribución etapas IFRS9 sistema"` |
| **Etapas de Deterioro (INVEX)** | `"Etapas de deterioro INVEX"`, `"Etapas 1, 2, 3 de INVEX"` |
| **Quebrantos Comerciales** | `"Quebrantos comerciales INVEX"`, `"Castigos cartera comercial"` |
| **ICAP** | `"ICAP de INVEX"`, `"Índice de capitalización vs sistema"` |
| **Tasa de Deterioro Ajustada** | `"TDA de INVEX"`, `"Tasa deterioro ajustada 2024"` |
| **Tasa Interés Efectiva (Sistema)** | `"Tasa efectiva del sistema"`, `"TE sistema últimos 12 meses"` |
| **Tasa Interés Efectiva (INVEX Consumo)** | `"Tasa INVEX consumo"`, `"TE INVEX segmento consumo"` |
| **Tasa Crédito Corporativo (MN)** | `"Tasa corporativa moneda nacional"`, `"Tasa MN créditos corporativos"` |
| **Tasa Crédito Corporativo (ME)** | `"Tasa corporativa moneda extranjera"`, `"Tasa ME créditos corporativos"` |

---

## 🛠️ Quick Start

### Prerrequisitos
*   Docker & Docker Compose
*   Make (opcional, para comandos rápidos)

### 1. Construir e Iniciar
```bash
make dev-rebuild
# O manualmente:
# docker-compose build bank-advisor && docker-compose up -d bank-advisor
```

### 2. Inicializar Datos (Migraciones + ETL)
Este comando ejecuta las migraciones de base de datos, carga los históricos (Legacy) y procesa los reportes detallados (Normalized).

```bash
make init-bank-advisor
```

*Tiempo estimado: ~3-4 minutos (procesa >100 meses de historia bancaria)*

### 3. Verificar Estado
```bash
curl http://localhost:8002/health | jq
```
Debe retornar `status: "healthy"` y detalles de la última ejecución del ETL.

### 4. Ejecutar Smoke Test
Valida que las 5 preguntas de negocio y las visualizaciones estén funcionando correctamente:

```bash
cd plugins/bank-advisor-private
./scripts/test_5_questions.sh
```

---

## 📚 Documentación

La documentación ha sido reorganizada para facilitar la navegación:

### 🔹 Core (Arquitectura y Diseño)
*   [Architecture Overview](docs/core/ARCHITECTURE.md): Principios SOLID, diagrama de sistema.
*   [NL2SQL Design](docs/core/nl2sql_design.md): Diseño del motor de lenguaje natural.
*   [RAG Design](docs/core/nl2sql_rag_design.md): Arquitectura del sistema de feedback loop.

### 🔹 Features (Funcionalidades)
*   [5 Business Questions](docs/features/DISEÑO_INTEGRACION_5_PREGUNTAS.md): Diseño detallado de las preguntas principales.
*   [9 Priority Visualizations](docs/features/9_PRIORITY_VISUALIZATIONS.md): Catálogo de visualizaciones implementadas.
*   [Frontend Integration](docs/features/FRONTEND_INTEGRATION.md): Integración con OctaviOS UI.
*   [ETL Consolidation](docs/features/ETL_CONSOLIDATION.md): Explicación del sistema de datos dual.

### 🔹 Reports (Validación y Status)
*   [Implementation Summary](docs/reports/IMPLEMENTATION_SUMMARY.md): Estado actual de implementación.
*   [Data Validation](docs/reports/VALIDACION_COMPLETA.md): Evidencia de precisión de datos (INVEX vs CNBV).
*   [QA Results](docs/reports/QA_TEST_RESULTS.md): Resultados de pruebas de calidad.
*   [Q1 2025 Summary](docs/Q1_2025_COMPLETION_SUMMARY.md): Resumen de implementación Q1 2025.

---

## 🧪 Testing

El proyecto cuenta con una suite de pruebas exhaustiva:

| Tipo | Comando | Propósito |
|------|---------|-----------|
| **Smoke Test** | `./scripts/test_5_questions.sh` | Valida las 5 preguntas críticas de negocio. |
| **Demo Test** | `python scripts/smoke_demo_bank_analytics.py` | Valida las 12 queries del demo general. |
| **Adversarial** | `pytest -m nl2sql_dirty` | Prueba inyecciones SQL y queries maliciosas. |
| **Unit** | `pytest src/bankadvisor/tests/` | Pruebas unitarias de servicios. |
| **ETL Ops** | `python scripts/ops_validate_etl.py` | Valida la integridad de los datos cargados. |

---

## 🏗️ Project Structure

Estructura completa del código fuente y recursos del proyecto:

```text
plugins/bank-advisor-private/
├── config/                 # Configuraciones y perfiles de cliente
│   ├── bankadvisor.yaml
│   ├── synonyms.yaml
│   └── profiles/
├── data/                   # Datos crudos (Raw Data - Git Ignored)
│   └── raw/
├── docs/                   # Documentación organizada
│   ├── core/               # Arquitectura, guías de desarrollo y diseños
│   ├── features/           # Especificaciones funcionales (5 preguntas, ETL)
│   ├── reports/            # Resultados de pruebas, validaciones y status
│   └── demos/              # Scripts y planes de demostración
├── etl/                    # Pipeline de transformación de datos (Polars)
│   ├── etl_unified.py      # Orquestador principal del ETL unificado
│   ├── loaders_polars.py   # Cargadores de datos optimizados
│   └── transforms_polars.py # Transformaciones de negocio
├── migrations/             # Esquemas y migraciones de base de datos
│   ├── 000_init_normalized_schema.sql # Esquema base normalizado
│   └── 004_query_logs_rag_feedback.sql # Tablas para feedback loop
├── scripts/                # Scripts de operación, testing y mantenimiento
│   ├── docker-entrypoint.sh # Script de inicio del contenedor
│   ├── init_bank_advisor_data.sh # Inicializador maestro
│   ├── test_5_questions.sh # Test suite de las 5 preguntas clave
│   └── smoke_demo_bank_analytics.py # Test general del demo
├── src/                    # Código fuente de la aplicación
│   ├── main.py             # Entrypoint del servidor MCP (FastAPI)
│   └── bankadvisor/
│       ├── services/       # Servicios core (Analytics, Intent, SQL Gen, RAG)
│       └── models/         # Modelos de datos (Pydantic, SQLAlchemy)
└── tests/                  # Tests automatizados (Unitarios, Integración, E2E)
```

---

## 🛡️ Security & Performance

*   **Read-Only**: El usuario de base de datos para consultas NL2SQL es de solo lectura.
*   **SQL Sanitization**: Validación estricta de queries generadas para prevenir inyección.
*   **Performance**:
    *   p50 Latency: **16ms** (Ratios/Reglas).
    *   p95 Latency: **200ms** (Timelines/DB).
    *   Consultas complejas: ~1.5s (requieren LLM reasoning).

---

## 🔧 Troubleshooting

### Problemas Comunes

| Problema | Causa | Solución |
|----------|-------|----------|
| `NL2SQL service not available` | Servicios no inicializados | Verificar logs de startup, reiniciar contenedor |
| `Query processing failed` | Query ambigua o métrica no soportada | Usar métricas del catálogo, ser más específico |
| `No data returned` | Filtro de fechas/banco sin datos | Ampliar rango de fechas, verificar banco existe |
| `Low confidence score` | Query muy diferente a patrones conocidos | Reformular query, usar ejemplos del catálogo |
| `RAG Feedback not seeding` | Job no iniciado o Qdrant no disponible | Verificar `docker-compose logs bank-advisor` |

### Logs Útiles

```bash
# Ver logs del servicio
docker-compose logs -f bank-advisor

# Verificar estado de RAG Feedback
curl http://localhost:8002/health | jq '.rag_feedback'

# Consultar queries logueadas
docker exec -it postgres psql -U octavios -d bankadvisor -c \
  "SELECT COUNT(*), AVG(rag_confidence) FROM query_logs WHERE success=true"
```

### Variables de Entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (requerido) | API key para embeddings |
| `SAPTIVA_API_KEY` | (opcional) | API key para LLM fallback |
| `RAG_FEEDBACK_INTERVAL_HOURS` | `1` | Intervalo del job de seeding |
| `RAG_MIN_CONFIDENCE` | `0.7` | Confianza mínima para seeding |

---

**Maintainers:** OctaviOS Team
**License:** Private / Proprietary
