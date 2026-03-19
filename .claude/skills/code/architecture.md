# Clean Architecture

## Layer Structure

```
┌─────────────────────────────────────────────────┐
│                  Presentation                    │
│              (Routers / Components)              │
│   apps/backend/src/routers/                     │
│   apps/web/src/components/                      │
└─────────────────────┬───────────────────────────┘
                      │ DTOs / ViewModels
                      ▼
┌─────────────────────────────────────────────────┐
│                Application                       │
│              (Services / Use Cases)              │
│   apps/backend/src/services/                    │
│   apps/web/src/hooks/                           │
└─────────────────────┬───────────────────────────┘
                      │ Domain Models
                      ▼
┌─────────────────────────────────────────────────┐
│                   Domain                         │
│           (Entities / Business Rules)            │
│   apps/backend/src/models/                      │
│   apps/web/src/types/                           │
└─────────────────────┬───────────────────────────┘
                      │ Repository Interfaces
                      ▼
┌─────────────────────────────────────────────────┐
│               Infrastructure                     │
│        (Database / External Services)            │
│   apps/backend/src/core/database.py             │
│   apps/backend/src/clients/                     │
└─────────────────────────────────────────────────┘
```

## Dependency Rule

**Dependencies point INWARD only:**
- Routers depend on Services (not vice versa)
- Services depend on Models (not vice versa)
- Models depend on NOTHING

## Backend Patterns

### Repository Pattern (Beanie)

```python
# apps/backend/src/models/chat.py
from beanie import Document
from pydantic import Field
from datetime import datetime

class ChatMessage(Document):
    """Chat message entity."""
    user_id: str
    content: str
    role: Literal["user", "assistant"]
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        collection = "messages"

# Usage in service (not router!)
messages = await ChatMessage.find(
    ChatMessage.user_id == user_id
).sort(-ChatMessage.created_at).to_list(limit=50)
```

### Service Layer Pattern

```python
# apps/backend/src/services/chat_service.py
from typing import Protocol

class LLMClient(Protocol):
    """Abstract LLM interface - DIP."""
    async def complete(self, prompt: str, history: list) -> str: ...

class ChatService:
    """Chat business logic - single responsibility."""

    def __init__(
        self,
        llm_client: LLMClient,  # Injected, not constructed
        db: Database,
    ):
        self._llm = llm_client
        self._db = db

    async def process_message(
        self,
        user_id: str,
        content: str,
    ) -> ChatMessage:
        """Process user message and return response."""
        # 1. Get context
        history = await self._get_history(user_id)

        # 2. Generate response (delegate to LLM)
        response = await self._llm.complete(content, history)

        # 3. Persist
        message = await self._save_message(user_id, response)

        return message
```

### Dependency Injection

```python
# apps/backend/src/core/dependencies.py
from functools import lru_cache

@lru_cache
def get_settings() -> Settings:
    return Settings()

async def get_database() -> Database:
    # Returns singleton database connection
    ...

async def get_chat_service(
    db: Database = Depends(get_database),
    llm: LLMClient = Depends(get_llm_client),
) -> ChatService:
    return ChatService(llm_client=llm, db=db)

# apps/backend/src/routers/chat.py
@router.post("/chat")
async def chat(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
    user: User = Depends(get_current_user),
):
    return await service.process_message(user.id, request.content)
```

## Frontend Patterns

### Component Composition

```typescript
// apps/web/src/components/chat/ChatContainer.tsx
// Container: handles state and logic
export function ChatContainer({ conversationId }: Props) {
  const { messages, isLoading, sendMessage } = useChat(conversationId);

  return (
    <ChatLayout>
      <MessageList messages={messages} isLoading={isLoading} />
      <ChatInput onSend={sendMessage} disabled={isLoading} />
    </ChatLayout>
  );
}

// Presentational: pure rendering
function MessageList({ messages, isLoading }: Props) {
  return (
    <div className="space-y-4">
      {messages.map(msg => (
        <ChatMessage key={msg.id} message={msg} />
      ))}
      {isLoading && <LoadingIndicator />}
    </div>
  );
}
```

### Custom Hooks (Use Cases)

```typescript
// apps/web/src/hooks/useChat.ts
export function useChat(conversationId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = useCallback(async (content: string) => {
    // Optimistic update
    const tempId = crypto.randomUUID();
    setMessages(prev => [...prev, { id: tempId, content, status: 'sending' }]);

    try {
      const response = await chatApi.send(conversationId, content);
      setMessages(prev => prev.map(m =>
        m.id === tempId ? response : m
      ));
    } catch (error) {
      setMessages(prev => prev.filter(m => m.id !== tempId));
      toast.error('Failed to send message');
    }
  }, [conversationId]);

  return { messages, isLoading, sendMessage };
}
```

### API Layer Separation

```typescript
// apps/web/src/lib/api/chat.ts
// Infrastructure - knows about HTTP, endpoints
export const chatApi = {
  async send(conversationId: string, content: string): Promise<Message> {
    const response = await fetch(`/api/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
    if (!response.ok) throw new ApiError(response);
    return response.json();
  },

  async getHistory(conversationId: string): Promise<Message[]> {
    const response = await fetch(`/api/conversations/${conversationId}/messages`);
    return response.json();
  },
};
```

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| Fat controllers | Router has business logic | Move to service layer |
| Anemic models | Models are just data | Add behavior methods |
| Service locator | Hidden dependencies | Explicit injection |
| Circular imports | A imports B, B imports A | Introduce interface |
| God class | One class does everything | Split by responsibility |

## Module Boundaries

```
apps/backend/src/
├── routers/         # HTTP handlers ONLY (no business logic)
├── services/        # Business logic (no HTTP concepts)
├── models/          # Domain entities (Beanie documents)
├── schemas/         # DTOs (Pydantic models for API)
├── core/            # Cross-cutting (config, deps, errors)
└── clients/         # External service clients

apps/web/src/
├── components/      # UI components (presentational)
├── hooks/           # Custom hooks (use cases)
├── lib/api/         # API clients (infrastructure)
├── types/           # TypeScript types (domain)
└── utils/           # Pure utility functions
```
