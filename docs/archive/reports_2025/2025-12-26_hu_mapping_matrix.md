# Mapeo Técnico: Historias de Usuario → Arquitectura Multi-Agente v1.2

**Fecha:** 26 Diciembre 2025
**Versión:** 1.0
**Autor:** Jaziel Flores
**Propósito:** Detallar técnicamente cómo cada Historia de Usuario (HU) del PRD se implementa en la arquitectura multi-agente v1.2

---

## Índice

1. [HU1: Query Multi-Banco](#hu1-query-multi-banco)
2. [HU2: Comparación Multi-Banco](#hu2-comparación-multi-banco)
3. [HU3: UI Clarificación](#hu3-ui-clarificación)
4. [HU4: Multi-Métrica](#hu4-multi-métrica)
5. [HU5: RAG con CUB + Anexo 36 + Banxico](#hu5-rag-con-cub--anexo-36--banxico)
6. [HU6: ICAP Funcional](#hu6-icap-funcional)
7. [HU7: Sistema de Feedback de Usuario](#hu7-sistema-de-feedback-de-usuario)

---

## HU1: Query Multi-Banco

### Resumen
**Como** analista financiero
**Quiero** consultar métricas de BBVA, Santander, Banorte, HSBC y otros bancos
**Para** hacer benchmarking competitivo real

**Prioridad:** P0 CRÍTICO
**Story Points:** 13
**Sprint:** 1-2

### Mapeo Arquitectónico

#### Intent
**`SQL_QUERY`** - Consulta de métricas con datos reales

#### Componentes Involucrados

```
Usuario
  ↓
Router/Orchestrator (clasifica como SQL_QUERY)
  ↓
QuerySpec Builder (construye QuerySpec)
  ↓ (consulta Ontology_Terms para validar banco + métrica)
Weaviate: Ontology_Terms
  ↓
QuerySpec Builder (genera QuerySpec)
  ↓
SQL Agent (convierte QuerySpec → SQL)
  ↓
PostgreSQL (ejecuta SELECT en vw_banking_metrics)
  ↓
SQL Agent (retorna datos)
  ↓
Chart Builder (opcional, si se solicita visualización)
  ↓
Usuario (recibe respuesta)
```

#### Flujo Técnico Detallado

**1. Entrada del Usuario:**
```
"Dame el IMOR de BBVA en 2024"
```

**2. Router/Orchestrator:**
- Clasifica intent usando LLM (SAPTIVA Turbo)
- Detecta: `SQL_QUERY` (query que necesita datos)
- Delega a `QuerySpec Builder`

**3. QuerySpec Builder:**

a) **Extrae entidades ontológicas:**
- Banco: "BBVA"
- Métrica: "IMOR"
- Periodo: "2024"

b) **Consulta `Ontology_Terms` en Weaviate:**
```python
# Buscar término IMOR en ontología
term = weaviate.query.get(
    "Ontology_Terms",
    ["term_id", "term_name", "sql_column", "sql_table", "synonyms"]
).with_where({
    "path": ["term_name"],
    "operator": "Equal",
    "valueText": "Indice de Morosidad"
}).do()

# Resultado:
{
    "term_id": "term_abc123",
    "term_name": "Indice de Morosidad",
    "code": "IMOR",
    "sql_column": "imor",
    "sql_table": "vw_banking_metrics",
    "unit": "%",
    "synonyms": ["morosidad", "cartera vencida ratio"]
}
```

c) **Valida entidades:**
- ✓ Banco "BBVA" existe en whitelist
- ✓ Métrica "IMOR" tiene mapeo SQL válido
- ✓ Periodo "2024" es válido

d) **Construye QuerySpec:**
```json
{
  "intent": "SQL_QUERY",
  "bank": "BBVA",
  "metric_code": "IMOR",
  "metric_term_id": "term_abc123",
  "sql": {
    "table": "vw_banking_metrics",
    "column": "imor",
    "filters": [
      {"field": "bank_name", "op": "=", "value": "BBVA"},
      {"field": "year", "op": "=", "value": 2024}
    ],
    "time_grain": "monthly",
    "limit": 5000
  },
  "confidence": 0.95,
  "ambiguity_flags": []
}
```

**4. SQL Agent:**

a) **Valida QuerySpec con JSON Schema:**
```python
from jsonschema import validate

validate(instance=query_spec, schema=QUERY_SPEC_SCHEMA)
```

b) **Genera SQL determinista con templates:**
```sql
SELECT
    date,
    bank_name,
    imor AS metric_value,
    'IMOR' AS metric_name,
    '%' AS unit
FROM vw_banking_metrics
WHERE bank_name = 'BBVA'
  AND EXTRACT(YEAR FROM date) = 2024
ORDER BY date DESC
LIMIT 5000;
```

c) **Validación SQL (3 capas):**
- ✓ Solo SELECT (whitelist)
- ✓ Tabla segura (vw_banking_metrics en whitelist)
- ✓ Budget: <30s timeout, <5000 rows, <2 joins

d) **Ejecuta con guardrails:**
```python
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(POSTGRES_URI)
cursor = conn.cursor(cursor_factory=RealDictCursor)

# Timeout a nivel de statement
cursor.execute("SET statement_timeout = '30s'")

# Ejecutar query
cursor.execute(sql_query)
results = cursor.fetchall()

# Validar límite de rows
if len(results) > 5000:
    results = results[:5000]
    warnings.append("Result truncated to 5000 rows")
```

**5. Chart Builder (opcional):**
- Si usuario pidió visualización, genera config Plotly
- Tipo: line chart (serie temporal)
- X: date, Y: metric_value

**6. Respuesta al Usuario:**
```json
{
  "content": "El IMOR de BBVA en 2024 varió entre 2.1% (enero) y 2.4% (diciembre).",
  "data": [
    {"date": "2024-01-01", "bank_name": "BBVA", "metric_value": 2.1, "unit": "%"},
    {"date": "2024-02-01", "bank_name": "BBVA", "metric_value": 2.15, "unit": "%"},
    ...
  ],
  "chart_config": { /* Plotly config */ },
  "query_spec": { /* QuerySpec original */ },
  "sql_executed": "SELECT ...",
  "execution_time_ms": 347
}
```

#### Requisitos de Ontología

**Entidades necesarias en `Ontology_Terms`:**

Para cada banco (INVEX, BBVA, Santander, Banorte, HSBC, etc.):
```json
{
  "term_id": "bank_bbva",
  "term_name": "BBVA México",
  "code": "BBVA",
  "synonyms": ["BBVA Bancomer", "Bancomer"],
  "sql_column": null,  // Los bancos no son columnas
  "sql_table": null,
  "category": "bank_entity",
  "metadata": {
    "bank_code_cnbv": "40012"
  }
}
```

