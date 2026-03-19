---
status: DONE
---
# BUG: Delta bar chart correcto pero LLM texto dice "no tengo datos"

## Tipo: B - LLM Context Gap

## Prioridad: P1 (usuario reporta inconsistencia visible)

## Problema

Cuando el pipeline delta genera un **bar chart correcto** (10/10 bancos, variaciones válidas, INVEX en rojo), el **texto del LLM contradice la gráfica**:

> "Lo siento, pero no tengo los datos de enero 2024 para realizar la comparación solicitada."

El chart muestra los datos correctos (SABADELL +49.13%, MONEX +40.82%, etc.), pero el LLM no tiene acceso a esos datos en su contexto, así que genera texto inventado que contradice la visualización.

## Evidencia

**Prompt**: `Toma como periodo inicial = enero 2024 y como periodo actual = enero 2025. Compara la cartera total entre el periodo inicial y el periodo final entre los bancos (MONEX, INVEX, BANCREA, SABADELL, BANCA MIFEL, MULTIVA, AFIRME, BANSI, VE POR MAS Y BANCO BASE). Presenta el dato del periodo inicial, el dato del periodo final y la variacion. Donde variacion = (periodo actual / periodo inicial -1). Haz una grafica de barras donde se vea la variacion graficada y marca a invex de color rojo`

**Resultado PROD**:
- Chart: Bar chart horizontal correcto, 10 bancos, variaciones en rango [-4.6%, +49.2%]
- Texto: "Lo siento, no tengo los datos de enero 2024..."
- Tabla: Muestra valores correctos (copiados del plotly trace, no del table_data)

## Causa Raiz

`DeltaResult.to_response_dict()` genera 3 campos ricos:

```python
# evolution.py:272-285
return {
    "plotly_config": plotly_config,  # ← Bar chart config
    "table_data": table_data,        # ← 4 columnas: Banco, Valor_A, Valor_B, Variacion
    "summary": "Variacion de CARTERA_TOTAL entre 2024-01-01 y 2025-01-01 para 10 bancos",
}
```

Pero el pipeline de contexto del LLM tiene una brecha:

```
Handler                    Backend                     LLM Context
DeltaResult ──────────→ _build_chart_data() ──────→ analytics_extractor
  plotly_config  ✅         plotly_config  ✅           x/y traces  ✅
  table_data     ✅         table_data     ✅           table_data  ❌ NUNCA INYECTADO
  summary        ✅         summary        ❌ DROPPED   summary     ❌ NUNCA INYECTADO
```

### Brecha 1: `analytics_extractor.py` solo lee plotly traces

`AnalyticsExtractor._extract_series()` extrae coordenadas x/y del plotly_config pero **ignora** `table_data` y `summary`. El LLM recibe valores numéricos crudos sin contexto semántico.

### Brecha 2: `llm_context_builder.py` no inyecta delta context

`BASE_CONTEXT` dice "La grafica ya se genero automaticamente" pero **no dice**:
- Que es un chart de variacion delta entre dos periodos
- Que `table_data` contiene los datos completos
- Que el LLM debe usar esos datos para responder (no inventar)

### Brecha 3: `summary` se pierde en `_build_chart_data()`

`bank_analytics_client.py:1255` extrae `table_data` pero `summary` nunca se pasa al schema `BankChartData`.

## Archivos Involucrados

| # | Archivo | Rol en el bug |
|---|---------|--------------|
| 1 | `plugins/.../application/use_cases/evolution.py:272` | Genera `table_data` + `summary` (correcto) |
| 2 | `apps/backend/src/services/bank_analytics_client.py:1255` | Pasa `table_data` pero pierde `summary` |
| 3 | `apps/backend/src/services/analytics_extractor.py` | Solo extrae plotly traces, ignora `table_data` |
| 4 | `apps/backend/src/services/llm_context_builder.py` | No inyecta delta context al LLM |
| 5 | `apps/backend/src/services/streaming/system_prompt_builder.py` | Orquesta build del contexto |

## Relacion con Otros Tickets

- **Hermano de**: `2026-02-11__BUG__evolution-handler-multibank-routing` (routing multi-banco)
- **Depende de**: El fix de regex `_PERIODO_LABEL` con comillas opcionales (ya en develop: `ad529df8`)
- **Impacta**: Todos los delta charts (cartera_total, cartera_comercial, cartera_comercial_sin_gob)
