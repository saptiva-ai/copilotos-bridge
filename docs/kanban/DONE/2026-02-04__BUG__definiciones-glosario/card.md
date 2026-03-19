---
status: DONE
---
# BUG: Definiciones y Glosario - Sistema No Responde Preguntas Conceptuales

**Prioridad:** P2 - Medium
**Fecha:** 2026-02-04
**Reportado por:** Usuario via Dashboard Feedback
**Status:** BACKLOG

---

## Resumen

El sistema NO puede responder preguntas conceptuales como "¿qué es la cartera comercial?". Cuando el usuario pregunta por definiciones o explicaciones de términos bancarios, el sistema no proporciona la información solicitada.

**Impacto:** 2 feedback negativos - usuarios no obtienen explicaciones de conceptos

---

## Casos Reportados

### Caso 1: Definición de Cartera Comercial
**Fecha:** 2026-02-03 13:14
**Message ID:** 61ef795d-bb8f-4ef4-9e0c-215d8e185b46
**Query:** `que es la cartera comercial de un banco ?`
**Feedback:** "no me dio la explicación de cartera comercial"

**Contexto del Error:**
- El usuario esperaba una definición/explicación del concepto
- El sistema probablemente intentó buscar datos en lugar de explicar

### Caso 2: Explicación Detallada
**Fecha:** 2026-02-03 13:47
**Message ID:** 7abc4031-78a2-41b4-9646-72f44a340412
**Query:** `explícame a detalle que es la cartera comercial de un banco, como se obtiene y dame un ejemplo que cualquier persona pudiera entender`
**Feedback:** "cambio el tipo de letra repentinamente y no respeto el área de la conversación" (+ no dio explicación)

---

## Análisis Técnico

### Causa Raíz

1. **No existe handler para queries de definición** - El sistema solo tiene handlers para datos numéricos (KPIs, métricas)
2. **Falta integración con glosario** - Existe `data/knowledge/` con términos pero no se consulta
3. **Intent detection** no reconoce "qué es", "explícame", "define" como intent de definición

### Queries que Deberían Funcionar

```
- "¿Qué es el ICAP?"
- "¿Qué es la cartera comercial?"
- "Explícame qué es el IMOR"
- "Define cartera vencida"
- "¿Cómo se calcula el ROE?"
```

### Archivos Involucrados

- `plugins/bank-advisor-private/src/bankadvisor/tools/` (falta definition_tools.py)
- `plugins/bank-advisor-private/data/knowledge/` (términos existentes)
- `plugins/bank-advisor-private/config/glossary.yaml` (si existe)

---

## Solución Propuesta

### 1. Crear MCP Tool `get_definition`

```python
@server.tool()
async def get_definition(term: str) -> dict:
    """Obtiene la definición de un término bancario/financiero."""
    # Buscar en glosario local
    glossary = load_glossary()

    # Fuzzy match del término
    matches = fuzzy_search(term, glossary.keys())

    if matches:
        return {
            "term": matches[0],
            "definition": glossary[matches[0]]["definition"],
            "formula": glossary[matches[0]].get("formula"),
            "example": glossary[matches[0]].get("example"),
            "related_terms": glossary[matches[0]].get("related", [])
        }

    return {"error": f"Término '{term}' no encontrado en el glosario"}
```

### 2. Crear Glosario Estructurado

```yaml
# config/glossary.yaml
CARTERA_COMERCIAL:
  definition: >
    La cartera comercial es el conjunto de créditos otorgados por un banco
    a empresas y personas físicas con actividad empresarial para financiar
    sus operaciones productivas, comerciales o de servicios.
  formula: null
  example: >
    Si un banco otorga un préstamo de $10 millones a una empresa para
    comprar maquinaria, ese crédito forma parte de su cartera comercial.
  related_terms:
    - CARTERA_VIGENTE
    - CARTERA_VENCIDA
    - IMOR

ICAP:
  definition: >
    El Índice de Capitalización (ICAP) mide la solidez financiera de un banco.
    Representa la proporción del capital del banco respecto a sus activos
    ponderados por riesgo.
  formula: "ICAP = Capital Neto / Activos Ponderados por Riesgo × 100"
  example: >
    Si un banco tiene un ICAP de 15%, significa que por cada $100 de
    activos riesgosos, tiene $15 de capital para absorber pérdidas.
  related_terms:
    - CAPITAL_NETO
    - ACTIVOS_PONDERADOS
```

