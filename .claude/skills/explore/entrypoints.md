# Service Entrypoints

## Key Files by Service

| Service | Main Entrypoint | Purpose |
|---------|-----------------|---------|
| Backend | `apps/backend/src/main.py` | FastAPI app creation |
| Frontend | `apps/web/src/app/layout.tsx` | Root layout |
| File Manager | `plugins/public/file-manager/src/main.py` | Plugin entrypoint |
| Bank Advisor | `plugins/bank-advisor-private/src/main.py` | NL2SQL service |

## Backend Architecture

```
apps/backend/src/
├── main.py              # App factory, startup
├── routers/             # HTTP endpoints
│   ├── chat.py          # /api/chat/*
│   ├── auth.py          # /api/auth/*
│   └── documents.py     # /api/documents/*
├── services/            # Business logic
│   ├── chat_service.py  # Chat orchestration
│   └── auth_service.py  # Authentication
├── models/              # Beanie documents
│   ├── user.py          # User model
│   └── chat.py          # ChatMessage model
├── schemas/             # Pydantic DTOs
├── core/                # Cross-cutting
│   ├── config.py        # Settings
│   ├── dependencies.py  # DI factories
│   └── security.py      # JWT, auth
└── clients/             # External services
    └── saptiva_client.py
```

## Frontend Architecture

```
apps/web/src/
├── app/                 # Next.js App Router
│   ├── layout.tsx       # Root layout
│   ├── page.tsx         # Home page
│   └── chat/
│       └── page.tsx     # Chat page
├── components/          # React components
│   ├── ui/              # Base components
│   └── chat/            # Chat-specific
│       ├── ChatContainer.tsx
│       └── ChatMessage.tsx
├── hooks/               # Custom hooks
│   └── useChat.ts
├── lib/                 # Utilities
│   ├── api/             # API clients
│   └── stores/          # State management
└── types/               # TypeScript types
```

## Plugin Architecture

### Bank Advisor
```
plugins/bank-advisor-private/
├── src/
│   ├── main.py          # FastAPI app
│   └── bankadvisor/
│       ├── services/    # NL2SQL services
│       ├── tools/       # MCP tools
│       └── agents/      # LLM agents
├── config/              # YAML configs
└── data/                # ETL scripts
```

## Finding Related Code

### From Router to Service
```python
# In router, find service dependency
Grep "Depends.*Service" apps/backend/src/routers/chat.py
# → ChatService

# Then find service implementation
Read apps/backend/src/services/chat_service.py
```

### From Component to Hook
```typescript
// In component, find hook usage
Grep "useChat" apps/web/src/components/chat/ChatContainer.tsx
// → useChat

// Then find hook implementation
Read apps/web/src/hooks/useChat.ts
```

### From Test to Implementation
```python
# Find what's being tested
Grep "from.*import" apps/backend/tests/unit/test_chat.py
# → from src.services.chat_service import ChatService

# Then read implementation
Read apps/backend/src/services/chat_service.py
```

## Quick Navigation Commands

```bash
# Find main entrypoint
Read apps/backend/src/main.py

# Find all routers
Glob "apps/backend/src/routers/*.py"

# Find all services
Glob "apps/backend/src/services/*.py"

# Find frontend pages
Glob "apps/web/src/app/**/page.tsx"

# Find frontend components
Glob "apps/web/src/components/**/*.tsx"
```
