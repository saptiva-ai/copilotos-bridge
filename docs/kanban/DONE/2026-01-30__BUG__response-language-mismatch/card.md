---
id: BUG-2026-01-30__response-language-mismatch
title: Sistema Responde en Ingles Cuando Usuario Pregunta en Espanol
status: DONE
phase: Validate
priority: medium
scope_in:
  - Revisar configuracion de idioma en system prompts
  - Verificar que el LLM detecte idioma del usuario
  - Asegurar respuestas consistentes en espanol
scope_out:
  - Soporte multi-idioma completo
  - Traduccion de graficas
artifacts:
  card: card.md
  research: research.md
  plan: plan.md
  validate: validate.md
plan_phase: 1
validation_commands:
  - make test T=api TEST_ARGS='-k language'
pr_files: []
test_status: ''
reported_by: rhernandez@bajaware.com
reported_at: '2026-01-30'
---

# Resumen

**Objetivo**: Corregir bug donde el sistema responde en ingles cuando el usuario hace preguntas en espanol.

**Impacto**: UX deficiente para usuarios hispanohablantes.

---

# Feedback del Usuario

## Reporte - rhernandez@bajaware.com (2026-01-30 00:06)
> "respondió en ingles cuando le pregunte en español"

**Query del usuario**: "explícame como obtuviste que citibanamex creció un 0.2% en el periodo analizado?"

**Fragmento de respuesta en ingles**:
```
"Okay, let's see. The user is asking how I obtained that Citibanamex grew by 0.2%..."
"Wait, but in the previous response, I mentioned CitibanameX with 20.68%..."
"Let me check the original data again..."
```

---

# Analisis Tecnico Preliminar

## Evidencia del Bug

La respuesta contiene texto de "razonamiento interno" del LLM que no deberia ser visible al usuario:

```
"Okay, let's see. The user is asking how I obtained..."
"Wait, but in the previous response..."
"The correct approach is to realize that..."
```

Esto sugiere:
1. El LLM esta usando un modo de "pensamiento" (chain-of-thought) que se filtro a la respuesta
2. El idioma por defecto del razonamiento interno es ingles
3. No se esta aplicando el formato correcto de respuesta

## Hipotesis de Root Cause

**Hipotesis 1 (MAS PROBABLE)**: Se esta usando un modelo con "thinking" mode habilitado y el output del pensamiento se esta incluyendo en la respuesta final.

**Hipotesis 2**: El system prompt no especifica claramente el idioma de respuesta.

**Hipotesis 3**: Hay un problema en el parsing de la respuesta del LLM donde se incluye contenido que deberia ser filtrado.

---

# Datos de Contexto

| Campo | Valor |
|-------|-------|
| Conversation ID | f75ee002-0082-46e8-913a-32e58d17327b |
| User | rhernandez@bajaware.com |
| Fecha | 2026-01-30 |
| Servicio afectado | Backend LLM integration |

---

# Investigacion Completada

1. [x] Revisar system prompt del chat - verificar instruccion de idioma
2. [x] Verificar si se esta usando extended thinking mode
3. [x] Revisar parsing de respuestas del LLM
4. [x] Verificar configuracion del modelo en settings

---

# Root Cause Identificado

**El bug es especifico de Saptiva Cortex**:

1. **Cortex usa `reasoning_content`**: Campo especial para chain-of-thought
2. **Fallback automatico**: Cuando `content` esta vacio, el codigo usa `reasoning_content` como respuesta
   - Ver `src/domain/chat_strategy.py:285-292`
   - Ver `src/services/streaming/saptiva_streamer.py:95-98`
3. **Turbo/Legacy no tienen este campo**: No filtran CoT de la misma manera

El bug ocurrio cuando el usuario uso Cortex (el default anterior) y el LLM no genero `content`, solo `reasoning_content`.

---

# Solucion Implementada

## 1. Sanitizer de Chain-of-Thought (Defensa en Profundidad)

Agregado `strip_chain_of_thought()` a `apps/backend/src/services/text_sanitizer.py`:

```python
def strip_chain_of_thought(text: str) -> str:
    """Remove CoT reasoning patterns that leaked into response."""
    cot_patterns = [
        r"^(?:Okay|Ok|Alright),?\s*(?:let'?s?\s*see|so|now)[.,]?\s*",
        r"^(?:Let me|I'll|I need to)\s+(?:think|check|see)[^.]{0,80}\.\s*",
        r"(?:The user is asking|The question is about)[^.]{0,80}\.\s*",
        # ... mas patrones
    ]
    for pattern in cot_patterns:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE | re.MULTILINE)
    return result
```

## 2. Tests

- **Unit tests**: `apps/backend/tests/unit/services/test_text_sanitizer_cot.py` (14/14 passing)
- **E2E tests**: `tests/e2e/regression/test_bug_2026_01_30_language_mismatch.py` (4/4 passing)

---

# Verificacion

| Test | Resultado |
|------|-----------|
| Unit tests CoT stripping | ✅ 14/14 passing |
| E2E language tests | ✅ 4/4 passing |
| Turbo no filtra CoT | ✅ Confirmado |

---

# Actualizaciones

- 2026-01-30 - Creado desde analisis de feedback de produccion
- 2026-01-30 - Root cause identificado: Saptiva Cortex reasoning_content
- 2026-01-30 - Fix implementado: strip_chain_of_thought sanitizer
- 2026-01-30 - Tests passing: 14/14 unit + 4/4 E2E
- 2026-01-30 - Movido a DONE

## Feedback Vinculado

**1 reporte(s)** de usuarios en producción.

| # | Feedback ID | Usuario | Query | Feedback | Fecha |
|---|-------------|---------|-------|----------|-------|
| 1 | FDBK-0015 | `cb6c6879` | explícame como obtuviste que citibanamex creció un 0.2% e... | - respondió en ingles cuando le pregunte en español - me dio un grafico y tab... | 2026-01-30 |

<details>
<summary>Detalle completo de feedbacks</summary>

### FDBK-0015
- **User**: `cb6c6879-e598-439a-881d-c92c93b6cd2b`
- **Conversation**: `f75ee002-0082-46e8-913a-32e58d17327b`
- **Message**: `19536dc7-32cb-426d-8469-83852db372b5`
- **Rating**: 👎
- **Query**: "explícame como obtuviste que citibanamex creció un 0.2% en el periodo analizado ?"
- **Feedback**: "- respondió en ingles cuando le pregunte en español
  - me dio un grafico y tabla con todos los bancos "
- **Fecha**: 2026-01-30T00:06:23.916Z

</details>
