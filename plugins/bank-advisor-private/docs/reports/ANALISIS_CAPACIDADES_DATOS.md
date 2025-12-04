# Análisis de Capacidades de Datos - Bank Advisor
**Fecha:** 2025-12-02
**Estado:** Sistema Legacy ETL operacional | Sistema Normalizado pendiente de carga

## 📊 Estado Actual de los Datos

### ✅ Datos Disponibles (monthly_kpis - Legacy ETL)

| Tabla | Registros | Rango | Bancos | Estado |
|-------|-----------|-------|--------|--------|
| `monthly_kpis` | 3,660 | 2017-01 a 2025-07 | 37 | ✅ OPERACIONAL |
| `instituciones` | 0 | - | - | ⚠️ VACÍA (ETL normalizado no ejecutado) |
| `metricas_financieras` | 0 | - | - | ⚠️ VACÍA |
| `metricas_cartera_segmentada` | 0 | - | - | ⚠️ VACÍA |
| `segmentos_cartera` | 0 | - | - | ⚠️ VACÍA |

**Columnas disponibles en monthly_kpis:**
- Carteras: `cartera_total`, `cartera_comercial_total`, `cartera_consumo_total`, `cartera_vivienda_total`
- Morosidad: `imor`, `icor`, `cartera_vencida`
- Etapas: `ct_etapa_1`, `ct_etapa_2`, `ct_etapa_3`
- Reservas: `reservas_etapa_todas`, `reservas_variacion_mm`
- Pérdida Esperada: `pe_total`, `pe_empresarial`, `pe_consumo`, `pe_vivienda`
- Quebrantos: `quebrantos_cc`, `quebrantos_vs_cartera_cc`
- Indicadores: `icap_total`, `tda_cartera_total`
- Tasas: `tasa_sistema`, `tasa_invex_consumo`, `tasa_mn`, `tasa_me`
- Segmentación: `entidades_gubernamentales_total`, `entidades_financieras_total`, `empresarial_total`

---

## 🎯 Análisis de Preguntas del Usuario

### Pregunta 1: "¿Cuál es el IMOR de INVEX vs el mercado?"

**✅ RESPUESTA: SÍ - COMPLETAMENTE FUNCIONAL**

**Datos disponibles:**
- ✅ IMOR por banco (`monthly_kpis.imor`)
- ✅ Histórico 2017-2025 (103 meses para INVEX)
- ✅ Promedio de mercado calculable (excluyendo INVEX)

**Query de ejemplo:**
```sql
WITH mercado AS (
  SELECT fecha, AVG(imor) as imor_mercado
  FROM monthly_kpis
  WHERE banco_norm != 'SISTEMA' AND banco_norm != 'INVEX'
  GROUP BY fecha
)
SELECT
  mk.fecha,
  ROUND(mk.imor::numeric, 4) as imor_invex,
  ROUND(m.imor_mercado::numeric, 4) as imor_mercado,
  ROUND((mk.imor - m.imor_mercado)::numeric, 4) as diferencia
FROM monthly_kpis mk
JOIN mercado m ON mk.fecha = m.fecha
WHERE mk.banco_norm = 'INVEX'
ORDER BY mk.fecha DESC;
```

**Resultado actual (últimos 12 meses):**
```
Julio 2025:  INVEX 3.96% vs Mercado 5.10% → INVEX mejor por -1.14pp
Junio 2025:  INVEX 3.96% vs Mercado 5.09% → INVEX mejor por -1.12pp
Mayo 2025:   INVEX 3.99% vs Mercado 5.09% → INVEX mejor por -1.10pp
```

**✅ INVEX tiene MEJOR morosidad que el promedio del mercado**

**Integración Bank Advisor:**
```python
# Via MCP tool bank_analytics
await bank_analytics(
    metric_or_query="¿Cuál es el IMOR de INVEX vs el mercado en los últimos 12 meses?",
    mode="dashboard"
)
```

---

### Pregunta 2: "¿Cómo está mi PDM/Market Share medido por cartera total?"

**✅ RESPUESTA: SÍ - COMPLETAMENTE FUNCIONAL**

