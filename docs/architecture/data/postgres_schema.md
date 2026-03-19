# Base de Datos GCP PostgreSQL - Bank Advisor

**Host:** ${GCP_POSTGRES_HOST}
**Database:** bankadvisor
**User:** bankadvisor
**Última actualización:** 2025-12-05

---

## Resumen General

- **Total de tablas:** 9
- **Total de columnas:** 127
- **Total de registros:** 3,344

---

## Tablas

### 1. monthly_kpis (33 columnas, 721 registros)

**Descripción:** KPIs mensuales consolidados de métricas financieras y de cartera. Contiene las métricas principales de INVEX organizadas por fecha.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `fecha` | timestamp | Fecha del reporte mensual |
| `banco_norm` | text | Nombre normalizado del banco (INVEX) |
| **Cartera Total y Segmentos** | | |
| `cartera_total` | double precision | Cartera de crédito total en millones de pesos |
| `cartera_comercial_total` | double precision | Cartera comercial total |
| `cartera_comercial_sin_gob` | double precision | Cartera comercial sin entidades gubernamentales |
| `cartera_consumo_total` | double precision | Cartera de crédito al consumo |
| `cartera_vivienda_total` | double precision | Cartera de crédito a la vivienda |
| `empresarial_total` | double precision | Cartera empresarial |
| `entidades_financieras_total` | double precision | Cartera a entidades financieras |
| `entidades_gubernamentales_total` | double precision | Cartera a entidades gubernamentales |
| **Cartera Vencida y Reservas** | | |
| `cartera_vencida` | double precision | Cartera de crédito vencida |
| `reservas_etapa_todas` | double precision | Reservas totales de todas las etapas |
| `reservas_variacion_mm` | double precision | Variación mensual de reservas (mes a mes) |
| **Cartera por Etapas (IFRS 9)** | | |
| `cartera_total_etapa_1` | double precision | Cartera total en etapa 1 (performing) |
| `ct_etapa_1` | double precision | Cartera etapa 1 (formato alternativo) |
| `pct_etapa_1` | double precision | Porcentaje de cartera en etapa 1 |
| `cartera_total_etapa_2` | double precision | Cartera total en etapa 2 (under-performing) |
| `ct_etapa_2` | double precision | Cartera etapa 2 (formato alternativo) |
| `pct_etapa_2` | double precision | Porcentaje de cartera en etapa 2 |
| `cartera_total_etapa_3` | double precision | Cartera total en etapa 3 (non-performing) |
| `ct_etapa_3` | double precision | Cartera etapa 3 (formato alternativo) |
| `pct_etapa_3` | double precision | Porcentaje de cartera en etapa 3 |
| **Indicadores de Calidad de Cartera** | | |
| `imor` | double precision | Índice de Morosidad (Cartera Vencida / Cartera Total) |
| `icor` | double precision | Índice de Cobertura (Reservas / Cartera Vencida) |
| `pe_total` | double precision | Pérdida Esperada total |
| **Tasas de Interés** | | |
| `tasa_mn` | double precision | Tasa promedio en moneda nacional |
| `tasa_me` | double precision | Tasa promedio en moneda extranjera |
| `tasa_sistema` | double precision | Tasa promedio del sistema bancario |
| `tasa_invex_consumo` | double precision | Tasa INVEX para crédito al consumo |
| `tda_cartera_total` | double precision | Tasa de Crecimiento Anual de cartera total |
| **Indicadores de Capitalización y Mercado** | | |
| `icap_total` | double precision | Índice de Capitalización Total |
| `market_share_pct` | double precision | Participación de mercado (porcentaje) |
| **Quebrantos** | | |
| `quebrantos_comerciales` | double precision | Quebrantos de cartera comercial |

---

### 2. metricas_cartera_segmentada (8 columnas, 2,445 registros)

**Descripción:** Métricas de calidad de cartera desglosadas por segmento de negocio (comercial, consumo, vivienda, etc.).

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `institucion` | text | Nombre de la institución bancaria |
| `fecha_corte` | text | Fecha de corte del reporte (formato texto) |
| `segmento_codigo` | text | Código del segmento de cartera |
| `segmento_nombre` | text | Nombre descriptivo del segmento |
| `cartera_total` | double precision | Cartera total del segmento en millones |
| `imor` | double precision | Índice de Morosidad del segmento |
| `icor` | double precision | Índice de Cobertura del segmento |
| `perdida_esperada` | double precision | Pérdida esperada del segmento |

---

### 3. metricas_financieras_ext (13 columnas, 162 registros)

**Descripción:** Métricas financieras extendidas con indicadores de rentabilidad y balance general.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `institucion` | text | Nombre de la institución |
| `fecha_corte` | text | Fecha de corte |
| `banco_norm` | text | Nombre normalizado del banco |
| **Balance General** | | |
| `activo_total` | double precision | Activos totales en millones de pesos |
| `inversiones_financieras` | double precision | Total de inversiones financieras |
| `cartera_total_pm2` | double precision | Cartera total (metodología PM2) |
| `captacion_total` | double precision | Captación total (depósitos) |
| `capital_contable` | double precision | Capital contable (patrimonio) |
| **Rentabilidad** | | |
| `resultado_neto` | double precision | Resultado neto (utilidad/pérdida) |
| `roa_12m` | double precision | Return on Assets últimos 12 meses (%) |
| `roe_12m` | double precision | Return on Equity últimos 12 meses (%) |
| **Duplicados de Join** | | |
| `institucion_right` | text | Campo duplicado de institución (artifact de join) |
| `fecha_corte_right` | text | Campo duplicado de fecha (artifact de join) |