Para cada métrica (IMOR, ICOR, ICAP, etc.):
```json
{
  "term_id": "metric_imor",
  "term_name": "Índice de Morosidad",
  "code": "IMOR",
  "definition": "Porcentaje de cartera vencida sobre cartera total",
  "formula_text": "IMOR = (Cartera Vencida / Cartera Total) × 100",
  "sql_column": "imor",
  "sql_table": "vw_banking_metrics",
  "unit": "%",
  "category": "riesgo",
  "synonyms": ["morosidad", "índice de mora", "cartera vencida ratio"],
  "source_refs": ["pdf:cub_glosario.pdf#p42", "cnbv:anexo_36"]
}
```

#### Criterios Técnicos de Éxito

**PoC QuerySpec (Día 6 - GATE BLOQUEANTE):**
- [ ] ≥ 90% QuerySpec válidos (JSON bien formado)
- [ ] ≥ 90% QuerySpec alineados con ontología (no columnas inventadas)
- [ ] 0% SQL destructivo (solo SELECT; validado)

**Datos (ETL Ontológico):**
- [ ] ≥ 100 términos en `Ontology_Terms` con mapeo SQL
- [ ] Top 20 términos críticos con `manual_overrides.yml`
- [ ] 10 bancos accesibles vía NL2SQL

**Performance:**
- [ ] Latencia p50 < 3s (desde query NL hasta respuesta)
- [ ] Query success rate ≥ 85%

**Validación:**
- [ ] Validación 3 capas activa (Intent, QuerySpec, SQL)
- [ ] SQL validator rechaza UPDATE/DELETE/DROP
- [ ] Budget enforced: 30s timeout, 5000 rows max

---

## HU2: Comparación Multi-Banco

### Resumen
**Como** C-Level
**Quiero** comparar "IMOR de INVEX vs BBVA vs Santander"
**Para** entender mi posición competitiva

**Prioridad:** P0 CRÍTICO
**Story Points:** 8
**Sprint:** 2-3

### Mapeo Arquitectónico

#### Intent
**`SQL_QUERY` + `VISUALIZATION`** - Query multi-banco con visualización comparativa

#### Componentes Involucrados

```
Usuario
  ↓
Router/Orchestrator (clasifica como SQL_QUERY + VISUALIZATION)
  ↓
QuerySpec Builder (construye QuerySpec con múltiples bancos)
  ↓
Weaviate: Ontology_Terms (valida bancos + métrica)
  ↓
SQL Agent (genera SQL con IN clause para múltiples bancos)
  ↓
PostgreSQL (ejecuta SELECT multi-banco)
  ↓
Chart Builder (genera comparativa multi-serie)
  ↓
Usuario (recibe gráfica + tabla resumen)
```

#### Flujo Técnico Detallado

**1. Entrada del Usuario:**
```
"Compara el IMOR de INVEX vs BBVA vs Santander en 2024"
```

**2. Router/Orchestrator:**
- Clasifica: `SQL_QUERY` + `VISUALIZATION`
- Detecta patrón de comparación ("compara", "vs")
- Delega a QuerySpec Builder con flag `comparison=true`

**3. QuerySpec Builder:**

a) **Extrae entidades:**
- Bancos: ["INVEX", "BBVA", "Santander"]
- Métrica: "IMOR"
- Periodo: "2024"
- Tipo: comparación multi-banco

b) **Construye QuerySpec multi-banco:**
```json
{
  "intent": "SQL_QUERY",
  "banks": ["INVEX", "BBVA", "Santander"],  // Múltiples bancos
  "metric_code": "IMOR",
  "metric_term_id": "metric_imor",
  "comparison_mode": true,
  "sql": {
    "table": "vw_banking_metrics",
    "column": "imor",
    "filters": [
      {"field": "bank_name", "op": "IN", "value": ["INVEX", "BBVA", "Santander"]},
      {"field": "year", "op": "=", "value": 2024}
    ],
    "group_by": ["bank_name", "date"],
    "time_grain": "monthly",
    "limit": 5000
  },
  "visualization": {
    "type": "multi_series_line",
    "series_key": "bank_name"
  },
  "confidence": 0.93
}
```

**4. SQL Agent:**

```sql
SELECT
    date,
    bank_name,
    imor AS metric_value,
    'IMOR' AS metric_name,
    '%' AS unit
FROM vw_banking_metrics
WHERE bank_name IN ('INVEX', 'BBVA', 'Santander')
  AND EXTRACT(YEAR FROM date) = 2024
ORDER BY date, bank_name
LIMIT 5000;
```

**5. Chart Builder:**

a) **Detecta modo comparación:**
```python
if query_spec.get("comparison_mode"):
    chart_type = "multi_series_line"
    series_key = "bank_name"
```

b) **Genera config Plotly:**
```json
{
  "data": [
    {
      "x": ["2024-01-01", "2024-02-01", ...],
      "y": [2.1, 2.15, 2.18, ...],
      "name": "INVEX",
      "type": "scatter",
      "mode": "lines+markers",
      "line": {"color": "#1f77b4", "width": 2}
    },
    {
      "x": ["2024-01-01", "2024-02-01", ...],
      "y": [2.4, 2.38, 2.42, ...],
      "name": "BBVA",
      "type": "scatter",
      "mode": "lines+markers",
      "line": {"color": "#ff7f0e", "width": 2}
    },
    {
      "x": ["2024-01-01", "2024-02-01", ...],
      "y": [2.25, 2.28, 2.30, ...],
      "name": "Santander",
      "type": "scatter",
      "mode": "lines+markers",
      "line": {"color": "#2ca02c", "width": 2}
    }
  ],
  "layout": {
    "title": "IMOR Comparativo: INVEX vs BBVA vs Santander (2024)",
    "xaxis": {"title": "Fecha"},
    "yaxis": {"title": "IMOR (%)", "ticksuffix": "%"},
    "legend": {"orientation": "h", "y": -0.2},
    "hovermode": "x unified"
  }
}
```

c) **Genera tabla resumen:**
```json
{
  "summary_table": [
    {"bank": "INVEX", "min": 2.10, "max": 2.30, "avg": 2.18, "latest": 2.25},
    {"bank": "BBVA", "min": 2.38, "max": 2.50, "avg": 2.43, "latest": 2.47},
    {"bank": "Santander", "min": 2.25, "max": 2.35, "avg": 2.29, "latest": 2.32}
  ]
}
```

**6. Respuesta al Usuario:**
```json
{
  "content": "Comparativa de IMOR en 2024:\n- INVEX: 2.18% promedio (mejor posición)\n- Santander: 2.29% promedio\n- BBVA: 2.43% promedio (mayor mora)",
  "chart_config": { /* Plotly multi-serie */ },
  "summary_table": [ /* Estadísticas por banco */ ],
  "interpretation": "INVEX mantiene el menor índice de morosidad del grupo durante 2024."
}
```