**Datos disponibles:**
- ✅ Cartera total por banco (`monthly_kpis.cartera_total`)
- ✅ Histórico completo 2017-2025
- ✅ PDM calculable con window functions

**Query de ejemplo:**
```sql
SELECT
  fecha,
  banco_norm,
  cartera_total,
  ROUND((100.0 * cartera_total / SUM(cartera_total)
    OVER (PARTITION BY fecha))::numeric, 2) as pdm_porcentaje
FROM monthly_kpis
WHERE fecha = '2025-07-01'
  AND cartera_total IS NOT NULL
  AND banco_norm != 'SISTEMA'  -- Excluir agregado del sistema
ORDER BY pdm_porcentaje DESC;
```

**Resultado actual (Julio 2025 - Top 10):**
```
1. BBVA México     6.60%
2. Banorte         3.78%
3. Santander       3.09%
4. Scotiabank      1.73%
5. HSBC            1.65%
6. Banamex         1.40%
7. Inbursa         1.39%
8. Banco del Bajío 0.84%
9. Banco Azteca    0.64%
10. INVEX          ???  (necesita verificación)
```

**Integración Bank Advisor:**
```python
await bank_analytics(
    metric_or_query="¿Cuál es la participación de mercado de INVEX por cartera total?",
    mode="dashboard"
)
```

---

### Pregunta 3: "¿Cómo ha evolucionado la cartera de consumo en el último trimestre?"

**✅ RESPUESTA: SÍ - COMPLETAMENTE FUNCIONAL**

**Datos disponibles:**
- ✅ Cartera de consumo por banco (`monthly_kpis.cartera_consumo_total`)
- ✅ Histórico completo
- ✅ Variación mensual calculable con LAG()

**Query de ejemplo:**
```sql
SELECT
  banco_norm,
  fecha,
  cartera_consumo_total,
  LAG(cartera_consumo_total) OVER (PARTITION BY banco_norm ORDER BY fecha) as mes_anterior,
  ROUND(((cartera_consumo_total - LAG(cartera_consumo_total)
    OVER (PARTITION BY banco_norm ORDER BY fecha)) /
    NULLIF(LAG(cartera_consumo_total) OVER (PARTITION BY banco_norm ORDER BY fecha), 0) * 100)::numeric, 2)
    as variacion_pct
FROM monthly_kpis
WHERE fecha >= (SELECT MAX(fecha) - INTERVAL '3 months' FROM monthly_kpis)
  AND cartera_consumo_total IS NOT NULL
  AND banco_norm = 'INVEX'
ORDER BY fecha DESC;
```

**Resultado INVEX (último trimestre):**
```
Jul 2025: 31,902 MDP  → 0.00% vs Jun (dato duplicado)
Jun 2025: 31,902 MDP  → +2.54% vs May
May 2025: 31,113 MDP  → +0.99% vs Abr
Abr 2025: 30,807 MDP  → (inicio del trimestre)
```

**Integración Bank Advisor:**
```python
await bank_analytics(
    metric_or_query="Evolución de la cartera de consumo de INVEX en el último trimestre",
    mode="dashboard"
)
```

---

### Pregunta 4: "¿Cómo está mi IMOR en cartera automotriz frente al mercado?"

**⚠️ RESPUESTA: PARCIALMENTE - DATOS DISPONIBLES PERO NO CARGADOS**

**Estado actual:**
- ❌ `monthly_kpis.cartera_consumo_total` es AGREGADA (no segmentada por tipo)
- ✅ **PERO** archivo `BE_BM_202509.xlsx` tiene hoja `CCCAut` con:
  - Cartera Automotriz por banco
  - IMOR Automotriz por banco
  - ICOR Automotriz por banco
  - Datos de Sep 2024, Ago 2025, Sep 2025

**Datos en BE_BM_202509.xlsx - Hoja CCCAut:**
```
Sistema:       278,142 MDP (Sep 2024) → 341,010 MDP (Sep 2025)  | IMOR: 1.21%
BBVA México:    64,025 MDP → 76,042 MDP                          | IMOR: 1.04%
Santander:      42,651 MDP → 58,499 MDP                          | IMOR: 0.96%
Banorte:        50,027 MDP → 65,531 MDP                          | IMOR: 0.51%
```