---

### 4. segmentos_cartera (4 columnas, 15 registros)

**Descripción:** Catálogo de segmentos de cartera de crédito utilizados en la segmentación.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Identificador único del segmento |
| `codigo` | varchar(50) | Código corto del segmento |
| `nombre` | varchar(100) | Nombre descriptivo del segmento |
| `descripcion` | text | Descripción detallada del segmento |

**Ejemplos de segmentos:**
- Cartera Comercial
- Crédito al Consumo
- Crédito a la Vivienda
- Empresarial
- Entidades Financieras
- Entidades Gubernamentales

---

### 5. etl_runs (10 columnas, 1 registro)

**Descripción:** Log de ejecuciones del proceso ETL (Extract, Transform, Load) que carga datos a la base.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Identificador único de la ejecución |
| `started_at` | timestamp | Fecha y hora de inicio del ETL |
| `completed_at` | timestamp | Fecha y hora de finalización |
| `status` | varchar(20) | Estado de la ejecución (success, failed, running) |
| `duration_seconds` | numeric | Duración total en segundos |
| `rows_processed_base` | integer | Filas procesadas en carga base |
| `rows_processed_enhancements` | integer | Filas procesadas en mejoras |
| `error_message` | text | Mensaje de error (si aplica) |
| `etl_version` | varchar(50) | Versión del proceso ETL |
| `created_at` | timestamp | Timestamp de creación del registro |

---

### 6. metricas_financieras (27 columnas, 0 registros)

**Descripción:** Tabla normalizada para métricas financieras con relación a catálogo de instituciones. Actualmente sin datos.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Identificador único |
| `institucion_id` | integer | FK a tabla instituciones |
| `fecha_corte` | date | Fecha de corte del reporte |
| **Balance General** | | |
| `activo_total` | numeric | Activos totales |
| `inversiones_financieras` | numeric | Inversiones financieras |
| `cartera_total` | numeric | Cartera de crédito total |
| `captacion_total` | numeric | Captación total |
| `capital_contable` | numeric | Capital contable |
| **Rentabilidad** | | |
| `resultado_neto` | numeric | Resultado neto del periodo |
| `roa_12m` | numeric | Return on Assets 12 meses |
| `roe_12m` | numeric | Return on Equity 12 meses |
| **Calidad de Cartera** | | |
| `imor` | numeric | Índice de Morosidad |
| `icor` | numeric | Índice de Cobertura |
| `perdida_esperada` | numeric | Pérdida esperada total |
| **Capitalización** | | |
| `icap_total` | numeric | Índice de Capitalización |
| **Tasas** | | |
| `tda_cartera_total` | numeric | Tasa de crecimiento anual |
| `tasa_sistema` | numeric | Tasa del sistema |
| `tasa_invex_consumo` | numeric | Tasa INVEX consumo |
| `tasa_mn` | numeric | Tasa moneda nacional |
| `tasa_me` | numeric | Tasa moneda extranjera |
| **Etapas IFRS 9** | | |
| `ct_etapa_1` | numeric | Cartera etapa 1 |
| `ct_etapa_2` | numeric | Cartera etapa 2 |
| `ct_etapa_3` | numeric | Cartera etapa 3 |
| **Reservas y Quebrantos** | | |
| `reservas_etapa_todas` | numeric | Reservas totales |
| `reservas_variacion_mm` | numeric | Variación mensual reservas |
| `quebrantos_cc` | numeric | Quebrantos cartera comercial |
| `quebrantos_vs_cartera_cc` | numeric | Quebrantos vs cartera comercial (ratio) |

---

### 7. instituciones (4 columnas, 0 registros)

**Descripción:** Catálogo de instituciones bancarias. Actualmente sin datos.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Identificador único de la institución |
| `nombre_oficial` | varchar(255) | Nombre oficial completo de la institución |
| `nombre_corto` | varchar(100) | Nombre corto o abreviatura |
| `es_sistema` | boolean | Flag si es "Sistema Bancario" (agregado) |

---

### 8. query_logs (18 columnas, 0 registros)

