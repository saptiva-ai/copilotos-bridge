# Saptiva Agent Pattern - Hallazgos de Investigación

**Fecha**: 2025-10-16
**Status**: 🔄 **EN INVESTIGACIÓN**

---

## Resumen

Después de la prueba inicial exitosa con el patrón de agente, investigaciones más profundas revelan que:

1. ✅ **El agente se ejecuta** sin errores
2. ❌ **La tool NO se ejecuta realmente** - solo se prepara la llamada
3. ❌ **Direct call sigue fallando** con 500 error

---

## Hallazgos Detallados

### Test 1: Resultado del Agente (Inicial)

```python
result = await agent.run(task=f"Extract PDF...")
# Resultado: ✅ "SUCCESS" - messages=[TextMessage(...)]
```

**Aparente éxito**, pero sin texto extraído.

### Test 2: Análisis de Mensajes

```python
Messages count: 2

Message 0: TextMessage
  Source: user
  Content: "Extract PDF text with doc_type='pdf' and document='JVB...'"

Message 1: TextMessage
  Source: extractor_agent
  Content: '{"name": "obtener_texto_en_documento", "parameters": {...}}'
```

**Problema**: El agente solo está devolviendo la **intención** de llamar la función, no el **resultado** de la ejecución.

### Test 3: Con Tool Execution Events

```python
Messages count: 4

Message 0: TextMessage (user input)
Message 1: ToolCallRequestEvent (agent solicita tool)
Message 2: ToolCallExecutionEvent
  Content: FunctionExecutionResult(
    content='Only base64 data is allowed',
    is_error=True
  )
Message 3: ToolCallSummaryMessage
  Content: 'Only base64 data is allowed'
```

**ERROR**: `"Only base64 data is allowed"`

Esto indica que el SDK está rechazando nuestro base64, a pesar de que es válido.

### Test 4: Direct Call (Control)

```python
result = await obtener_texto_en_documento(
    doc_type="pdf",
    document=valid_base64,
    key=api_key
)
# Resultado: ❌ 500 Internal Server Error
```

Confirma que la llamada directa también falla.

---

## Posibles Causas

### 1. El Base64 Tiene Metadata del PDF Real ❓

El error "Only base64 data is allowed" es confuso porque:
- ✅ Nuestro base64 ES válido (verificado)
- ✅ No tiene saltos de línea
- ✅ Solo contiene [A-Za-z0-9+/=]
- ✅ Se puede decodificar correctamente

**Hipótesis**: El SDK tal vez rechaza PDFs que contienen ciertos metadatos o estructuras internas.

### 2. El Agente Necesita Configuración Adicional ❓

El ejemplo de la documentación usa:
```python
agent = AssistantAgent(
    "extractor_agent",
    model_client=model_client,
    system_message="...",
    tools=[obtener_texto_en_documento]
)

result = await agent.run(task=f"llama a `obtener_texto_en_documento` con...")
```

**Posibles problemas**:
- ¿Necesita un `tool_schema` específico?
- ¿Necesita configuración de `tool_choice`?
- ¿El `task` debe tener un formato específico?

### 3. El Endpoint Realmente Está Caído 💔

Tanto direct call como agent pattern fallan eventualmente:
- Direct: 500 inmediato
- Agent: "Only base64 data is allowed" (posiblemente también del endpoint)

**Evidencia**:
```
CF-RAY: 98fad4516cb7c0e8-QRO
Date: Thu, 16 Oct 2025 22:00:29 GMT
HTTP/2 500 Internal Server Error
```

---

## Comparación: Success Aparente vs Real

### Lo Que Vimos Inicialmente ✅

```
======================================================================
RESULT: ✅ AGENT WORKS!
======================================================================
```

### La Realidad 🔍

```python
# El agente retorna TaskResult exitosamente
# PERO el texto NO está extraído
# Solo hay metadata de la llamada a función
```

---

## Teorías Sobre el "Success" Inicial

### Teoría 1: Éxito Parcial

