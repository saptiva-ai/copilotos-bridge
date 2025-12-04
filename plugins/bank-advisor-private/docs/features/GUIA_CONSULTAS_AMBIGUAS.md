# Guia de Consultas Ambiguas - NL2SQL BankAdvisor

## Objetivo

Esta guia documenta los **tipos de ambigüedad** que el sistema NL2SQL debe detectar y solicitar clarificación al usuario, en lugar de asumir valores por defecto.

## Taxonomia de Ambigüedades

### 1. Ambigüedad de Métrica (Tipo de Dato)

Cuando el usuario no especifica claramente qué indicador quiere.

| Consulta Ambigua | Por qué es Ambigua | Opciones de Clarificación |
|-----------------|-------------------|--------------------------|
| `"cartera"` | ¿Cartera Total? ¿Comercial? ¿Consumo? ¿Vivienda? ¿Vencida? | "¿A qué tipo de cartera te refieres?" |
| `"datos del banco"` | No especifica ninguna métrica | "¿Qué información necesitas?" |
| `"información financiera"` | Demasiado genérico | "¿Qué indicador específico?" |
| `"estado actual"` | Sin métrica definida | "¿Sobre qué métrica?" |
| `"métricas de riesgo"` | ¿IMOR? ¿ICOR? ¿PE? ¿TDA? | "¿Qué indicador de riesgo?" |

**Ejemplo de Interacción Esperada:**
```
Usuario: "cartera de INVEX"
OctaviOS: "Hay varios tipos de cartera disponibles:
          1. Cartera Total
          2. Cartera Comercial
          3. Cartera de Consumo
          4. Cartera de Vivienda
          5. Cartera Vencida
          ¿Cuál te interesa?"
```

---

### 2. Ambigüedad de Banco/Entidad

Cuando no se especifica el banco o se menciona uno no disponible.

| Consulta Ambigua | Por qué es Ambigua | Opciones de Clarificación |
|-----------------|-------------------|--------------------------|
| `"IMOR actual"` | ¿De qué banco? ¿INVEX? ¿Sistema? | "¿De qué entidad?" |
| `"morosidad últimos meses"` | Falta el banco | "¿INVEX o Sistema Bancario?" |
| `"reservas 2024"` | No especifica entidad | "¿Qué banco quieres consultar?" |

**Bancos NO disponibles en el dataset:**
- Banorte, BBVA, Santander, Banamex, HSBC, Scotiabank, etc.

**Ejemplo de Interacción Esperada:**
```
Usuario: "IMOR de Banorte"
OctaviOS: "Lo siento, actualmente solo tengo datos de:
          - INVEX
          - Sistema Bancario (promedio)
          ¿Te gustaría ver alguno de estos?"
```

---

### 3. Ambigüedad Temporal

Cuando el período no está claro o es interpretable de múltiples formas.

| Consulta Ambigua | Por qué es Ambigua | Opciones de Clarificación |
|-----------------|-------------------|--------------------------|
| `"IMOR de INVEX reciente"` | ¿Cuántos meses es "reciente"? | "¿Últimos 1, 3, 6 o 12 meses?" |
| `"evolución de cartera"` | ¿Todo el histórico? ¿Este año? | "¿Qué período te interesa?" |
| `"ICOR del año pasado"` | ¿2023 o 2024? (depende de fecha actual) | "¿Te refieres a 2023 o 2024?" |
| `"tendencia histórica"` | ¿Desde cuándo? | "¿Desde qué año quieres ver?" |

**Ejemplo de Interacción Esperada:**
```
Usuario: "cómo ha evolucionado el IMOR"
OctaviOS: "Para mostrarte la evolución del IMOR, necesito saber el período:
          1. Últimos 3 meses
          2. Últimos 6 meses
          3. Último año (12 meses)
          4. Histórico completo (desde 2017)"
```

---

### 4. Ambigüedad de Intención/Visualización

Cuando no está claro qué tipo de análisis o visualización quiere el usuario.

| Consulta Ambigua | Por qué es Ambigua | Opciones de Clarificación |
|-----------------|-------------------|--------------------------|
| `"IMOR de INVEX"` | ¿Solo valor? ¿Evolución? ¿Comparación? | "¿Qué te gustaría ver?" |
| `"reservas de INVEX 2024"` | ¿Valor puntual? ¿Tendencia? | "¿Valor actual o evolución?" |
| `"datos de cartera comercial"` | ¿Tabla? ¿Gráfica? ¿Resumen? | "¿Cómo quieres visualizarlo?" |

**Ejemplo de Interacción Esperada (el del ticket):**
```
Usuario: "¿Cómo está el IMOR de Banorte en los últimos 3 meses?"
OctaviOS: "Entiendo que necesitas el Índice de Morosidad.
          (Nota: Banorte no está disponible, mostrando INVEX)
          ¿Te interesa ver:
          1. Solo el valor actual (2.90%)
          2. La evolución mes a mes
          3. Comparación con el Sistema Bancario?"
Usuario: "La evolución"
[Sistema genera gráfica de línea temporal]
```