#### Criterios Técnicos de Éxito

**Visualización:**
- [ ] Soporta hasta 5 bancos simultáneos
- [ ] Colores distinguibles (paleta categórica automática)
- [ ] Leyenda clara con nombre de banco
- [ ] Hover muestra: fecha, banco, valor

**Datos:**
- [ ] Query retorna data para todos los bancos solicitados
- [ ] Missing data: muestra advertencia si falta algún banco

**Performance:**
- [ ] Latencia < 3s incluso con 5 bancos
- [ ] Gráfica renderiza en <500ms en frontend

---

## HU3: UI Clarificación

### Resumen
**Como** usuario nuevo
**Quiero** que el sistema me pregunte cuando mi query es ambigua
**Para** obtener resultados precisos sin errores confusos

**Prioridad:** P1 IMPORTANTE
**Story Points:** 8
**Sprint:** 2

### Mapeo Arquitectónico

#### Intent
**`ABSTENTION_MODE`** - Modo de abstención cuando confidence < 0.7

#### Componentes Involucrados

```
Usuario
  ↓ (query ambigua: "Dame datos del banco")
Router/Orchestrator
  ↓
QuerySpec Builder (detecta ambigüedad)
  ↓
Weaviate: Ontology_Terms (busca candidatos)
  ↓
QuerySpec Builder (confidence < 0.7 → ABSTENCIÓN)
  ↓
Frontend: ClarificationDialog (muestra opciones)
  ↓
Usuario (selecciona opción)
  ↓
Router/Orchestrator (reintenta con contexto)
```

#### Flujo Técnico Detallado

**1. Entrada Ambigua del Usuario:**
```
"Dame datos del banco"
```

**2. QuerySpec Builder:**

a) **Detecta ambigüedad:**
```python
# Faltan entidades críticas
missing_entities = []
if not banco_detectado:
    missing_entities.append("bank")
if not métrica_detectada:
    missing_entities.append("metric")

if missing_entities:
    confidence_score = 0.3  # Bajo por ambigüedad
```

b) **Genera candidatos desde Ontología:**
```python
# Buscar bancos disponibles
bank_candidates = weaviate.query.get(
    "Ontology_Terms",
    ["term_name", "code"]
).with_where({
    "path": ["category"],
    "operator": "Equal",
    "valueText": "bank_entity"
}).with_limit(10).do()

# Buscar métricas populares
metric_candidates = weaviate.query.get(
    "Ontology_Terms",
    ["term_name", "code", "definition"]
).with_where({
    "path": ["category"],
    "operator": "In",
    "valueText": ["riesgo", "capital", "liquidez"]
}).with_limit(5).do()
```

c) **Construye respuesta de clarificación:**
```json
{
  "intent": "CLARIFICATION_NEEDED",
  "confidence": 0.3,
  "ambiguity_flags": ["missing_bank", "missing_metric"],
  "clarification_request": {
    "message": "Tu consulta necesita más detalles. Por favor especifica:",
    "fields": [
      {
        "field": "bank",
        "question": "¿Qué banco te interesa?",
        "options": [
          {"label": "INVEX", "value": "INVEX"},
          {"label": "BBVA México", "value": "BBVA"},
          {"label": "Santander", "value": "Santander"},
          {"label": "Banorte", "value": "Banorte"}
        ],
        "allow_custom": false
      },
      {
        "field": "metric",
        "question": "¿Qué métrica quieres consultar?",
        "options": [
          {
            "label": "IMOR (Índice de Morosidad)",
            "value": "IMOR",
            "description": "Cartera vencida sobre cartera total"
          },
          {
            "label": "ICOR (Índice de Cobertura)",
            "value": "ICOR",
            "description": "Reservas sobre cartera vencida"
          },
          {
            "label": "ICAP (Índice de Capitalización)",
            "value": "ICAP",
            "description": "Capital neto sobre activos en riesgo"
          }
        ],
        "allow_custom": true
      }
    ]
  }
}
```

**3. Frontend - ClarificationDialog:**

```tsx
// apps/web/src/components/chat/ClarificationDialog.tsx

interface ClarificationDialogProps {
  clarificationRequest: ClarificationRequest;
  onSubmit: (selections: Record<string, string>) => void;
}

export function ClarificationDialog({
  clarificationRequest,
  onSubmit
}: ClarificationDialogProps) {
  const [selections, setSelections] = useState<Record<string, string>>({});

  const handleSubmit = () => {
    // Validar que se seleccionaron todos los campos requeridos
    const allFieldsSelected = clarificationRequest.fields.every(
      field => selections[field.field]
    );

    if (allFieldsSelected) {
      onSubmit(selections);
    }
  };

  return (
    <div className="clarification-dialog">
      <p>{clarificationRequest.message}</p>

      {clarificationRequest.fields.map(field => (
        <div key={field.field} className="clarification-field">
          <label>{field.question}</label>

          {field.options.map(option => (
            <button
              key={option.value}
              onClick={() => setSelections({
                ...selections,
                [field.field]: option.value
              })}
              className={selections[field.field] === option.value ? 'selected' : ''}
            >
              <strong>{option.label}</strong>
              {option.description && (
                <span className="description">{option.description}</span>
              )}
            </button>
          ))}

          {field.allow_custom && (
            <input
              type="text"
              placeholder="Otra opción..."
              onChange={(e) => setSelections({
                ...selections,
                [field.field]: e.target.value
              })}
            />
          )}
        </div>
      ))}

      <button onClick={handleSubmit}>Continuar</button>
    </div>
  );
}
```

**4. Usuario Selecciona:**
```json
{
  "bank": "BBVA",
  "metric": "IMOR"
}
```

**5. Reintento con Contexto:**
```python
# Backend recibe selecciones
refined_query = f"Dame {selections['metric']} de {selections['bank']}"

# Reenvía al Router con contexto enriquecido
router.process(
    query=refined_query,
    context={
        "clarified_entities": {
            "bank": "BBVA",
            "metric": "IMOR"
        }
    }
)
```

#### Criterios Técnicos de Éxito

**Detección de Ambigüedad:**
- [ ] Sistema detecta queries ambiguas con confidence < 0.7
- [ ] Flags de ambigüedad: `missing_bank`, `missing_metric`, `missing_period`, `multiple_interpretations`

**UI/UX:**
- [ ] Componente React `ClarificationDialog` renderiza opciones
- [ ] Máximo 4-5 opciones por campo (no abrumar al usuario)
- [ ] Opciones incluyen descripción breve si disponible
- [ ] Permite input personalizado si `allow_custom: true`