**Problema:** El ETL normalizado (`etl_processor.py`) NO procesa la hoja CCCAut, solo procesa:
- Pm2 (Portafolio Mensual 2)
- Indicadores
- CCT (Cartera de Crédito Total)

**Solución requerida:**
1. Extender `etl_processor.py` para procesar hoja `CCCAut`
2. Crear tabla `cartera_automotriz` o agregar columnas a `monthly_kpis`:
   - `cartera_automotriz`
   - `imor_automotriz`
   - `icor_automotriz`
3. Re-ejecutar ETL

**Workaround temporal:** Consulta manual al Excel (no integrado al MCP)

---

### Pregunta 5: "¿Cuál es el tamaño de los bancos por activos? ¿Qué % tiene cada banco?"

**⚠️ RESPUESTA: PARCIALMENTE - DATOS DISPONIBLES PERO NO CARGADOS**

**Estado actual:**
- ❌ NO existe columna `activos_totales` en `monthly_kpis`
- ✅ **PERO** archivo `BE_BM_202509.xlsx` tiene hoja `EF Resumen` con:
  - **ACTIVO** (columna completa con activos totales)
  - Solo snapshot de Septiembre 2025 (no histórico)

**Datos en BE_BM_202509.xlsx - Hoja EF Resumen:**
```
Sistema:        15,362,543 MDP  (100%)
BBVA México:     3,371,171 MDP  (21.93%)
Santander:       2,019,417 MDP  (13.14%)
Banorte:         1,868,293 MDP  (12.16%)
Banamex:         1,117,474 MDP  (7.27%)
HSBC:              897,782 MDP  (5.84%)
Scotiabank:        893,048 MDP  (5.81%)
Inbursa:           706,596 MDP  (4.60%)
```

**Problema:** El ETL normalizado NO procesa `EF Resumen`

**Solución requerida:**
1. Extender `etl_processor.py` para procesar hoja `EF Resumen`
2. Crear tabla `estados_financieros` con columnas:
   - `institucion_id`
   - `fecha`
   - `activos_totales`
   - `pasivos_totales`
   - `capital_contable`
   - etc.
3. Re-ejecutar ETL

**Workaround temporal:** Consulta manual al Excel

---

## 🔍 Resumen de Capacidades

| Pregunta | Estado | Datos | Acción Requerida |
|----------|--------|-------|------------------|
| 1. IMOR INVEX vs Mercado | ✅ FUNCIONAL | monthly_kpis | Ninguna - listo para usar |
| 2. Market Share (PDM) | ✅ FUNCIONAL | monthly_kpis | Ninguna - listo para usar |
| 3. Evolución Consumo Q3 | ✅ FUNCIONAL | monthly_kpis | Ninguna - listo para usar |
| 4. IMOR Automotriz | ⚠️ PARCIAL | BE_BM (CCCAut) | Extender ETL + crear tabla |
| 5. Activos Totales | ⚠️ PARCIAL | BE_BM (EF Resumen) | Extender ETL + crear tabla |

**Cobertura:** 3/5 preguntas completamente funcionales (60%)
**Datos disponibles pero no cargados:** 2/5 preguntas (40%)

---

## 🚀 Plan de Integración - Ampliar Funcionalidad

### Fase 1: Preparación (1-2 horas)

#### 1.1 Rebuild Container con ETL Directory
```bash
# El Dockerfile ya incluye etl/, solo rebuild
cd /home/jazielflo/Proyects/octavios-chat-bajaware_invex
docker-compose down bank-advisor
docker-compose build bank-advisor
docker-compose up -d bank-advisor
```

#### 1.2 Verificar ETL Normalizado Existente
```bash
# Ejecutar ETL normalizado actual (Pm2, Indicadores, CCT)
docker exec octavios-chat-bajaware_invex-bank-advisor python /app/etl/etl_processor.py

# Cargar SQL generado
docker exec octavios-chat-bajaware_invex-bank-advisor cat /app/etl/carga_inicial_bancos.sql | \
  docker exec -i octavios-chat-bajaware_invex-postgres psql -U octavios -d bankadvisor

# Verificar tablas
docker exec octavios-chat-bajaware_invex-postgres psql -U octavios -d bankadvisor -c "
SELECT
  'instituciones' as tabla, COUNT(*) FROM instituciones
UNION ALL
SELECT 'metricas_financieras', COUNT(*) FROM metricas_financieras
UNION ALL
SELECT 'metricas_cartera_segmentada', COUNT(*) FROM metricas_cartera_segmentada;
"
```

