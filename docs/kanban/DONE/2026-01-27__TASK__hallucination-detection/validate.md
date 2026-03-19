# Validación: Detección de Alucinaciones

## Comandos de Validación

```bash
# 1. Tests del HallucinationDetectorService
make test-local TEST_FILE="tests/unit/test_hallucination_detector.py"

# 2. Tests de integración
make test-local TEST_FILE="tests/unit/test_streaming_services.py" TEST_ARGS="-k hallucination"

# 3. Test manual con caso de fsaavedra
# Reproducir: "comparativo de cartera comercial por región"
# Verificar: Sistema responde "no disponible" en lugar de inventar
```

## Criterios de Aceptación

### Funcionales

- [ ] **AC1:** Detectar porcentajes que no suman 100%
  - Input: Texto con porcentajes sumando 113.7%
  - Output: Warning tipo "percentage_sum"

- [ ] **AC2:** Detectar valores no presentes en fuente
  - Input: Respuesta con valor X, fuente solo tiene valor Y
  - Output: Warning tipo "value_mismatch"

- [ ] **AC3:** Detectar desgloses no soportados
  - Input: Respuesta menciona "región Centro", fuente solo tiene serie temporal
  - Output: Warning tipo "unsupported_breakdown"

- [ ] **AC4:** LLM responde "no disponible" para datos inexistentes
  - Input: "Dame cartera comercial por región"
  - Output: "No tengo desglose regional, pero puedo mostrar evolución temporal"

- [ ] **AC5:** Logging de warnings para análisis
  - Verificar logs con: `grep "hallucination_detector" logs/*.log`

### No Funcionales

- [ ] **NFR1:** Latencia de validación <50ms
- [ ] **NFR2:** No falsos positivos en valores derivados (sumas, promedios)
- [ ] **NFR3:** Backward compatible con respuestas existentes

## Casos de Test Específicos

### Caso 1: Reproducir Error de fsaavedra

```python
def test_fsaavedra_case():
    """Reproducir el caso exacto que causó feedback negativo."""
    # Datos reales del bank-advisor
    bank_chart_data = {
        "plotly_config": {
            "data": [{
                "y": [16402586992],  # Valor real Oct 2025
                "name": "INVEX"
            }]
        },
        "metadata": {"intent": "evolution"}
    }

    # Respuesta problemática del LLM (simulada)
    problematic_response = """
    | Región | Saldo (MDP) | Participación (%) |
    | Centro | 7,745,103,317 | 47.2% |
    | Occidente | 4,471,864,208 | 27.3% |
    | Norte | 3,249,782,454 | 19.8% |
    | Sur | 1,935,836,993 | 11.8% |
    | Sureste | 1,243,876,543 | 7.6% |
    | Total | 18,646,463,515 | 100.0% |
    """

    warnings = HallucinationDetectorService.validate_response(
        problematic_response, bank_chart_data
    )

    # Debe detectar 3 tipos de problemas
    assert any(w.type == "percentage_sum" for w in warnings)
    assert any(w.type == "value_mismatch" for w in warnings)
    assert any(w.type == "unsupported_breakdown" for w in warnings)
```

### Caso 2: Respuesta Válida

```python
def test_valid_response():
    """Verificar que respuestas correctas no generen warnings."""
    bank_chart_data = {
        "plotly_config": {
            "data": [{
                "y": [16402586992],
                "name": "INVEX"
            }]
        }
    }

    valid_response = """
    El saldo de la cartera comercial de INVEX al cierre de
    octubre de 2025 es **16,402,586,992 MDP**.
    """

    warnings = HallucinationDetectorService.validate_response(
        valid_response, bank_chart_data
    )

    assert len(warnings) == 0
```

## Métricas de Éxito

| Métrica | Baseline | Target |
|---------|----------|--------|
| Feedback negativo por datos incorrectos | 3 (100% de negativos) | <1% |
| Detección de porcentajes erróneos | 0% | 100% |
| Detección de valores no en fuente | 0% | >90% |
| Latencia de validación | N/A | <50ms |

## Validación en Producción

1. Desplegar a staging
2. Reproducir query: "cartera comercial de INVEX por región"
3. Verificar:
   - [ ] No inventa datos regionales
   - [ ] Responde con datos disponibles (temporal)
   - [ ] Sugiere alternativa al usuario

## Log de Validación

_A completar durante implementación_

| Fecha | Fase | Status | Notas |
|-------|------|--------|-------|
| | | | |