**Backend:**
- [ ] Endpoint `POST /api/chat/clarify` para candidatos
- [ ] Respuesta estructurada con fields + options
- [ ] Reintento automático después de clarificación

**Testing:**
- [ ] 5 queries ambiguas diferentes:
  - "Dame datos del banco" (sin banco ni métrica)
  - "IMOR" (sin banco)
  - "Dame info de INVEX" (sin métrica)
  - "Morosidad" (ambiguo: ¿IMOR o cartera vencida nominal?)
  - "Capital" (ambiguo: ¿ICAP, capital básico, capital complementario?)

---

## HU4: Multi-Métrica

### Resumen
**Como** analista
**Quiero** consultar "IMOR y ICOR de INVEX" en una sola query
**Para** no tener que hacer múltiples preguntas

**Prioridad:** P1 IMPORTANTE
**Story Points:** 5
**Sprint:** 3

### Mapeo Arquitectónico

#### Intent
**`SQL_QUERY` + `VISUALIZATION` (multi-métrica)**

#### Componentes Involucrados

```
Usuario
  ↓ (query multi-métrica: "IMOR y ICOR de INVEX")
Router/Orchestrator
  ↓
QuerySpec Builder (construye QuerySpec con múltiples métricas)
  ↓
Weaviate: Ontology_Terms (valida ambas métricas)
  ↓
SQL Agent (genera SQL con UNION o pivoted query)
  ↓
PostgreSQL (ejecuta SELECT multi-métrica)
  ↓
Chart Builder (detecta escalas diferentes → dual-axis)
  ↓
Usuario (recibe gráfica dual-axis + tabla)
```

#### Flujo Técnico Detallado

**1. Entrada del Usuario:**
```
"Dame IMOR y ICOR de INVEX en 2024"
```

**2. QuerySpec Builder:**

a) **Extrae múltiples métricas:**
```python
metrics_detected = ["IMOR", "ICOR"]
```

b) **Valida cada métrica en Ontología:**
```python
metric_terms = []
for metric_code in metrics_detected:
    term = get_ontology_term(metric_code)
    metric_terms.append({
        "code": metric_code,
        "sql_column": term.sql_column,
        "unit": term.unit,
        "scale": detect_scale(term.unit)  # % vs MXN vs absoluto
    })
```

c) **Construye QuerySpec multi-métrica:**
```json
{
  "intent": "SQL_QUERY",
  "bank": "INVEX",
  "metrics": [
    {
      "code": "IMOR",
      "term_id": "metric_imor",
      "sql_column": "imor",
      "unit": "%",
      "scale_type": "percentage"
    },
    {
      "code": "ICOR",
      "term_id": "metric_icor",
      "sql_column": "icor",
      "unit": "%",
      "scale_type": "percentage"
    }
  ],
  "multi_metric_mode": true,
  "sql": {
    "table": "vw_banking_metrics",
    "columns": ["imor", "icor"],
    "filters": [
      {"field": "bank_name", "op": "=", "value": "INVEX"},
      {"field": "year", "op": "=", "value": 2024}
    ],
    "time_grain": "monthly"
  },
  "visualization": {
    "type": "multi_metric_line",
    "dual_axis": false  // Ambas son %, misma escala
  }
}
```

**3. SQL Agent:**

```sql
SELECT
    date,
    bank_name,
    imor,
    icor
FROM vw_banking_metrics
WHERE bank_name = 'INVEX'
  AND EXTRACT(YEAR FROM date) = 2024
ORDER BY date;
```

**4. Chart Builder:**

a) **Detecta escalas:**
```python
# Ambas métricas son % → misma escala
scales = [metric["unit"] for metric in query_spec["metrics"]]
if len(set(scales)) > 1:
    dual_axis = True  # Escalas diferentes (ej: % vs MXN)
else:
    dual_axis = False  # Misma escala
```

b) **Genera Plotly multi-métrica:**
```json
{
  "data": [
    {
      "x": ["2024-01-01", "2024-02-01", ...],
      "y": [2.1, 2.15, 2.18, ...],
      "name": "IMOR (%)",
      "type": "scatter",
      "mode": "lines+markers",
      "line": {"color": "#1f77b4"}
    },
    {
      "x": ["2024-01-01", "2024-02-01", ...],
      "y": [145.2, 147.8, 150.1, ...],
      "name": "ICOR (%)",
      "type": "scatter",
      "mode": "lines+markers",
      "line": {"color": "#ff7f0e"}
    }
  ],
  "layout": {
    "title": "IMOR e ICOR de INVEX (2024)",
    "xaxis": {"title": "Fecha"},
    "yaxis": {"title": "Porcentaje (%)", "ticksuffix": "%"},
    "legend": {"orientation": "h"}
  }
}
```

**Ejemplo con escalas diferentes (dual-axis):**

Query: "Dame IMOR y Cartera Total de INVEX"
- IMOR: % (escala 0-10%)
- Cartera Total: MXN (escala millones)

```json
{
  "data": [
    {
      "x": ["2024-01-01", ...],
      "y": [2.1, ...],
      "name": "IMOR",
      "yaxis": "y"  // Eje izquierdo
    },
    {
      "x": ["2024-01-01", ...],
      "y": [45000, ...],
      "name": "Cartera Total",
      "yaxis": "y2"  // Eje derecho
    }
  ],
  "layout": {
    "yaxis": {"title": "IMOR (%)", "side": "left"},
    "yaxis2": {
      "title": "Cartera Total (MXN)",
      "overlaying": "y",
      "side": "right"
    }
  }
}
```

**5. Tabla Resumen:**
```json
{
  "summary_table": [
    {
      "date": "2024-12-01",
      "imor": 2.25,
      "icor": 152.3
    },
    ...
  ]
}
```

#### Criterios Técnicos de Éxito

**Parser:**
- [ ] Detecta hasta 3 métricas en una query
- [ ] Extrae métricas con conectores: "y", "e", "además de", ","

**Visualización:**
- [ ] Auto-detecta escalas diferentes
- [ ] Usa dual-axis si scales incompatibles (% vs MXN)
- [ ] Colores distinguibles para cada métrica

**SQL:**
- [ ] Query optimizado (no N queries, sino 1 query pivoted)
- [ ] Performance: <3s incluso con 3 métricas

---

## HU5: RAG con CUB + Anexo 36 + Banxico

### Resumen
**Como** usuario no-experto
**Quiero** preguntar "¿qué es ICOR?"
**Para** entender los términos antes de consultarlos

**Prioridad:** P1 IMPORTANTE
**Story Points:** 5
**Sprint:** 3

### Mapeo Arquitectónico

#### Intent
**`BANK_KNOWLEDGE`** - Consulta de conocimiento/definiciones

#### Componentes Involucrados

