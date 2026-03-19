# Arquitectura: Sistema Multi-Agente

> **Cuándo leer**: Para entender los agentes, sus responsabilidades y contratos.

## Catálogo de Intents

| Intent | Agente Responsable | Uso | Status |
|--------|-------------------|-----|--------|
| `BANK_KNOWLEDGE` | Knowledge Synthesizer | Definiciones, glosario, fórmulas | ✅ v1.2 |
| `SQL_QUERY` | QuerySpec Builder + SQL Agent | Consulta de datos reales | ✅ v1.2 |
| `VISUALIZATION` | Chart Builder | Gráficas, tablas, export | ✅ v1.2 |
| `DRIVER_ANALYSIS` | - | Análisis de factores | ❌ v1.3+ |

---

## Diagrama de Flujo

```
Usuario: "Dame el IMOR de INVEX"
            │
            ▼
┌───────────────────────┐
│   Router/Orchestrator │
│   ┌─────────────────┐ │
│   │ Clasifica intent│ │
│   │ → SQL_QUERY     │ │
│   └─────────────────┘ │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│   QuerySpec Builder   │
│   ┌─────────────────┐ │
│   │ Consulta        │ │
│   │ Ontology_Terms  │◄──── Weaviate
│   │ → Construye     │ │
│   │   QuerySpec     │ │
│   └─────────────────┘ │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│      SQL Agent        │
│   ┌─────────────────┐ │
│   │ Valida QuerySpec│ │
│   │ Genera SQL      │ │
│   │ Ejecuta         │◄──── PostgreSQL
│   └─────────────────┘ │
└───────────┬───────────┘
            │
            ▼
      Respuesta con:
      - Datos
      - Trazabilidad
      - source_refs
```

---

## Contratos por Agente

### Router / Orchestrator

| Campo | Valor |
|-------|-------|
| **Responsabilidad** | Decidir intent + coordinar agentes |
| **Input** | Query en lenguaje natural |
| **Output** | Intent clasificado |
| **NO hace** | Generar SQL final |

---

### Knowledge Synthesizer

| Campo | Valor |
|-------|-------|
| **Responsabilidad** | Responder usando Ontology_Terms |
| **Input** | Query clasificada como KNOWLEDGE |
| **Output** | Definición + fórmula + source_refs |

**Contrato**:
- Siempre cita término canónico + fórmula si existe
- Si no hay match: pide clarificación o top-k candidatos
- **NUNCA** inventa definiciones

---

### QuerySpec Builder

| Campo | Valor |
|-------|-------|
| **Responsabilidad** | Producir QuerySpec conforme a JSON Schema |
| **Input** | Query clasificada como SQL_QUERY |
| **Output** | QuerySpec válido + confidence score |

**Contrato**:
- Usa **únicamente** entidades de Ontology_Terms
- Si score bajo (`confidence < 0.7`): abstención
- Retorna `ambiguity_flags` si hay incertidumbre

---

### SQL Agent

| Campo | Valor |
|-------|-------|
| **Responsabilidad** | Recibir QuerySpec → generar SQL → ejecutar |
| **Input** | QuerySpec validado |
| **Output** | Resultados de query |

**Contrato**:
- **Nunca ejecuta** si el validator falla
- Solo `SELECT` (whitelist estricta)
- Budget: max 5000 rows, 30s timeout, 2 joins

---

### Chart Builder

| Campo | Valor |
|-------|-------|
| **Responsabilidad** | Generar visualizaciones |
| **Input** | QuerySpec + SQL results |
| **Output** | JSON de configuración Plotly |

**Contrato**:
- Tipos soportados: line, bar, table
- Incluye título, ejes, leyenda
- Exportable a PNG/CSV

---

## Flujo de Errores

```
┌─────────────────────────────────────────────────────────┐
│                    Punto de Fallo                        │
├────────────────────┬────────────────────────────────────┤
│ Router no entiende │ → Pedir clarificación al usuario   │
│ Ontology sin match │ → Ofrecer top-k candidatos         │
│ QuerySpec inválido │ → Reparación automática o abstención│
│ SQL falla          │ → Error con mensaje seguro         │
│ Timeout            │ → Respuesta parcial + indicador    │
└────────────────────┴────────────────────────────────────┘
```

---

## Ejemplo Completo

**Input**: "Compara IMOR de INVEX vs BBVA en 2024"

**Router**: Clasifica → `SQL_QUERY` + `VISUALIZATION`

**QuerySpec Builder** consulta Ontology_Terms:
```json
{
  "intent": "SQL_QUERY",
  "metrics": ["IMOR"],
  "banks": ["INVEX", "BBVA"],
  "time_range": {"year": 2024},
  "confidence": 0.91
}
```

**SQL Agent** genera:
```sql
SELECT bank, month, imor
FROM monthly_kpis
WHERE bank IN ('INVEX', 'BBVA')
  AND year = 2024
```

**Chart Builder** produce gráfica comparativa.

---

**Versión**: 1.2.1 | **Fuente**: `docs/tex/Arquitectura.tex` secciones 3, 7
