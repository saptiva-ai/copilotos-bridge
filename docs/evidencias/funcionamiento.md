# Verificación de Funcionalidad: Kill-Switch de Deep Research y Chat Simple

Este documento contiene la evidencia de que el kill-switch para Deep Research está funcionando correctamente y que el chat simple opera con los modelos Saptiva configurados.

## Variables de Entorno

Para estas pruebas, se asumen las siguientes variables de entorno:

```bash
export BASE_URL="http://localhost:8001"
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMThlODhjOS1lMmUxLTQ5YmMtYjhjMi03M2E3MGVhMDBkYTQiLCJ0eXBlIjoiYWNjZXNzIiwiaWF0IjoxNzU5MTg2NDIyLCJleHAiOjE3NTkxOTAwMjIsInVzZXJuYW1lIjoiZGVtbyIsImVtYWlsIjoiZGVtb0BleGFtcGxlLmNvbSJ9.rrYBWnL6wHz7iInlCbtZtrMZbUMGM2keY0t2l3jgImU"
```

## 1. Verificación del Kill-Switch de Deep Research

### 1.1. Intento de iniciar una nueva investigación

Se espera que la API devuelva un error `410 GONE` cuando se intenta iniciar una investigación, ya que el kill-switch está activo.

**Comando:**

```bash
curl -X POST "$BASE_URL/api/deep-research" \
-H "Authorization: Bearer $TOKEN" \
-H "Content-Type: application/json" \
-d 
'{'
  '"query": "Test query",'
  '"explicit": true
}'
```

**Respuesta Esperada (410 GONE):**

```json
{
  "detail": {
    "error": "Deep Research feature is not available",
    "error_code": "DEEP_RESEARCH_DISABLED",
    "message": "This feature has been disabled. Please use standard chat instead.",
    "kill_switch": true
  }
}
```

### 1.2. Intento de listar las tareas de investigación

Se espera que la API devuelva un error `410 GONE`.

**Comando:**

```bash
curl -X GET "$BASE_URL/api/tasks" \
-H "Authorization: Bearer $TOKEN"
```

**Respuesta Esperada (410 GONE):**

```json
{
  "detail": {
    "error": "Deep Research feature is not available",
    "error_code": "DEEP_RESEARCH_DISABLED",
    "message": "This feature has been disabled.",
    "kill_switch": true
  }
}
```

## 2. Verificación del Chat Simple con Modelos Saptiva

### 2.1. Listar los modelos disponibles

Se espera que la API devuelva la lista de modelos permitidos y el modelo por defecto configurado en las variables de entorno.

**Comando:**

```bash
curl -X GET "$BASE_URL/api/models" \
-H "Authorization: Bearer $TOKEN"
```

**Respuesta Esperada:**

```json
{
  "default_model": "saptiva_turbo",
  "allowed_models": [
    "saptiva_turbo",
    "saptiva_base"
  ]
}
```

### 2.2. Enviar un mensaje de chat

Se espera que el chat responda correctamente utilizando el modelo por defecto (`saptiva_turbo`).

**Comando:**

```bash
curl -X POST "$BASE_URL/api/chat" \
-H "Authorization: Bearer $TOKEN" \
-H "Content-Type: application/json" \
-d 
'{'
  '"message": "Hola, ¿quién eres?",'
  '"model": "saptiva_turbo"
}'
```

**Respuesta Esperada (200 OK):**

```json
{
  "chat_id": "...",
  "message_id": "...",
  "content": "Soy un asistente virtual de Saptiva.",
  "role": "assistant",
  "model": "saptiva_turbo",
  "created_at": "...",
  "tokens": 10,
  "latency_ms": 500,
  "finish_reason": "stop"
}
```

*(Nota: El contenido de la respuesta del chat puede variar)*

