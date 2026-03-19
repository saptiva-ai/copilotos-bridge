# Patrones de Código

> Patrones comunes usados en el codebase. Ejemplos mínimos para referencia rápida.

## Cuándo Usar Cada Patrón

| Patrón | Uso |
|--------|-----|
| HTTP Client | Core → plugins públicos (File Manager) |
| MCP Protocol | Core → plugins MCP (Bank Advisor) |
| SSE Streaming | Respuestas de chat en tiempo real |
| Repository (Beanie) | Acceso a MongoDB |
| Service Layer | Lógica de negocio aislada |
| Dependency Injection | Inyectar servicios en routers |

## HTTP Client (Inter-Plugin)

```python
# apps/backend/src/services/document_service.py
async def upload_to_file_manager(file_bytes: bytes, metadata: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.file_manager_url}/upload",
            files={"file": file_bytes}, data=metadata
        )
        return response.json()
```

## MCP Protocol (Tool Invocation)

```python
# apps/backend/src/services/audit_mcp_client.py
async def audit_document(file_id: str, policy: str):
    result = await invoke_tool(
        tool_name="audit_document_full",
        arguments={"file_id": file_id, "policy": policy}
    )
    return result
```

## SSE Streaming (Chat)

```python
# apps/backend/src/routers/chat.py
@router.post("/chat/stream")
async def stream_chat(request: ChatRequest):
    async def event_generator():
        async for chunk in chat_service.stream_response(request):
            yield {"data": chunk.model_dump_json()}
    return EventSourceResponse(event_generator())
```

**Frontend:**
```typescript
const eventSource = new EventSource('/api/chat/stream');
eventSource.onmessage = (e) => appendToMessage(JSON.parse(e.data).content);
```

## Optimistic Updates (Frontend)

```typescript
// apps/web/src/lib/stores/chatStore.ts
const sendMessage = async (content: string) => {
  const tempId = crypto.randomUUID();
  addMessage({ id: tempId, content, status: 'sending' }); // Optimista
  try {
    const response = await api.sendMessage(content);
    updateMessage(tempId, response);
  } catch { removeMessage(tempId); showToast('Error'); }
};
```

## Repository Pattern (Beanie ODM)

```python
# apps/backend/src/models/chat.py
class ChatMessage(Document):
    user_id: str
    content: str
    role: Literal["user", "assistant"]
    class Settings:
        collection = "messages"

# Uso
messages = await ChatMessage.find(ChatMessage.user_id == user_id).to_list()
```

## Service Layer Pattern

```python
# apps/backend/src/services/chat_service.py
class ChatService:
    def __init__(self, saptiva_client: SaptivaClient, db: Database):
        self.saptiva = saptiva_client
        self.db = db

    async def process_message(self, user_id: str, content: str) -> Message:
        history = await self.db.get_history(user_id)
        response = await self.saptiva.complete(content, history)
        await self.db.save_message(user_id, response)
        return response
```

## Dependency Injection

```python
# apps/backend/src/core/dependencies.py
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Database = Depends(get_database)
) -> User:
    payload = verify_jwt(token)
    user = await db.get_user(payload["sub"])
    if not user: raise HTTPException(401, "Invalid token")
    return user

# Uso en router
@router.get("/me")
async def get_profile(user: User = Depends(get_current_user)):
    return user
```

## Error Handling

```python
# Excepciones de dominio
class DomainError(Exception):
    def __init__(self, message: str, code: str):
        self.message, self.code = message, code

class MetricNotFoundError(DomainError): pass

# Handler global
@app.exception_handler(DomainError)
async def domain_error_handler(request, exc: DomainError):
    return JSONResponse(status_code=400, content={"error": exc.code, "message": exc.message})
```

## Pydantic Settings

```python
# apps/backend/src/core/config.py
class Settings(BaseSettings):
    mongodb_uri: str
    redis_uri: str
    jwt_secret: str
    class Config:
        env_file = ".env"

settings = Settings()
```
