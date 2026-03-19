# Code Conventions

## Python (Backend)

### Style
- **Formatter**: Black (line-length=88)
- **Linter**: ruff
- **Import order**: isort (built into ruff)

### Naming

| Entity | Convention | Example |
|--------|------------|---------|
| Functions | `snake_case` | `get_user_metrics()` |
| Variables | `snake_case` | `user_count` |
| Classes | `PascalCase` | `ChatService` |
| Constants | `UPPER_SNAKE` | `MAX_RETRIES` |
| Private | `_leading_underscore` | `_internal_method()` |

### Type Hints

**Required** for all public functions:

```python
async def get_user_metrics(
    user_id: str,
    time_range: TimeRange,
    *,  # Force keyword args after this
    include_details: bool = False,
) -> MetricsResponse:
    """Get user metrics for given time range.

    Args:
        user_id: User identifier
        time_range: Time range to query
        include_details: Include breakdown details

    Returns:
        MetricsResponse with data and metadata

    Raises:
        UserNotFoundError: If user doesn't exist
    """
```

### Docstrings

Use **Google style**:

```python
def calculate_score(values: list[float], weights: list[float]) -> float:
    """Calculate weighted average score.

    Args:
        values: List of raw values
        weights: List of weights (same length as values)

    Returns:
        Weighted average as float

    Raises:
        ValueError: If lists have different lengths

    Example:
        >>> calculate_score([0.8, 0.9], [0.5, 0.5])
        0.85
    """
```

## TypeScript (Frontend)

### Style
- **Linter**: ESLint
- **Formatter**: Prettier
- **Config**: `.eslintrc.js`, `.prettierrc`

### Naming

| Entity | Convention | Example |
|--------|------------|---------|
| Components | `PascalCase` | `ChatMessage` |
| Functions | `camelCase` | `handleSubmit()` |
| Variables | `camelCase` | `messageCount` |
| Types/Interfaces | `PascalCase` | `ChatMessageProps` |
| Constants | `UPPER_SNAKE` | `API_BASE_URL` |
| Files (components) | `PascalCase.tsx` | `ChatMessage.tsx` |
| Files (utils) | `camelCase.ts` | `formatDate.ts` |

### Types

**Avoid `any`** - use explicit types:

```typescript
// ❌ Bad
const handleData = (data: any) => { ... };

// ✅ Good
interface ChatResponse {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  createdAt: Date;
}

const handleData = (data: ChatResponse) => { ... };
```

### Component Props

```typescript
interface ChatMessageProps {
  message: Message;
  isLoading?: boolean;
  onFeedback: (type: 'up' | 'down') => void;
}

export function ChatMessage({
  message,
  isLoading = false,
  onFeedback
}: ChatMessageProps) {
  // ...
}
```

### Hooks

```typescript
// Custom hook naming: use{Purpose}
export function useMessages(conversationId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Always return object for named access
  return { messages, isLoading, refetch };
}
```

## Import Organization

### Python

```python
# 1. Standard library
import os
from datetime import datetime
from typing import Optional

# 2. Third-party
import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel

# 3. Local application
from src.core.config import settings
from src.models.user import User
from src.services.chat import ChatService
```

### TypeScript

```typescript
// 1. React/Next
import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

// 2. Third-party
import { motion } from 'framer-motion';
import clsx from 'clsx';

// 3. Local components
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/hooks/useAuth';

// 4. Types
import type { Message } from '@/types/chat';
```

## Error Messages

Use descriptive, actionable messages:

```python
# ❌ Bad
raise ValueError("Invalid input")

# ✅ Good
raise ValueError(
    f"Invalid user_id format: '{user_id}'. "
    f"Expected UUID, got {type(user_id).__name__}"
)
```

## Comments

Only when logic isn't self-evident:

```python
# ❌ Bad - obvious
# Loop through users
for user in users:
    ...

# ✅ Good - explains WHY
# Retry up to 3 times with exponential backoff
# because Saptiva API rate limits at 100 req/min
for attempt in range(3):
    ...
```
