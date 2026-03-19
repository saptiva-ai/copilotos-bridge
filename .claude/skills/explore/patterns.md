# Search Patterns by Layer

## Backend (FastAPI)

### Services
```bash
# All services
Glob "apps/backend/src/services/*.py"

# Specific service
Grep "class ChatService" apps/backend/src/services/

# Service methods
Grep "async def" apps/backend/src/services/chat_service.py
```

### Routers
```bash
# All routers
Glob "apps/backend/src/routers/*.py"

# Specific endpoint
Grep "@router.post.*chat" apps/backend/src/routers/

# All endpoints in file
Grep "@router\.(get|post|put|delete)" apps/backend/src/routers/chat.py
```

### Models
```bash
# Beanie documents
Grep "class.*Document" apps/backend/src/models/

# Pydantic schemas
Grep "class.*BaseModel" apps/backend/src/schemas/
```

### Core
```bash
# Config
Grep "class Settings" apps/backend/src/core/

# Dependencies
Grep "def get_" apps/backend/src/core/dependencies.py

# Middleware
Grep "@app.middleware" apps/backend/src/
```

### Tests
```bash
# All test files
Glob "apps/backend/tests/**/*.py"

# Tests for specific function
Grep "def test_chat" apps/backend/tests/

# Fixtures
Grep "@pytest.fixture" apps/backend/tests/
```

## Frontend (Next.js)

### Pages
```bash
# App router pages
Glob "apps/web/src/app/**/page.tsx"

# Layouts
Glob "apps/web/src/app/**/layout.tsx"
```

### Components
```bash
# All components
Glob "apps/web/src/components/**/*.tsx"

# Specific component
Grep "export.*function.*Chat" apps/web/src/components/

# Component with hooks
Grep "useState|useEffect" apps/web/src/components/chat/
```

### Hooks
```bash
# Custom hooks
Glob "apps/web/src/hooks/*.ts"

# Hook usage
Grep "use[A-Z]" apps/web/src/
```

### API/Lib
```bash
# API clients
Glob "apps/web/src/lib/api/*.ts"

# Stores
Glob "apps/web/src/lib/stores/*.ts"
```

## Plugins

### Bank Advisor
```bash
# Services
Glob "plugins/bank-advisor-private/src/bankadvisor/services/*.py"

# Config
Glob "plugins/bank-advisor-private/config/*.yaml"

# Data/ETL
Glob "plugins/bank-advisor-private/data/**/*"
```

### File Manager
```bash
Glob "plugins/public/file-manager/src/**/*.py"
```

## Cross-Cutting

### Environment Variables
```bash
Grep "settings\." apps/backend/src/
Grep "process.env" apps/web/src/
```

### Error Handling
```bash
Grep "raise.*Error" apps/backend/src/
Grep "throw.*Error" apps/web/src/
```

### Logging
```bash
Grep "logger\." apps/backend/src/
Grep "console\." apps/web/src/
```