```
Usuario
  ↓ (query conceptual: "¿Qué es IMOR?")
Router/Orchestrator (clasifica como BANK_KNOWLEDGE)
  ↓
Knowledge Synthesizer
  ↓
Weaviate: Ontology_Terms (busca término + definición)
  ↓
Knowledge Synthesizer (sintetiza respuesta con fuentes)
  ↓
Usuario (recibe definición + fórmula + fuente)
```

#### Flujo Técnico Detallado

**1. Entrada del Usuario:**
```
"¿Qué es el ICOR?"
```

**2. Router/Orchestrator:**
- Clasifica: `BANK_KNOWLEDGE`
- Detecta patrón conceptual: "qué es", "define", "explica"
- Delega a `Knowledge Synthesizer`

**3. Knowledge Synthesizer:**

a) **Extrae término a buscar:**
```python
term_query = "ICOR"  # Extraído de "¿Qué es el ICOR?"
```

b) **Busca en `Ontology_Terms`:**
```python
# Búsqueda híbrida: exacta + semántica
results = weaviate.query.get(
    "Ontology_Terms",
    ["term_id", "term_name", "code", "definition",
     "formula_text", "variables", "unit", "source_refs"]
).with_hybrid(
    query=term_query,
    alpha=0.5  # 50% keyword, 50% semantic
).with_limit(3).do()

# Resultado:
{
  "term_id": "metric_icor",
  "term_name": "Índice de Cobertura de Cartera Vencida",
  "code": "ICOR",
  "definition": "Porcentaje de reservas preventivas sobre el total de cartera vencida. Mide la capacidad del banco para absorber pérdidas crediticias.",
  "formula_text": "ICOR = (Reservas Preventivas / Cartera Vencida) × 100",
  "variables": ["Reservas Preventivas", "Cartera Vencida"],
  "unit": "%",
  "category": "riesgo",
  "source_refs": [
    "pdf:cub_glosario.pdf#p45",
    "cnbv:anexo_36_seccion_B12",
    "banxico:glosario_financiero#icor"
  ],
  "link_confidence": 0.98
}
```

c) **Sintetiza respuesta estructurada:**
```python
# Usa LLM para generar respuesta natural pero SOLO con datos de la ontología
response = synthesize_knowledge_response(
    term=results[0],
    include_formula=True,
    include_sources=True,
    include_related=True
)
```

**4. Respuesta al Usuario:**
```json
{
  "content": "**ICOR (Índice de Cobertura de Cartera Vencida)**\n\n**Definición:** Porcentaje de reservas preventivas sobre el total de cartera vencida. Mide la capacidad del banco para absorber pérdidas crediticias.\n\n**Fórmula:**\n```\nICOR = (Reservas Preventivas / Cartera Vencida) × 100\n```\n\n**Unidad:** %\n\n**Interpretación:**\n- ICOR > 100%: El banco tiene reservas suficientes para cubrir toda la cartera vencida.\n- ICOR < 100%: El banco tiene reservas insuficientes para cubrir la totalidad de su cartera vencida.\n\n**Fuentes regulatorias:**\n- Catálogo Único de Bancos (CUB), Glosario, p. 45\n- CNBV Anexo 36, Sección B12\n- Banxico, Glosario Financiero: ICOR\n\n**Consultas relacionadas que puedes hacer:**\n- \"Dame el ICOR de INVEX\"\n- \"Compara ICOR de INVEX vs sistema bancario\"\n- \"¿Qué es cartera vencida?\"",

  "term_data": {
    "term_id": "metric_icor",
    "canonical_name": "Índice de Cobertura de Cartera Vencida",
    "code": "ICOR",
    "formula": "ICOR = (Reservas Preventivas / Cartera Vencida) × 100",
    "unit": "%"
  },

  "sources": [
    {
      "type": "CUB",
      "reference": "cub_glosario.pdf#p45",
      "date": "2024-06-15"
    },
    {
      "type": "CNBV",
      "reference": "anexo_36_seccion_B12",
      "url": "https://www.cnbv.gob.mx/..."
    },
    {
      "type": "Banxico",
      "reference": "glosario_financiero#icor",
      "url": "https://www.banxico.org.mx/..."
    }
  ],

  "related_queries": [
    "Dame el ICOR de INVEX",
    "Compara ICOR de INVEX vs sistema bancario",
    "¿Qué es cartera vencida?",
    "¿Qué son las reservas preventivas?"
  ]
}
```

**5. Modo Abstención (si no hay match):**

Query: "¿Qué es el índice de felicidad bancaria?"

```json
{
  "content": "No cuento con información sobre 'índice de felicidad bancaria' en las fuentes regulatorias oficiales (CUB, Anexo 36, Banxico).\n\n**¿Quizás te refieres a alguno de estos términos?**\n- IMOR (Índice de Morosidad)\n- ICOR (Índice de Cobertura)\n- ICAP (Índice de Capitalización)\n- ROE (Return on Equity)\n- ROA (Return on Assets)\n\nPor favor aclara el término o selecciona una opción.",

  "clarification_needed": true,
  "candidates": [
    {"term": "IMOR", "description": "Índice de Morosidad"},
    {"term": "ICOR", "description": "Índice de Cobertura"},
    ...
  ]
}
```

#### Requisitos de Ontología

**Estructura de `Ontology_Terms` para RAG:**

```json
{
  "term_id": "sha256_hash",
  "term_name": "Nombre canónico del término",
  "code": "CÓDIGO_CORTO",
  "definition": "Definición completa y precisa del término según fuentes regulatorias",
  "calculation_logic": "Descripción de cómo se calcula (texto)",
  "formula_text": "Fórmula matemática legible",
  "variables": ["Variable 1", "Variable 2"],
  "synonyms": ["sinónimo 1", "sinónimo 2"],
  "unit": "% | MXN | USD | adimensional",
  "category": "riesgo | capital | liquidez | rentabilidad",
  "source_refs": [
    "pdf:nombre_documento.pdf#pXX",
    "cnbv:anexo_36_seccionXX",
    "banxico:glosario#termino"
  ],
  "link_confidence": 0.0-1.0
}
```

**ETL Ontológico (Días 3-5):**

1. **Parse PDF (CUB + Glosario Banxico):**
```python
# Extraer términos + definiciones + fórmulas
extracted_terms = pdf_parser.extract_glossary_terms(
    pdf_path="data/sources/cub_glosario.pdf",
    extract_formulas=True,
    extract_pages=True
)

# Output:
[
  {
    "term": "Índice de Cobertura",
    "code_detected": "ICOR",
    "definition": "...",
    "formula": "...",
    "page": 45
  },
  ...
]
```

2. **Parse Excel (Columnas DB):**
```python
# Leer esquema de base de datos
db_schema = excel_parser.parse_schema(
    excel_path="data/sources/data_dictionary.xlsx"
)

# Output:
[
  {
    "column_name": "icor",
    "table_name": "vw_banking_metrics",
    "description": "Indice de Cobertura",
    "unit": "%"
  },
  ...
]
```