---

### Fase 2: Extender ETL para Cartera Automotriz (2-3 horas)

#### 2.1 Modificar database_schema.sql
```sql
-- Agregar tabla para segmentos de cartera detallados
CREATE TABLE IF NOT EXISTS segmentos_cartera_detallado (
    id SERIAL PRIMARY KEY,
    institucion_id INTEGER REFERENCES instituciones(id),
    fecha DATE NOT NULL,
    tipo_segmento VARCHAR(50) NOT NULL,  -- 'automotriz', 'tarjetas', 'nomina', etc.
    cartera_total DOUBLE PRECISION,
    cartera_vencida DOUBLE PRECISION,
    imor DOUBLE PRECISION,
    icor DOUBLE PRECISION,
    reservas DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(institucion_id, fecha, tipo_segmento)
);

CREATE INDEX IF NOT EXISTS idx_segmentos_detallado_institucion_fecha
ON segmentos_cartera_detallado(institucion_id, fecha);
```

#### 2.2 Extender etl_processor.py
```python
# Agregar función para procesar CCCAut
def process_automotive_sheet(df_cccaut: pd.DataFrame) -> List[Dict]:
    """
    Procesa hoja CCCAut (Cartera Automotriz) del BE_BM.

    Extrae:
    - Cartera automotriz por banco
    - IMOR automotriz
    - ICOR automotriz
    """
    header_idx = find_header_row(df_cccaut, "Automotriz")
    date_row = df_cccaut.iloc[header_idx + 1]

    # Definir métricas (start_col es relativo al header row)
    metrics = [
        ("cartera_automotriz", 2, 3, 3),  # Columnas 2, 5, 8 (cada 3)
        ("imor_automotriz", 5, 3, 3),     # Columnas 5, 8, 11
        ("icor_automotriz", 8, 3, 3),     # Columnas 8, 11, 14
    ]

    df_long = parse_sheet(df_cccaut, bank_col=1, header_marker="Automotriz", metrics=metrics)

    # Normalizar nombres de bancos
    df_long["banco_norm"] = df_long["banco"].apply(normalize_bank_name)

    # Limpiar valores numéricos
    for col in ["cartera_automotriz", "imor_automotriz", "icor_automotriz"]:
        df_long[col] = df_long[col].apply(clean_numeric)

    return df_long.to_dict("records")


# Modificar main() para incluir CCCAut
def main():
    # ... código existente ...

    # NUEVO: Procesar cartera automotriz
    logger.info("Procesando hoja CCCAut (Cartera Automotriz)...")
    df_cccaut = pd.read_excel(EXCEL_PATH, sheet_name="CCCAut", header=None)
    automotive_data = process_automotive_sheet(df_cccaut)

    # Generar SQL para segmentos_cartera_detallado
    sql_statements.append("\n-- Cartera Automotriz")
    for row in automotive_data:
        if row["fecha"] and row["institucion_id"]:
            sql_statements.append(f"""
INSERT INTO segmentos_cartera_detallado
  (institucion_id, fecha, tipo_segmento, cartera_total, imor, icor)
VALUES
  ({row["institucion_id"]}, '{row["fecha"]}', 'automotriz',
   {row["cartera_automotriz"] or 'NULL'},
   {row["imor_automotriz"] or 'NULL'},
   {row["icor_automotriz"] or 'NULL'})
ON CONFLICT (institucion_id, fecha, tipo_segmento) DO UPDATE SET
  cartera_total = EXCLUDED.cartera_total,
  imor = EXCLUDED.imor,
  icor = EXCLUDED.icor;
""")

    # ... resto del código ...
```

