# Arquitectura: Cobertura de Datos

> **Cuándo leer**: Para saber qué bancos, métricas y queries están soportados.

## Estado de Datos (Diciembre 2025)

| Dataset | Registros | Status |
|---------|-----------|--------|
| `monthly_kpis` | 721 | ✅ Operativo |
| `metricas_financieras` | 162 | ⚠️ Solo SQL |
| `metricas_cartera_seg` | 2,445 | 📦 Almacenado |
| `hip_*` (varios) | 23M+ | 📦 Almacenado |
| **Total Cargado** | **23,084,058** | |
| **Total Accesible** | **721** | |
| **Target v1.2** | **~7,000** | |

---

## Cobertura de Bancos

| Banco | Actual | Target v1.2 |
|-------|--------|-------------|
| INVEX | ✅ Completo | ✅ |
| SISTEMA (Agregado) | ✅ Completo | ✅ |
| BBVA México | ⚠️ Solo ICAP | ✅ |
| Santander México | ⚠️ Solo ICAP | ✅ |
| Banorte | ⚠️ Solo ICAP | ✅ |
| HSBC México | ⚠️ Solo ICAP | ✅ |
| Citibanamex | ⚠️ Solo ICAP | ✅ |
| Scotiabank | ⚠️ Solo ICAP | ✅ |
| Banco Azteca | ⚠️ Solo ICAP | ✅ |
| Inbursa | ⚠️ Solo ICAP | ✅ |

**Meta v1.2**: 10 bancos consultables

---

## Métricas Disponibles

| Métrica | Código | Status | Unidad |
|---------|--------|--------|--------|
| Índice de Morosidad | IMOR | ✅ OK | % |
| Índice de Cobertura | ICOR | ✅ OK | % |
| Índice de Capitalización | ICAP | ✅ OK | % |
| Cartera Total | - | ✅ OK | MXN |
| Cartera Comercial | - | ✅ OK | MXN |
| Cartera Consumo | - | ✅ OK | MXN |
| Cartera Vivienda | - | ✅ OK | MXN |
| Cartera Vencida | - | ✅ OK | MXN |
| Reservas | - | ✅ OK | MXN |

---

## Queries Demo (v1.2)

### Soportadas

| # | Query | Intent |
|---|-------|--------|
| 1 | ¿Qué es IMOR? | KNOWLEDGE |
| 2 | Dame el IMOR de INVEX en 2024 | SQL_QUERY |
| 3 | Compara IMOR de INVEX vs BBVA vs Santander | SQL_QUERY + VIZ |
| 4 | ICAP de todos los bancos disponibles | SQL_QUERY + VIZ |
| 5 | Cartera total de HSBC desde 2020 | SQL_QUERY + VIZ |
| 6 | ¿Qué banco tiene el IMOR más bajo en 2024? | SQL_QUERY |
| 7 | Tendencia de cartera vencida del sistema | SQL_QUERY + VIZ |
| 8 | IMOR y ICOR de Banorte últimos 12 meses | SQL_QUERY + VIZ |
| 9 | ¿Cómo se calcula el ICOR? | KNOWLEDGE |
| 10 | Dame la definición de Capital Básico | KNOWLEDGE |

### NO Soportadas (v1.2)

| # | Query | Razón |
|---|-------|-------|
| 1 | ¿Por qué subió el IMOR de INVEX? | DRIVER_ANALYSIS (v1.3+) |
| 2 | Proyecta el IMOR de BBVA para 2026 | Forecasting (v1.3+) |
| 3 | Avísame cuando IMOR suba | Alertas (v1.3+) |
| 4 | Exporta a PDF | Solo CSV en v1.2 |
| 5 | Cartera por segmento de edad | Granularidad no disponible |

---

## Tablas SQL Permitidas

| Tabla/Vista | Descripción | Métricas |
|-------------|-------------|----------|
| `monthly_kpis` | KPIs mensuales por banco | IMOR, ICOR, ICAP, Carteras |
| `vw_banking_metrics` | Vista agregada segura | Todas |
| `metricas_financieras` | Métricas derivadas | Derivadas |

---

## Fecha de Corte

| Aspecto | Valor |
|---------|-------|
| Datos más recientes | Diciembre 2024 |
| Frecuencia actualización | Mensual |
| Fuente | CNBV / Banxico |

> Cada respuesta incluye `data_as_of_date` para trazabilidad.

---

## Limitaciones Conocidas

| Limitación | Impacto | Mitigación |
|------------|---------|------------|
| Solo 721 registros accesibles | Cobertura limitada | ETL ontológico en progreso |
| Histórico < 12 meses para algunos bancos | DriverAnalysis no viable | Disclaimer en respuestas |
| Sin datos intradía | Solo granularidad mensual | Documentar en abstención |

---

**Versión**: 1.2.1 | **Fuente**: `docs/tex/Arquitectura.tex` secciones 17, 18