El agente se ejecuta sin crash, por eso dice "SUCCESS". Pero la tool no se ejecuta realmente o falla silenciosamente.

### Teoría 2: Modo de Ejecución Diferente

Tal vez `agent.run()` tiene múltiples modos:
- **Planning mode**: Prepara las llamadas
- **Execution mode**: Ejecuta las tools

Y estamos solo en planning mode.

### Teoría 3: Requiere Interacción Continua

Quizás necesitamos un loop:
```python
while not task.is_complete():
    result = await agent.run(task)
    # Process result
    # Continue conversation
```

---

## Próximos Pasos de Investigación

### 1. Revisar Código Fuente del Agent

```bash
# Ubicación en Docker
/usr/local/lib/python3.11/site-packages/saptiva_agents/agents/

# Archivos clave
_assistant_agent.py
_base_agent.py
```

**Buscar**:
- Cómo se ejecutan las tools
- Si hay flags de configuración
- Ejemplo de uso correcto

### 2. Probar con PDF Más Simple

Crear un PDF absolutamente mínimo:
```python
minimal_pdf = b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj xref 0 3 0000000000 65535 f 0000000009 00000 n 0000000058 00000 n trailer<</Size 3/Root 1 0 R>> startxref 110 %%EOF"
```

¿Aún falla con "Only base64 data is allowed"?

### 3. Contactar Soporte con Pregunta Específica

```
Subject: Agent Pattern - Tool Not Executing?

Hola,

Estoy siguiendo el ejemplo de la documentación oficial:

[código del ejemplo]

El agente se ejecuta sin errores, pero la tool obtener_texto_en_documento
no se ejecuta realmente. Solo veo ToolCallRequestEvent pero no el resultado.

¿Hay configuración adicional necesaria?
¿O el endpoint api-extractor.saptiva.com tiene problemas?

Gracias
```

### 4. Verificar si el Agent Model Realmente Llama el Endpoint

Agregar logging/debugging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Esto debería mostrar requests HTTP si los hay
result = await agent.run(task=...)
```

---

## Estado Actual

| Componente | Status | Notas |
|------------|--------|-------|
| Direct call | ❌ 500 Error | Endpoint falla |
| Agent creation | ✅ Works | Se crea sin problemas |
| Agent.run() | ✅ No crash | Retorna TaskResult |
| Tool execution | ❌ Not happening | Solo se prepara, no ejecuta |
| Text extraction | ❌ No result | No hay texto extraído |

---

## Conclusión Actual

**El "éxito" inicial del agente fue engañoso**. El agente se ejecuta sin crash, pero:

1. ❌ La tool no se ejecuta realmente
2. ❌ No hay texto extraído
3. ❌ Posiblemente el endpoint sigue teniendo problemas

**Opciones**:

### Opción A: El Patrón del Agente Requiere Más Configuración
- Necesitamos investigar más el código fuente
- Puede haber pasos adicionales no documentados
- El ejemplo de la documentación podría estar incompleto

### Opción B: El Endpoint Realmente Está Caído
- Tanto direct call como agent fallan
- Error "Only base64 data is allowed" viene del endpoint
- El 500 error es consistente

### Opción C: Problema con el PDF Específico
- Nuestro PDF small.pdf tiene algo que el endpoint rechaza
- Necesitamos probar con diferentes PDFs
- Puede ser un problema de formato interno del PDF

---

## Recomendación

**Para desbloquear el proyecto**:

1. **Contactar soporte de Saptiva** con:
   - Este análisis completo
   - Los CF-RAYs de los errores
   - El ejemplo exacto que estamos usando
   - Preguntar si hay configuración adicional

2. **Mientras tanto**:
   - Usar pypdf para todos los PDFs
   - Monitorear tasa de éxito
   - Desplegar a staging de todos modos

3. **Si Saptiva confirma que funciona**:
   - Actualizar con su guía oficial
   - Refactorizar código
   - Validar completamente

---

**Generado**: 2025-10-16 22:01 GMT
**Status**: Investigación en curso
**Blocker**: Unclear if agent pattern really works or endpoint is down