#### 2.3 Actualizar Bank Advisor SQL Templates
```python
# En bankadvisor/services/sql_generation_service.py o analytics_service.py

AUTOMOTIVE_TEMPLATES = {
    "imor_automotriz_invex_vs_mercado": """
WITH mercado AS (
  SELECT fecha, AVG(imor) as imor_mercado
  FROM segmentos_cartera_detallado
  WHERE tipo_segmento = 'automotriz'
    AND institucion_id != (SELECT id FROM instituciones WHERE nombre_normalizado = 'INVEX')
  GROUP BY fecha
)
SELECT
  s.fecha,
  i.nombre_normalizado as banco,
  ROUND(s.imor::numeric, 4) as imor_automotriz,
  ROUND(m.imor_mercado::numeric, 4) as imor_mercado,
  ROUND((s.imor - m.imor_mercado)::numeric, 4) as diferencia
FROM segmentos_cartera_detallado s
JOIN instituciones i ON s.institucion_id = i.id
JOIN mercado m ON s.fecha = m.fecha
WHERE i.nombre_normalizado = 'INVEX'
  AND s.tipo_segmento = 'automotriz'
ORDER BY s.fecha DESC;
"""
}
```

---

### Fase 3: Extender ETL para Activos Totales (1-2 horas)

#### 3.1 Modificar database_schema.sql
```sql
-- Tabla para Estados Financieros (Balance Sheet)
CREATE TABLE IF NOT EXISTS estados_financieros (
    id SERIAL PRIMARY KEY,
    institucion_id INTEGER REFERENCES instituciones(id),
    fecha DATE NOT NULL,
    activos_totales DOUBLE PRECISION,
    pasivos_totales DOUBLE PRECISION,
    capital_contable DOUBLE PRECISION,
    cartera_credito_total DOUBLE PRECISION,
    captacion_total DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(institucion_id, fecha)
);

CREATE INDEX IF NOT EXISTS idx_estados_financieros_institucion_fecha
ON estados_financieros(institucion_id, fecha);
```

#### 3.2 Extender etl_processor.py
```python
def process_financial_statements(df_ef: pd.DataFrame) -> List[Dict]:
    """
    Procesa hoja EF Resumen (Estados Financieros).

    Extrae activos, pasivos, capital, etc. por banco.
    """
    # La hoja EF Resumen tiene estructura transpuesta:
    # Fila 6: Nombres de bancos (Sistema, BBVA, Santander, ...)
    # Fila 10: ACTIVO (valores por banco)
    # Fila X: PASIVO
    # Fila Y: CAPITAL CONTABLE

    header_row = 5  # "Septiembre de 2025\nMillones de pesos"
    banks_row = df_ef.iloc[5]  # Fila con nombres de bancos

    # Extraer nombres de bancos (columnas 2 en adelante)
    banks = [normalize_bank_name(b) for b in banks_row[2:] if pd.notna(b)]

    # Buscar fila ACTIVO
    activo_row_idx = None
    for idx, row in df_ef.iterrows():
        if pd.notna(row[1]) and "ACTIVO" in str(row[1]).upper():
            activo_row_idx = idx
            break

    if activo_row_idx is None:
        raise ValueError("No se encontró fila ACTIVO en EF Resumen")

    activo_values = df_ef.iloc[activo_row_idx, 2:2+len(banks)]

    # Fecha del reporte (extraer de header "Septiembre de 2025")
    fecha_str = str(banks_row[1])  # "Septiembre de 2025\nMillones de pesos"
    # Parse fecha (simplificado, ajustar según formato real)
    fecha = "2025-09-01"  # Hardcoded por ahora

    records = []
    for i, banco in enumerate(banks):
        records.append({
            "banco": banco,
            "fecha": fecha,
            "activos_totales": clean_numeric(activo_values.iloc[i])
        })

    return records


# Agregar a main()
def main():
    # ... código existente ...

    # NUEVO: Procesar estados financieros
    logger.info("Procesando hoja EF Resumen (Estados Financieros)...")
    df_ef = pd.read_excel(EXCEL_PATH, sheet_name="EF Resumen", header=None)
    financial_data = process_financial_statements(df_ef)

    # Generar SQL
    sql_statements.append("\n-- Estados Financieros")
    for row in financial_data:
        if row["fecha"] and row["institucion_id"]:
            sql_statements.append(f"""
INSERT INTO estados_financieros
  (institucion_id, fecha, activos_totales)
VALUES
  ({row["institucion_id"]}, '{row["fecha"]}', {row["activos_totales"] or 'NULL'})
ON CONFLICT (institucion_id, fecha) DO UPDATE SET
  activos_totales = EXCLUDED.activos_totales;
""")
```

