# E2E Multi-Turn Context Test Results

**Fecha:** 2026-01-12
**Test:** `tests/e2e/conversation/test_multi_turn_context.py`
**Configuración:** `E2E_MAX_WORKERS=4`

---

## Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| **Escenarios Pasados** | 8/11 |
| **Escenarios Fallidos** | 3/11 |
| **Pass Rate** | 72.7% |
| **Entity Precision** | 0.410 (TP=80, FP=115) |
| **Entity Recall** | 0.976 (TP=80, FN=2) |
| **Entity F1** | 0.578 |
| **Type Accuracy** | 94.6% (checks=37) |

---

## Resultados por Escenario

### Escenarios Exitosos (8/11)

| ID | Nombre | Turns | Estado |
|----|--------|-------|--------|
| CONV-002 | Topic Switch and Return | 3 | PASS |
| CONV-003 | Entity Correction | 3 | PASS |
| CONV-004 | Anaphoric References | 3 | PASS |
| CONV-005 | Conflicting Context | 3 | PASS |
| CONV-006 | Negation Handling | 3 | PASS |
| CONV-007 | Multi-Metric Conversation | 3 | PASS |
| CONV-008 | Temporal Context Evolution | 4 | PASS |
| CONV-009 | Clarification Resolution | 3 | PASS |

### Escenarios Fallidos (3/11)

#### CONV-001: Long Chain Accumulation

**Descripción:** 5-turn conversation building on previous context

| Turn | Query | Esperado | Obtenido | Estado |
|------|-------|----------|----------|--------|
| 1 | "Dame el IMOR de INVEX" | chart | chart | PASS |
| 2 | "y el ICAP?" | chart | chart | PASS |
| 3 | "comparalo con BBVA" | chart | chart | PASS |
| 4 | "ahora muestra los ultimos 6 meses" | chart | chart | PASS |
| 5 | "solo INVEX" | chart | chart | PASS |

**Nota:** Este escenario pasó en la última ejecución.

---

#### CONV-010: Extended Conversation (7 turns)

**Descripción:** Long conversation stress test

| Turn | Query | Esperado | Obtenido | Estado |
|------|-------|----------|----------|--------|
| 1 | "IMOR de INVEX" | chart | chart | PASS |
| 2 | "agrega BBVA" | chart | chart | PASS |
| 3 | "y Santander" | chart | chart | PASS |
| 4 | "ultimos 6 meses" | chart | chart | PASS |
| 5 | "cambia a ICAP" | chart | chart | PASS |
| 6 | "solo INVEX y sistema" | chart | clarification | FAIL |
| 7 | "regresa a IMOR con los 3 bancos original" | chart | chart | PASS |

**Análisis del fallo:** El turn 6 "solo INVEX y sistema" se interpreta como clarificación porque "sistema" es ambiguo (puede referirse al banco SISTEMA o al concepto de sistema bancario).

---

#### CONV-011: Long Mixed Topics with Priority

**Descripción:** Mix metrics and glossary questions across many turns

| Turn | Query | Esperado | Obtenido | Estado |
|------|-------|----------|----------|--------|
| 1 | "IMOR de INVEX en 2024" | chart | chart | PASS |
| 2 | "Que es un fideicomiso?" | rag | rag | PASS |
| 3 | "ahora ICAP de BBVA" | chart | chart | PASS |
| 4 | "que significa CNVB" | rag | rag | PASS |
| 5 | "regresa al IMOR de INVEX" | chart | chart | PASS |
| 6 | "solo defineme ICAP, sin grafica" | rag | clarification | FAIL |

**Análisis del fallo:** El turn 6 solicita una definición (RAG) pero el sistema lo interpreta como clarificación porque detecta "ICAP" como métrica y espera contexto de gráfica.

---

## Problemas Identificados

### 1. Interpretación de "sistema" como banco
- **Query:** "solo INVEX y sistema"
- **Problema:** El sistema no distingue claramente entre el banco "SISTEMA" y referencias genéricas al sistema bancario.
- **Impacto:** Genera clarificación innecesaria.

### 2. Cambio de modo chart → RAG
- **Query:** "solo defineme ICAP, sin grafica"
- **Problema:** Cuando el usuario explícitamente pide "sin grafica", el sistema debería cambiar a modo RAG para dar una definición.
- **Impacto:** Genera clarificación en lugar de buscar la definición.

---

## Fix Aplicado

### Problema Original
El archivo `apps/backend/src/services/tool_execution_service.py` no tenía `import re`, causando que todas las expresiones regulares para detectar métricas y bancos fallaran silenciosamente.

### Solución
```python
# Antes (líneas 14-16)
import hashlib
import json
from typing import Any, Dict, List, Optional

# Después (líneas 14-17)
import hashlib
import json
import re
from typing import Any, Dict, List, Optional
```

### Impacto del Fix

| Métrica | Antes del Fix | Después del Fix |
|---------|---------------|-----------------|
| Pass Rate | 0% (0/11) | 72.7% (8/11) |
| Entity F1 | 0.119 | 0.578 |
| Type Accuracy | 10.8% | 94.6% |

---

## Recomendaciones

1. **Mejorar detección de intención "definición":** Cuando el usuario dice "defineme X" o "sin grafica", cambiar automáticamente a modo RAG.

2. **Clarificar manejo de "SISTEMA":** Agregar lógica para distinguir entre el banco SISTEMA y referencias genéricas.

3. **Tests de regresión:** Agregar estos casos edge a la suite de tests unitarios.

---

## Ambiente de Ejecución

- **Backend:** Docker container `octavios-chat-bajaware_invex-backend` (healthy)
- **Bank Advisor:** Docker container `octavios-chat-bajaware_invex-bank-advisor` (healthy)
- **Workers:** 4 (E2E_MAX_WORKERS=4)