---

## Criterios de Aceptación

- [x] Query "qué es la cartera comercial" devuelve definición clara
- [x] Query "explícame el ICAP" devuelve definición + fórmula + ejemplo
- [x] El sistema distingue entre query de datos vs query de definición
- [ ] Glosario tiene al menos 20 términos bancarios básicos

## Verificación (2026-02-06)

Replay test: `tests/e2e/regression/test_feedback_replay_2026_02_06.py` — 2/2 passed
- "que es la cartera comercial de un banco?" → Responde con explicación (términos: comercial, banco)
- "qué es el ICAP?" → Responde con definición (término: capital)

El `knowledge` type en QueryRouter ya maneja queries conceptuales. El bug original pudo ser de una versión anterior del prompt.

**DoD pendiente**: Verificar en PROD que las definiciones se entregan correctamente.

---

## Test E2E Requerido

```python
# tests/e2e/regression/test_definition_queries.py

import pytest
from tests.e2e.utils import query_system

class TestDefinitionQueries:
    """
    Test que replica el bug: sistema no responde preguntas conceptuales.

    Feedback original:
    - 61ef795d: "no me dio la explicación de cartera comercial"
    - Query: "que es la cartera comercial de un banco ?"
    """

    @pytest.mark.parametrize("query,expected_terms", [
        ("que es la cartera comercial", ["créditos", "empresas", "comercial"]),
        ("qué es el ICAP", ["capitalización", "capital", "riesgo"]),
        ("explícame el IMOR", ["morosidad", "vencida", "cartera"]),
        ("define cartera vencida", ["vencida", "pago", "días"]),
    ])
    def test_definition_query_returns_explanation(self, query, expected_terms):
        """El sistema debe devolver una explicación, no datos numéricos."""
        response = query_system(query)

        # No debe ser un error
        assert response.get("type") != "error"

        # Debe contener texto explicativo
        text = response.get("response_text", "").lower()
        assert any(term in text for term in expected_terms), \
            f"Response should contain definition terms: {expected_terms}"

        # No debe intentar generar gráfica para definiciones
        assert response.get("chart_status") != "error"

    def test_cartera_comercial_definition_specific(self):
        """Replica exacta del feedback 61ef795d."""
        response = query_system("que es la cartera comercial de un banco ?")

        # Debe explicar qué es, no buscar datos
        text = response.get("response_text", "").lower()
        assert "crédito" in text or "préstamo" in text
        assert "empresa" in text or "comercial" in text
```

---

## Referencias

- Feedback: 61ef795d, 7abc4031
- Archivos de conocimiento: `data/knowledge/`
- Relacionado: `2026-02-04__BUG__bank-code-hallucination` (también falta tool)

## Feedback Vinculado

**1 reporte(s)** de usuarios en producción.

| # | Feedback ID | Usuario | Query | Feedback | Fecha |
|---|-------------|---------|-------|----------|-------|
| 1 | FDBK-0030 | `cb6c6879` | que es la cartera comercial de un banco ? | - no me dio la explicación de cartera comercial | 2026-02-03 |

<details>
<summary>Detalle completo de feedbacks</summary>

### FDBK-0030
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `ced6f20e-ac8e-4047-90dd-e7f43ed3368f`
- **Message**: `61ef795d-bb8f-4ef4-9e0c-215d8e185b46`
- **Rating**: 👎
- **Query**: "que es la cartera comercial de un banco ?"
- **Feedback**: "- no me dio la explicación de cartera comercial"
- **Fecha**: 2026-02-03T19:14:01.820Z

</details>