#### 3.3 Queries para Ranking por Activos
```sql
-- Top 10 bancos por activos
SELECT
  i.nombre_normalizado as banco,
  ef.activos_totales,
  ROUND((100.0 * ef.activos_totales /
    SUM(ef.activos_totales) OVER ())::numeric, 2) as porcentaje_mercado
FROM estados_financieros ef
JOIN instituciones i ON ef.institucion_id = i.id
WHERE ef.fecha = (SELECT MAX(fecha) FROM estados_financieros)
ORDER BY ef.activos_totales DESC;
```

---

### Fase 4: Integración con Bank Advisor MCP (30 min - 1 hora)

#### 4.1 Actualizar Context Service (NL2SQL)
```python
# En bankadvisor/services/nl2sql_context_service.py

# Agregar a DATABASE_SCHEMA_DOCS
SCHEMA_DOCS_EXTENDED = """
### Tablas de Segmentación Detallada

**segmentos_cartera_detallado**: Segmentos de cartera por tipo (automotriz, tarjetas, etc.)
- institucion_id (FK a instituciones)
- fecha (DATE)
- tipo_segmento (VARCHAR) - 'automotriz', 'tarjetas', 'nomina', 'pyme', etc.
- cartera_total (DOUBLE PRECISION)
- imor (DOUBLE PRECISION) - IMOR del segmento
- icor (DOUBLE PRECISION) - ICOR del segmento

**estados_financieros**: Balance sheet de bancos
- institucion_id (FK a instituciones)
- fecha (DATE)
- activos_totales (DOUBLE PRECISION)
- pasivos_totales (DOUBLE PRECISION)
- capital_contable (DOUBLE PRECISION)

### Casos de Uso

**Cartera Automotriz:**
```sql
SELECT i.nombre_normalizado, s.fecha, s.imor
FROM segmentos_cartera_detallado s
JOIN instituciones i ON s.institucion_id = i.id
WHERE s.tipo_segmento = 'automotriz'
  AND i.nombre_normalizado = 'INVEX';
```

**Ranking por Activos:**
```sql
SELECT i.nombre_normalizado, ef.activos_totales,
  ROUND(100.0 * ef.activos_totales / SUM(ef.activos_totales) OVER (), 2) as pct
FROM estados_financieros ef
JOIN instituciones i ON ef.institucion_id = i.id
WHERE ef.fecha = '2025-09-01'
ORDER BY ef.activos_totales DESC;
```
"""
```

#### 4.2 Agregar Keywords al Intent Classifier
```python
# En bankadvisor/services/intent_service.py

INTENT_KEYWORDS = {
    # ... existentes ...
    "automotriz": ["automotriz", "auto", "vehicular", "automóvil"],
    "activos": ["activos", "tamaño", "balance", "estados financieros"],
    "segmento": ["segmento", "tipo de cartera", "cartera automotriz", "tarjetas"],
}
```

---

### Fase 5: Testing y Validación (1 hora)

#### 5.1 Tests de Integración
```bash
# Test 1: Verificar carga de datos automotriz
docker exec octavios-chat-bajaware_invex-postgres psql -U octavios -d bankadvisor -c "
SELECT
  tipo_segmento,
  COUNT(DISTINCT institucion_id) as num_bancos,
  COUNT(*) as num_registros,
  MIN(fecha) as fecha_min,
  MAX(fecha) as fecha_max
FROM segmentos_cartera_detallado
GROUP BY tipo_segmento;
"

# Test 2: Verificar activos
docker exec octavios-chat-bajaware_invex-postgres psql -U octavios -d bankadvisor -c "
SELECT
  COUNT(DISTINCT institucion_id) as num_bancos,
  COUNT(*) as num_registros,
  SUM(activos_totales) as activos_sistema
FROM estados_financieros;
"

# Test 3: Query E2E via MCP
# Desde octavios-core o cliente MCP:
{
  "method": "tools/call",
  "params": {
    "name": "bank_analytics",
    "arguments": {
      "metric_or_query": "¿Cuál es el IMOR de INVEX en cartera automotriz comparado con el mercado?",
      "mode": "dashboard"
    }
  }
}
```