---

### 5. Ambigüedad de Comparación

Cuando se pide comparar pero no está claro qué o contra qué.

| Consulta Ambigua | Por qué es Ambigua | Opciones de Clarificación |
|-----------------|-------------------|--------------------------|
| `"comparar IMOR"` | ¿Qué bancos? ¿Qué períodos? | "¿Qué quieres comparar?" |
| `"INVEX vs competencia"` | ¿Qué es "competencia"? | "¿Contra qué entidad?" |
| `"mejor que el promedio"` | ¿En qué métrica? ¿Qué período? | "¿Qué indicador y período?" |

**Ejemplo de Interacción Esperada:**
```
Usuario: "compara el IMOR"
OctaviOS: "Para hacer una comparación, necesito saber:
          - ¿INVEX vs Sistema Bancario?
          - ¿Comparar diferentes períodos de tiempo?
          - ¿Comparar con otro indicador (ej: ICOR)?"
```

---

### 6. Ambigüedad Multi-Métrica

Cuando el usuario pide varias cosas a la vez.

| Consulta Ambigua | Por qué es Ambigua | Opciones de Clarificación |
|-----------------|-------------------|--------------------------|
| `"IMOR y ICOR de INVEX"` | ¿Juntos? ¿Separados? | "¿Una gráfica combinada o separadas?" |
| `"todas las métricas"` | Demasiado amplio | "¿Cuáles específicamente?" |
| `"resumen financiero"` | ¿Qué incluye? | "¿Qué indicadores incluyo?" |

---

## Catálogo de Consultas de Prueba

### Archivo: `tests/data/ambiguous_queries_test.json`

```json
{
  "clarification_tests": [
    {
      "id": "AMB-MET-001",
      "query": "cartera de INVEX",
      "ambiguity_type": "metric",
      "expected_clarification": {
        "question": "¿A qué tipo de cartera te refieres?",
        "options": ["Cartera Total", "Cartera Comercial", "Cartera de Consumo", "Cartera de Vivienda", "Cartera Vencida"]
      }
    },
    {
      "id": "AMB-MET-002",
      "query": "indicadores de riesgo 2024",
      "ambiguity_type": "metric",
      "expected_clarification": {
        "question": "¿Qué indicador de riesgo te interesa?",
        "options": ["IMOR (Morosidad)", "ICOR (Cobertura)", "Pérdida Esperada", "TDA (Deterioro)"]
      }
    },
    {
      "id": "AMB-BANK-001",
      "query": "IMOR actual",
      "ambiguity_type": "bank",
      "expected_clarification": {
        "question": "¿De qué entidad?",
        "options": ["INVEX", "Sistema Bancario"]
      }
    },
    {
      "id": "AMB-BANK-002",
      "query": "IMOR de Banorte",
      "ambiguity_type": "unsupported_bank",
      "expected_clarification": {
        "message": "Banorte no está disponible. ¿Te gustaría ver INVEX o Sistema?",
        "options": ["INVEX", "Sistema Bancario"]
      }
    },
    {
      "id": "AMB-TIME-001",
      "query": "evolución del IMOR de INVEX",
      "ambiguity_type": "time_range",
      "expected_clarification": {
        "question": "¿Qué período de tiempo?",
        "options": ["Últimos 3 meses", "Últimos 6 meses", "Último año", "Histórico completo"]
      }
    },
    {
      "id": "AMB-TIME-002",
      "query": "IMOR reciente",
      "ambiguity_type": "time_range",
      "expected_clarification": {
        "question": "¿Cuántos meses consideras 'reciente'?",
        "options": ["Último mes", "Últimos 3 meses", "Últimos 6 meses"]
      }
    },
    {
      "id": "AMB-INT-001",
      "query": "IMOR de INVEX últimos 3 meses",
      "ambiguity_type": "intent",
      "expected_clarification": {
        "question": "¿Qué te gustaría ver?",
        "options": ["Solo el valor actual", "Evolución mes a mes", "Comparación con Sistema"]
      }
    },
    {
      "id": "AMB-INT-002",
      "query": "cartera comercial de INVEX 2024",
      "ambiguity_type": "visualization",
      "expected_clarification": {
        "question": "¿Cómo quieres visualizar los datos?",
        "options": ["Valor actual con variación", "Gráfica de evolución", "Tabla mensual"]
      }
    },
    {
      "id": "AMB-CMP-001",
      "query": "compara el IMOR",
      "ambiguity_type": "comparison",
      "expected_clarification": {
        "question": "¿Qué quieres comparar?",
        "options": ["INVEX vs Sistema", "Diferentes períodos", "Contra otro indicador"]
      }
    },
    {
      "id": "AMB-MULTI-001",
      "query": "IMOR y ICOR de INVEX",
      "ambiguity_type": "multi_metric",
      "expected_clarification": {
        "question": "¿Cómo quieres ver las métricas?",
        "options": ["Gráfica combinada", "Gráficas separadas", "Tabla resumen"]
      }
    }
  ]
}
```