3. **Linker (Entity Resolution PDF ↔ Excel):**
```python
# Matchear términos PDF con columnas Excel
matches = entity_linker.link(
    pdf_terms=extracted_terms,
    db_schema=db_schema,
    use_embeddings=True,
    use_string_similarity=True
)

# Output:
[
  {
    "pdf_term": "Índice de Cobertura",
    "db_column": "icor",
    "score": 0.95,
    "method": "embedding + string_similarity"
  },
  ...
]
```

4. **Manual Overrides (top 20 términos críticos):**
```yaml
# plugins/bank-advisor-private/config/manual_overrides.yml
overrides:
  - pdf_term: "Indice de Morosidad"
    code: "IMOR"
    sql_column: "imor"
    sql_table: "vw_banking_metrics"
    confidence: 1.0

  - pdf_term: "Indice de Cobertura de Cartera Vencida"
    code: "ICOR"
    sql_column: "icor"
    sql_table: "vw_banking_metrics"
    confidence: 1.0
```

5. **Build & Upsert a Weaviate:**
```python
# Consolidar ontología
ontology_terms = build_ontology_terms(
    pdf_terms=extracted_terms,
    db_schema=db_schema,
    matches=matches,
    manual_overrides=load_yaml("manual_overrides.yml")
)

# Upsert a Weaviate con term_id estable
for term in ontology_terms:
    weaviate.data_object.create(
        data_object=term.to_dict(),
        class_name="Ontology_Terms",
        uuid=term.term_id  # UUID estable (sha256)
    )
```

#### Criterios Técnicos de Éxito

**Ontología:**
- [ ] ≥ 100 términos en `Ontology_Terms`
- [ ] Top 20 términos críticos con `manual_overrides.yml`
- [ ] Cada término tiene: definición + fuente + (formula si aplica)

**Citación de Fuentes:**
- [ ] TODAS las respuestas citan fuente específica (CUB/Anexo36/Banxico)
- [ ] Formato: "Según [fuente], página [XX], fecha [YYYY-MM-DD]"

**Modo Abstención:**
- [ ] Si no hay match con confidence > 0.7: abstención + candidatos
- [ ] NO inventa definiciones

**Testing:**
- [ ] 20 términos comunes:
  - IMOR, ICOR, ICAP, ROA, ROE
  - Cartera Total, Cartera Vencida, Reservas Preventivas
  - Capital Básico, Capital Complementario, Capital Neto
  - Activos Ponderados por Riesgo, Liquidez, Apalancamiento
  - Índice de Liquidez, LCR, NSFR

---

## HU6: ICAP Funcional

### Resumen
**Como** regulador
**Quiero** consultar ICAP de cualquier banco
**Para** validar cumplimiento de capital

**Prioridad:** P2 SHOULD
**Story Points:** 5
**Sprint:** 2

**Estado actual:** ICAP tiene 100% valores en cero. Requiere investigación.

### Mapeo Arquitectónico

#### Intent
**`SQL_QUERY`** (una vez resuelto el problema de datos)

#### Problema Actual

**Root Cause Analysis (Día 1-2 del Sprint 2):**

1. **Verificar fuente de datos:**
```sql
-- Verificar si ICAP existe en la tabla
SELECT
    COUNT(*) as total_rows,
    COUNT(CASE WHEN icap IS NOT NULL AND icap != 0 THEN 1 END) as non_zero_icap,
    MIN(icap) as min_icap,
    MAX(icap) as max_icap,
    AVG(icap) as avg_icap
FROM vw_banking_metrics
WHERE bank_name IN ('INVEX', 'BBVA', 'Santander');

-- Output esperado SI HAY PROBLEMA:
-- total_rows: 720
-- non_zero_icap: 0
-- min/max/avg: 0
```

2. **Verificar ETL:**
```python
# Revisar script de carga
# plugins/bank-advisor-private/src/bankadvisor/data/etl/load_monthly_kpis.py

# ¿Se está cargando la columna ICAP?
# ¿La fuente CNBV tiene valores de ICAP?
# ¿Hay un bug en el mapeo de columnas?
```

3. **Verificar fuente CNBV:**
```bash
# Descargar reportes CNBV más recientes
curl -o icap_202412.xlsx "https://www.cnbv.gob.mx/..."

# Verificar manualmente si hay datos de ICAP
```

#### Posibles Escenarios y Soluciones

**Escenario 1: Bug en ETL (Solucionable)**

**Problema:** Columna mal mapeada en el ETL

**Solución:**
```python
# Fix en load_monthly_kpis.py

# ANTES (bug):
"icap": row["ICAP_INCORRECTO"],  # Columna incorrecta

# DESPUÉS (fix):
"icap": row["R12A_ICAP"],  # Columna correcta de CNBV
```

**Tiempo estimado:** 2-4 horas
**Action:** Fix ETL → Re-run ETL → Validate → Deploy

---

**Escenario 2: Fuente CNBV no tiene ICAP (Temporal)**

**Problema:** CNBV dejó de publicar ICAP temporalmente

**Solución:**
- Documentar limitación
- Comunicar a stakeholders
- Agregar mensaje en UI: "ICAP no disponible temporalmente por fuente de datos"

**Tiempo estimado:** 2 horas (documentación)
**Action:** Documentar + Comunicar → Postponer hasta que CNBV publique

---

**Escenario 3: ICAP requiere cálculo (Complejo)**

**Problema:** ICAP no viene en la fuente, hay que calcularlo

**Fórmula ICAP:**
```
ICAP = (Capital Neto / Activos Ponderados por Riesgo) × 100
```

**Solución:**
```python
# Agregar cálculo en ETL
def calculate_icap(row):
    capital_neto = row["CAPITAL_NETO"]
    activos_riesgo = row["ACTIVOS_PONDERADOS_RIESGO"]

    if activos_riesgo and activos_riesgo > 0:
        icap = (capital_neto / activos_riesgo) * 100
        return icap
    else:
        return None

# Aplicar en ETL
df["icap"] = df.apply(calculate_icap, axis=1)
```

**Tiempo estimado:** 1-2 días (validar fórmula + testing)
**Action:** Implement calculation → Validate vs CNBV benchmark → Deploy

---

#### Decision Tree

```
ICAP tiene valores en 0
  ↓
RCA: ¿Por qué?
  ↓
  ├─→ Bug ETL (columna incorrecta)
  │     ↓
  │   FIX: Corregir mapeo → Re-run ETL (4h)
  │
  ├─→ Fuente CNBV no publica ICAP
  │     ↓
  │   DOCUMENT: Limitación conocida → OUT v1.2
  │
  └─→ ICAP requiere cálculo
        ↓
      CALCULATE: Implementar fórmula → Validate (1-2 días)
```