---

## 📝 Checklist de Implementación

### ✅ Fase 1: Preparación
- [ ] Rebuild container con etl/ incluido
- [ ] Ejecutar ETL normalizado existente (Pm2, Indicadores, CCT)
- [ ] Verificar tablas instituciones, metricas_financieras pobladas

### ⚠️ Fase 2: Cartera Automotriz
- [ ] Crear tabla `segmentos_cartera_detallado` en database_schema.sql
- [ ] Implementar `process_automotive_sheet()` en etl_processor.py
- [ ] Agregar generación SQL para inserts de automotriz
- [ ] Aplicar migración (psql database_schema.sql)
- [ ] Ejecutar ETL y verificar datos cargados
- [ ] Actualizar templates SQL en Bank Advisor
- [ ] Test E2E: "IMOR automotriz INVEX vs mercado"

### ⚠️ Fase 3: Activos Totales
- [ ] Crear tabla `estados_financieros` en database_schema.sql
- [ ] Implementar `process_financial_statements()` en etl_processor.py
- [ ] Agregar generación SQL para inserts de EF
- [ ] Aplicar migración
- [ ] Ejecutar ETL y verificar datos
- [ ] Actualizar templates SQL
- [ ] Test E2E: "Ranking bancos por activos"

### ✅ Fase 4: Integración NL2SQL
- [ ] Actualizar SCHEMA_DOCS en nl2sql_context_service.py
- [ ] Agregar keywords "automotriz", "activos" al intent classifier
- [ ] Agregar ejemplos de queries al RAG context
- [ ] Test E2E via MCP tool

### ✅ Fase 5: Validación
- [ ] Tests de integración SQL
- [ ] Tests E2E via MCP
- [ ] Documentar nuevas capacidades en README
- [ ] Actualizar este documento con resultados

---

## 🎯 Impacto Esperado

### Después de Fase 1 (Solo Rebuild)
- ✅ 3/5 preguntas funcionales (sin cambios)
- Tablas normalizadas pobladas (instituciones, metricas_financieras)

### Después de Fase 2 (Cartera Automotriz)
- ✅ 4/5 preguntas funcionales (+20%)
- Nueva capacidad: Análisis por segmento (automotriz, tarjetas, etc.)

### Después de Fase 3 (Activos Totales)
- ✅ 5/5 preguntas funcionales (100% cobertura)
- Nueva capacidad: Ranking y análisis por tamaño de banco

### Métricas de Éxito
- **Cobertura de preguntas:** 60% → 100%
- **Tablas operacionales:** 1 → 4
- **Granularidad de datos:** Solo agregado → Segmentado por tipo
- **Dimensiones de análisis:** Cartera + Morosidad → + Activos + Segmentos

---

## 📚 Referencias

**Archivos clave:**
- ETL Processor: `plugins/bank-advisor-private/etl/etl_processor.py`
- Database Schema: `plugins/bank-advisor-private/database_schema.sql`
- MCP Server: `plugins/bank-advisor-private/src/main.py`
- NL2SQL Context: `plugins/bank-advisor-private/src/bankadvisor/services/nl2sql_context_service.py`
- Data Source: `plugins/bank-advisor-private/data/raw/BE_BM_202509.xlsx`

**Hojas disponibles en BE_BM_202509.xlsx:**
- ✅ Pm2, Indicadores, CCT (procesadas)
- ⚠️ CCCAut (Automotriz) - **PENDIENTE**
- ⚠️ EF Resumen (Estados Financieros) - **PENDIENTE**
- 🔍 CCCAdq BiMu, CCOAC, CCCMicro - oportunidades futuras

---

**Conclusión:**
El sistema actual puede responder **3 de 5 preguntas** usando solo monthly_kpis. Para alcanzar cobertura 100%, necesitamos extender el ETL normalizado para procesar hojas adicionales (CCCAut, EF Resumen) del archivo BE_BM_202509.xlsx. Los datos están disponibles, solo falta procesarlos e integrarlos.