---

## Cómo Ejecutar las Pruebas

### Opción 1: Pruebas Unitarias con Pytest

```bash
# Ir al directorio del plugin
cd plugins/bank-advisor-private

# Activar entorno virtual
source .venv/bin/activate

# Ejecutar todas las pruebas de ambigüedad
pytest -m nl2sql_dirty -k "ambiguous" -v

# Ejecutar pruebas específicas de clarificación
pytest src/bankadvisor/tests/integration/test_nl2sql_dirty_data.py -k "MF-" -v
```

### Opción 2: Prueba Manual con el Script Standalone

```bash
# Ejecutar el runner de pruebas hostiles (incluye ambiguas)
python src/bankadvisor/tests/integration/test_nl2sql_dirty_data.py
```

### Opción 3: Usando el Shell Script

```bash
# Ejecutar contra servidor local
./scripts/run_nl2sql_dirty_tests.sh --local --verbose

# Solo pruebas de consultas incompletas (MF = Missing Fields)
pytest -m nl2sql_dirty -k "MF-" -v
```

### Opción 4: Prueba Interactiva con cURL

```bash
# Prueba directa contra el endpoint JSON-RPC
curl -X POST http://localhost:8000/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-1",
    "method": "bank_advisor.query",
    "params": {
      "query": "cartera de INVEX"
    }
  }' | jq
```

---

## Matriz de Pruebas por Tipo de Ambigüedad

| ID | Categoría | Query | Espera Clarificación | En hostile_queries.json |
|---|----------|-------|---------------------|------------------------|
| MF-001 | Métrica | "datos del banco" | Si - falta métrica | ✅ |
| MF-002 | Completo | "ultimo mes" | Si - falta todo | ✅ |
| MF-004 | Métrica | "INVEX 2024" | Si - falta métrica | ✅ |
| MF-005 | Banco/Tiempo | "morosidad" | Parcial - usa defaults | ✅ |
| IB-001 | Banco | "BancoFantasma" | Si - banco no existe | ✅ |
| IB-004 | Banco | "Bank of America" | Si - no disponible | ✅ |
| MM-003 | Multi | "todas las metricas" | Si - muy amplio | ✅ |
| MM-005 | Multi | "resumen financiero" | Si - ambiguo | ✅ |
| NS-002 | Irrelevante | "clima en Cancun" | Si - fuera de dominio | ✅ |
| NS-006 | Social | "hola buenos dias" | Si - no es consulta | ✅ |

---

## Criterios de Éxito para Clarificación

El sistema debe:

1. **Detectar** que la consulta es ambigua (confidence_score < 0.7)
2. **Identificar** qué dimensión falta (metric, bank, time_range, intent)
3. **Proporcionar opciones** concretas al usuario (máximo 4-5)
4. **Mantener contexto** para la respuesta del usuario
5. **NO asumir** valores por defecto sin avisar

---

## Flujo de Clarificación Propuesto

```
                    ┌─────────────────┐
                    │  Usuario envía  │
                    │    consulta     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  QuerySpecParser│
                    │   .parse()      │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼────┐  ┌──────▼──────┐  ┌───▼────────┐
     │ Completa    │  │  Parcial    │  │  Ambigua   │
     │ conf > 0.9  │  │ 0.7 < conf  │  │ conf < 0.7 │
     │             │  │   < 0.9     │  │            │
     └──────┬──────┘  └──────┬──────┘  └──────┬─────┘
            │                │                │
     ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼─────┐
     │ Ejecutar SQL│  │ Ejecutar +  │  │ Solicitar  │
     │ + Gráfica   │  │  Advertir   │  │Clarificación│
     └─────────────┘  └─────────────┘  └────────────┘
```

---

## Próximos Pasos para tu Colega

1. **Implementar detección** de `requires_clarification` en el pipeline
2. **Agregar campo** `clarification_options` en la respuesta JSON-RPC
3. **Crear endpoint** `/rpc/clarify` para recibir respuesta del usuario
4. **Integrar en frontend** el componente de opciones de clarificación
5. **Pruebas E2E** con el flujo completo de clarificación

---

## Referencias

- `hostile_queries.json`: Catálogo de 53 consultas hostiles/ambiguas
- `test_nl2sql_dirty_data.py`: Test harness automatizado
- `QuerySpecParser`: Parser principal en `services/query_spec_parser.py`
- `IntentService`: Servicio de resolución en `services/intent_service.py`