#### Criterios Técnicos de Éxito

**Root Cause Analysis (Obligatorio):**
- [ ] RCA documentado con evidencia (queries SQL, screenshots)
- [ ] Decisión tomada: Fix vs Document vs Calculate

**Si es Fix:**
- [ ] ETL corregido y re-ejecutado
- [ ] Valores de ICAP != 0 para al menos 50% de bancos/meses
- [ ] Validación: ICAP values match CNBV benchmark (±0.1%)

**Si es Document:**
- [ ] Limitación documentada en `docs/known_limitations.md`
- [ ] Comunicado a stakeholders (Carlos, Fernando)
- [ ] UI muestra mensaje: "ICAP temporalmente no disponible"

**Si es Calculate:**
- [ ] Fórmula implementada y validada vs CNBV
- [ ] Tests unitarios para cálculo
- [ ] Validación: valores calculados vs CNBV benchmark (±0.1%)

**Timeline:**
- [ ] RCA completado: Día 1-2 de Sprint 2
- [ ] Fix/Document/Calculate: Día 3-5 de Sprint 2

---

## HU7: Sistema de Feedback de Usuario

### Resumen
**Como** usuario del sistema
**Quiero** poder indicar si una respuesta es correcta o incorrecta
**Para** ayudar a mejorar el sistema continuamente

**Prioridad:** P1 IMPORTANTE
**Story Points:** 3
**Sprint:** 4

### Mapeo Arquitectónico

#### Intent
**N/A** (Sistema transversal, aplica a todas las respuestas)

#### Componentes Involucrados

```
Usuario
  ↓ (ve respuesta del chat)
Frontend: MessageFeedback Component
  ↓ (click pulgar arriba/abajo)
POST /api/feedback
  ↓
Backend: Feedback Service
  ↓
MongoDB: feedback_collection
  ↓
(Opcional) Dashboard Interno: Feedback Analytics
```

#### Flujo Técnico Detallado

**1. Frontend - MessageFeedback Component:**

```tsx
// apps/web/src/components/chat/MessageFeedback.tsx

interface MessageFeedbackProps {
  messageId: string;
  onFeedbackSubmit?: (feedback: Feedback) => void;
}

export function MessageFeedback({
  messageId,
  onFeedbackSubmit
}: MessageFeedbackProps) {
  const [rating, setRating] = useState<'positive' | 'negative' | null>(null);
  const [comment, setComment] = useState('');
  const [showCommentBox, setShowCommentBox] = useState(false);

  const handleThumbClick = (newRating: 'positive' | 'negative') => {
    setRating(newRating);

    if (newRating === 'negative') {
      setShowCommentBox(true);  // Pedir comentario en feedback negativo
    } else {
      submitFeedback(newRating, '');
    }
  };

  const submitFeedback = async (rating: 'positive' | 'negative', comment: string) => {
    const feedback = {
      message_id: messageId,
      rating,
      comment,
      timestamp: new Date().toISOString()
    };

    try {
      await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(feedback)
      });

      onFeedbackSubmit?.(feedback);

      // Mostrar confirmación al usuario
      toast.success('¡Gracias por tu feedback!');
    } catch (error) {
      toast.error('Error al enviar feedback');
    }
  };

  return (
    <div className="message-feedback">
      <div className="feedback-buttons">
        <button
          onClick={() => handleThumbClick('positive')}
          className={rating === 'positive' ? 'active' : ''}
          aria-label="Respuesta correcta"
        >
          <ThumbsUpIcon />
        </button>

        <button
          onClick={() => handleThumbClick('negative')}
          className={rating === 'negative' ? 'active' : ''}
          aria-label="Respuesta incorrecta"
        >
          <ThumbsDownIcon />
        </button>
      </div>

      {showCommentBox && (
        <div className="feedback-comment">
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="¿Qué estuvo mal? (opcional)"
            rows={3}
          />
          <button onClick={() => submitFeedback('negative', comment)}>
            Enviar
          </button>
        </div>
      )}
    </div>
  );
}
```

**2. Backend - Feedback Endpoint:**

```python
# apps/backend/src/routers/feedback.py

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

class FeedbackCreate(BaseModel):
    message_id: str
    rating: str  # 'positive' | 'negative'
    comment: Optional[str] = None

class FeedbackResponse(BaseModel):
    id: str
    message_id: str
    rating: str
    comment: Optional[str]
    timestamp: datetime
    user_id: str
    message_content: str
    response_content: str

@router.post("/", response_model=dict)
async def create_feedback(
    feedback: FeedbackCreate,
    current_user=Depends(get_current_user)
):
    """
    Almacena feedback del usuario sobre una respuesta del chat.
    """
    # Obtener el mensaje original y la respuesta
    message = await Message.get(feedback.message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Crear documento de feedback
    feedback_doc = Feedback(
        message_id=feedback.message_id,
        user_id=current_user.id,
        rating=feedback.rating,
        comment=feedback.comment,
        timestamp=datetime.utcnow(),

        # Capturar contexto completo
        message_content=message.content,
        response_content=message.response.content,
        query_spec=message.response.query_spec,  # QuerySpec que generó la respuesta
        sql_executed=message.response.sql_executed,  # SQL ejecutado
        intent=message.response.intent,  # Intent clasificado

        # Metadata
        session_id=message.chat_id,
        model_used=message.response.model,
        execution_time_ms=message.response.execution_time_ms
    )

    await feedback_doc.insert()

    # Log para analytics
    logger.info(
        "feedback.created",
        feedback_id=str(feedback_doc.id),
        rating=feedback.rating,
        intent=message.response.intent
    )

    return {
        "id": str(feedback_doc.id),
        "status": "created",
        "message": "Feedback received successfully"
    }
```

**3. MongoDB Schema - Feedback Collection:**

```python
# apps/backend/src/models/feedback.py

from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional, Dict, Any

class Feedback(Document):
    """
    Almacena feedback del usuario sobre respuestas del chat.
    """
    # Identificadores
    message_id: str  # ID del mensaje que recibió feedback
    user_id: str
    session_id: str  # ID del chat

    # Feedback
    rating: str  # 'positive' | 'negative'
    comment: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Contexto completo (para análisis)
    message_content: str  # Query original del usuario
    response_content: str  # Respuesta generada por el sistema

    # Contexto técnico
    intent: Optional[str] = None  # BANK_KNOWLEDGE | SQL_QUERY | VISUALIZATION
    query_spec: Optional[Dict[str, Any]] = None  # QuerySpec si aplica
    sql_executed: Optional[str] = None  # SQL ejecutado si aplica
    model_used: Optional[str] = None  # Modelo LLM usado
    execution_time_ms: Optional[int] = None

    # Metadata
    user_agent: Optional[str] = None

    class Settings:
        name = "feedback"
        indexes = [
            "message_id",
            "user_id",
            "rating",
            "timestamp",
            "intent"
        ]
```