**Descripción:** Log de consultas SQL generadas por el asistente de Bank Advisor. Almacena historial de interacciones para análisis y mejora del RAG.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | Identificador único del log |
| `query_id` | uuid | UUID único de la consulta |
| `timestamp` | timestamp with time zone | Fecha y hora de la consulta |
| **Query** | | |
| `user_query` | text | Pregunta original del usuario en lenguaje natural |
| `generated_sql` | text | Query SQL generada por el sistema |
| `banco` | varchar(50) | Banco consultado |
| `metric` | varchar(100) | Métrica principal consultada |
| `intent` | varchar(50) | Intención detectada (comparar, tendencia, etc.) |
| **Ejecución** | | |
| `success` | boolean | Si la query se ejecutó exitosamente |
| `execution_time_ms` | double precision | Tiempo de ejecución en milisegundos |
| `result_row_count` | integer | Cantidad de filas retornadas |
| `error_message` | text | Mensaje de error (si aplica) |
| **Pipeline y Modo** | | |
| `pipeline_used` | varchar(20) | Pipeline utilizado (rag, direct, hybrid) |
| `mode` | varchar(20) | Modo de operación (chat, api, etc.) |
| `filters` | jsonb | Filtros aplicados en formato JSON |
| **RAG Feedback** | | |
| `seeded_to_rag` | boolean | Si fue agregada al índice RAG |
| `seed_timestamp` | timestamp with time zone | Cuándo fue agregada al RAG |
| `rag_confidence` | double precision | Nivel de confianza del RAG (0-1) |

---

### 9. rag_feedback_candidates (10 columnas, 0 registros)

**Descripción:** Candidatos para retroalimentación del sistema RAG. Queries exitosas que podrían mejorar el índice vectorial.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `query_id` | uuid | UUID de la query original |
| `timestamp` | timestamp with time zone | Fecha y hora de la consulta |
| `query_age` | interval | Edad de la query (calculada) |
| **Query Info** | | |
| `user_query` | text | Pregunta del usuario |
| `generated_sql` | text | SQL generada |
| `banco` | varchar(50) | Banco consultado |
| `metric` | varchar(100) | Métrica consultada |
| `intent` | varchar(50) | Intención de la consulta |
| **Métricas** | | |
| `execution_time_ms` | double precision | Tiempo de ejecución |
| `rag_confidence` | double precision | Confianza del RAG |

---

## Glosario de Términos Bancarios

### Indicadores de Calidad de Cartera

- **IMOR (Índice de Morosidad):** Porcentaje de cartera vencida sobre cartera total. Indica qué porcentaje de los créditos no están siendo pagados a tiempo.
  - Fórmula: `(Cartera Vencida / Cartera Total) × 100`

- **ICOR (Índice de Cobertura):** Porcentaje de reservas sobre cartera vencida. Indica qué tan bien están cubiertas las pérdidas potenciales.
  - Fórmula: `(Reservas / Cartera Vencida) × 100`

- **Pérdida Esperada:** Estimación de pérdidas futuras basada en modelos de riesgo crediticio.

### Indicadores de Rentabilidad

- **ROA (Return on Assets):** Rentabilidad sobre activos. Mide qué tan eficientemente se usan los activos para generar utilidades.
  - Fórmula: `(Resultado Neto / Activo Total) × 100`

- **ROE (Return on Equity):** Rentabilidad sobre capital. Mide el retorno para los accionistas.
  - Fórmula: `(Resultado Neto / Capital Contable) × 100`

### Indicadores de Capitalización

- **ICAP (Índice de Capitalización):** Mide la suficiencia de capital del banco según regulación de Basilea III.

### Clasificación IFRS 9 (Etapas de Crédito)

- **Etapa 1:** Créditos "performing" - Sin deterioro significativo, riesgo bajo
- **Etapa 2:** Créditos "under-performing" - Incremento significativo en riesgo pero sin incumplimiento
- **Etapa 3:** Créditos "non-performing" - Cartera vencida o con evidencia objetiva de deterioro

### Otros Términos

- **Quebrantos:** Pérdidas definitivas por créditos que ya no se pueden recuperar (castigos)
- **Reservas:** Provisiones contables para cubrir pérdidas esperadas
- **Captación:** Depósitos y otros pasivos con clientes
- **TDA (Tasa de Crecimiento):** Tasa de crecimiento anual

---

## Relaciones entre Tablas

```
instituciones (1) ----< (N) metricas_financieras
                              └── FK: institucion_id

segmentos_cartera (1) ----< (N) metricas_cartera_segmentada
                                 └── Relación implícita por segmento_codigo

query_logs (1) ----< (N) rag_feedback_candidates
                          └── Relación por query_id
```

---

## Notas Técnicas

### Migración a GCP
- Fecha de migración: 2025-12-05
- Versión desplegada: 1.2.2
- La base de datos GCP contiene datos más actualizados que la instancia local

### Uso en Producción
- El servicio `bank-advisor` se conecta a esta base de datos en producción
- La instancia local de PostgreSQL está deshabilitada en producción (profile: local)
- Variables de entorno configuradas en `/home/jf/octavios-chat-bajaware_invex/envs/.env`

### Datos Actuales
- **monthly_kpis:** 721 registros mensuales de KPIs consolidados
- **metricas_cartera_segmentada:** 2,445 registros de métricas por segmento
- **metricas_financieras_ext:** 162 registros de métricas financieras extendidas
- Total de datos bancarios: 3,344 registros

---

## Contacto y Mantenimiento

**Propietario:** Bank Advisor Plugin - Octavio's Chat (INVEX)
**Mantenedor:** Equipo de Desarrollo
**Última revisión:** 2025-12-05