**4. Dashboard Interno - Feedback Analytics (Opcional v1.3):**

```python
# apps/backend/src/routers/admin/feedback_analytics.py

@router.get("/admin/feedback/analytics")
async def get_feedback_analytics(
    current_user=Depends(require_admin),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """
    Dashboard de analytics de feedback para equipo interno.
    """
    pipeline = [
        {
            "$match": {
                "timestamp": {
                    "$gte": start_date or datetime(2024, 1, 1),
                    "$lte": end_date or datetime.utcnow()
                }
            }
        },
        {
            "$group": {
                "_id": {
                    "rating": "$rating",
                    "intent": "$intent"
                },
                "count": {"$sum": 1},
                "avg_execution_time": {"$avg": "$execution_time_ms"}
            }
        }
    ]

    results = await Feedback.aggregate(pipeline).to_list()

    return {
        "total_feedback": await Feedback.count(),
        "positive_rate": calculate_positive_rate(results),
        "negative_rate": calculate_negative_rate(results),
        "by_intent": group_by_intent(results),
        "common_issues": await get_common_issues()  # NLP clustering de comments
    }

async def get_common_issues():
    """
    Clustering de comentarios negativos para identificar patrones.
    """
    negative_feedback = await Feedback.find(
        Feedback.rating == "negative",
        Feedback.comment != None
    ).to_list()

    comments = [f.comment for f in negative_feedback]

    # Clustering simple con keywords
    issues = {
        "datos_incorrectos": [],
        "query_no_entendido": [],
        "latencia_alta": [],
        "grafica_incorrecta": [],
        "otros": []
    }

    for comment in comments:
        comment_lower = comment.lower()
        if any(kw in comment_lower for kw in ["dato", "incorrecto", "equivocado"]):
            issues["datos_incorrectos"].append(comment)
        elif any(kw in comment_lower for kw in ["no entendió", "malinterpretó"]):
            issues["query_no_entendido"].append(comment)
        elif any(kw in comment_lower for kw in ["lento", "demora", "espera"]):
            issues["latencia_alta"].append(comment)
        elif any(kw in comment_lower for kw in ["gráfica", "visualización"]):
            issues["grafica_incorrecta"].append(comment)
        else:
            issues["otros"].append(comment)

    return {
        category: {
            "count": len(comments_list),
            "examples": comments_list[:5]  # Top 5 ejemplos
        }
        for category, comments_list in issues.items()
    }
```

#### Criterios Técnicos de Éxito

**Frontend:**
- [ ] Botones de feedback visibles en cada mensaje del assistant
- [ ] Pulgar arriba: submit inmediato
- [ ] Pulgar abajo: mostrar textarea opcional para comentario
- [ ] Visual feedback al usuario: toast "¡Gracias por tu feedback!"
- [ ] Estado persistente: botón seleccionado queda marcado

**Backend:**
- [ ] Endpoint `POST /api/feedback` funcionando
- [ ] Validación: message_id existe, rating es válido
- [ ] Captura contexto completo: query, response, QuerySpec, SQL, intent

**Base de Datos:**
- [ ] Feedback almacenado en MongoDB con timestamps
- [ ] Índices en: message_id, user_id, rating, timestamp, intent
- [ ] Retención: feedback se mantiene indefinidamente (para ML futuro)

**Testing:**
- [ ] Test unitario: create feedback con rating='positive'
- [ ] Test unitario: create feedback con rating='negative' + comment
- [ ] Test E2E: flujo completo usuario → feedback → BD
- [ ] Test: invalid message_id retorna 404

**Analytics (Opcional v1.3):**
- [ ] Dashboard admin `/admin/feedback/analytics`
- [ ] Métricas: positive_rate, negative_rate, by_intent
- [ ] Clustering de comentarios negativos por categorías

---

## Resumen General

### Arquitectura Multi-Agente v1.2

**Componentes:**
1. **Router/Orchestrator** - Clasifica intents
2. **Knowledge Synthesizer** - Responde BANK_KNOWLEDGE
3. **QuerySpec Builder** - Construye QuerySpec para SQL_QUERY
4. **SQL Agent** - Ejecuta SQL de forma segura
5. **Chart Builder** - Genera visualizaciones

**Datos:**
- **Ontology_Terms** (Weaviate) - Entidades estructuradas con mapeo SQL
- **PostgreSQL** - Métricas bancarias (vw_banking_metrics)
- **Query_Examples** (Weaviate) - Few-shot examples

**Intents:**
- **BANK_KNOWLEDGE** → Knowledge Synthesizer
- **SQL_QUERY** → QuerySpec Builder → SQL Agent
- **VISUALIZATION** → Chart Builder
- **DRIVER_ANALYSIS** → OUT v1.2 (v1.3+)

### Mapeo HU → Arquitectura

| HU | Intent | Componentes Clave | Prioridad | Sprint |
|----|--------|-------------------|-----------|--------|
| HU1: Query Multi-Banco | SQL_QUERY | QuerySpec Builder, SQL Agent | P0 | 1-2 |
| HU2: Comparación Multi-Banco | SQL_QUERY + VIZ | QuerySpec Builder, SQL Agent, Chart Builder | P0 | 2-3 |
| HU3: UI Clarificación | ABSTENTION | QuerySpec Builder, Frontend ClarificationDialog | P1 | 2 |
| HU4: Multi-Métrica | SQL_QUERY + VIZ | QuerySpec Builder, SQL Agent, Chart Builder (dual-axis) | P1 | 3 |
| HU5: RAG CUB/Anexo36/Banxico | BANK_KNOWLEDGE | Knowledge Synthesizer, Ontology_Terms | P1 | 3 |
| HU6: ICAP Funcional | SQL_QUERY (post-fix) | SQL Agent, ETL (requiere RCA) | P2 | 2 |
| HU7: Feedback Sistema | N/A (transversal) | Frontend MessageFeedback, Backend Feedback Service | P1 | 4 |

### Timeline de Implementación

**Sprint 1 (27-29 Dic):** HU1 Query Multi-Banco
**Sprint 2 (30 Dic - 2 Ene):** HU6 ICAP (RCA), HU3 Clarificación
**Sprint 3 (3-6 Ene):** HU2 Comparación, HU4 Multi-Métrica, HU5 RAG
**Sprint 4 (7-10 Ene):** HU7 Feedback, Testing E2E, Deploy

---

**Última actualización:** 26 Diciembre 2025
**Próxima revisión:** Después del PoC QuerySpec (Día 6)
