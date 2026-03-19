# Fork and Feature Management Strategy

This document describes the architecture and branching strategy for managing client-specific features in the octavios-chat project, specifically the audit system for Capital 414.

## Repository Structure

```
UPSTREAM (public)
github.com/saptiva-ai/octavios-chat
  └── main (open-source base product)

FORK (private)
github.com/saptiva-ai/octavios-chat-capital414
  ├── main (synced with upstream, open-source features)
  ├── develop (active development, open-source features)
  └── client/capital414 (client-specific features + open-source base)
```

## Architecture Pattern: Chain of Responsibility

### Overview

We use the **Chain of Responsibility pattern** to decouple client-specific message handling from the core chat system. This allows:

- ✅ **Feature Toggle**: Client features exist only in client branches
- ✅ **Open/Closed**: Add handlers without modifying core code
- ✅ **Testability**: Each handler is independent
- ✅ **Maintainability**: Sync upstream changes without conflicts

### Implementation

#### Base Infrastructure (All Repos)

File: `apps/api/src/domain/message_handlers.py`

```python
class MessageHandler(ABC):
    """Base class for all message handlers."""

    @abstractmethod
    async def can_handle(self, context: ChatContext) -> bool:
        pass

    @abstractmethod
    async def process(self, context: ChatContext, **kwargs) -> ChatProcessingResult:
        pass

class StandardChatHandler(MessageHandler):
    """Handles normal chat messages (fallback)."""
    async def can_handle(self, context: ChatContext) -> bool:
        return True  # Always accepts

def create_handler_chain() -> MessageHandler:
    """Factory with auto-detection of client-specific handlers."""
    standard_handler = StandardChatHandler()

    try:
        from .audit_handler import AuditCommandHandler
        return AuditCommandHandler(next_handler=standard_handler)
    except ImportError:
        # Open-source version - no audit handler
        return standard_handler
```

#### Client-Specific Handler (Capital 414 Only)

File: `apps/api/src/domain/audit_handler.py` (only in `client/capital414` branch)

```python
class AuditCommandHandler(MessageHandler):
    """Handles 'Auditar archivo:' commands."""

    AUDIT_COMMAND_PREFIX = "Auditar archivo:"

    async def can_handle(self, context: ChatContext) -> bool:
        return context.message.strip().startswith(self.AUDIT_COMMAND_PREFIX)

    async def process(self, context: ChatContext, **kwargs) -> ChatProcessingResult:
        # Execute document validation
        # Generate PDF report
        # Return formatted summary
        ...
```

### Handler Chain Flow

```
User Message
    ↓
create_handler_chain()
    ↓
    ├── AuditCommandHandler? ← Only in client/capital414
    │   ├── can_handle() = True → process() → Return result
    │   └── can_handle() = False → Pass to next
    ↓
StandardChatHandler (fallback)
    └── Always processes → Return chat response
```

## Workflow

### 1. Development of Open-Source Features

Work in `develop` branch (without client-specific code):

```bash
# Work on develop
git checkout develop
# ... make changes to shared features ...
git add .
git commit -m "feat: add new shared feature"
git push origin develop

# When ready, merge to main
git checkout main
git merge develop --no-ff
git push origin main
```

### 2. Syncing Upstream Changes

Bring changes from public repo to fork:

```bash
# Update main from upstream
git checkout main
git fetch upstream
git merge upstream/main
git push origin main

# Update develop
git checkout develop
git merge main
git push origin develop

# Update client branch with new changes
git checkout client/capital414
git merge develop  # Or: git rebase develop for cleaner history

# Resolve conflicts if any (keep audit files!)
git add .
git commit -m "merge: sync with develop"
git push origin client/capital414
```

### 3. Working on Client-Specific Features

Add or modify audit system in `client/capital414`:

```bash
git checkout client/capital414

# Modify audit-specific files
git add apps/api/src/domain/audit_handler.py
git add apps/api/src/services/*auditor*.py
git commit -m "feat(audit): improve validation accuracy"
git push origin client/capital414
```

### 4. Contributing to Upstream

To contribute shared features back to the public repo:

```bash
# Create PR from fork to upstream
# From: saptiva-ai/octavios-chat-capital414:main
# To:   saptiva-ai/octavios-chat:main

# Ensure NO client-specific code is included!
# The PR should only contain:
# - Improvements to core chat system
# - Bug fixes in shared components
# - New shared features
```

## File Organization

### Shared Files (All Repos)

```
apps/api/src/
├── routers/chat.py (uses create_handler_chain())
├── services/chat_service.py
├── services/document_service.py
├── domain/
│   ├── chat_strategy.py
│   ├── chat_context.py
│   ├── chat_response_builder.py
│   └── message_handlers.py ← Shared base
```

### Client-Specific Files (Only in client/capital414)

```
apps/api/src/
├── domain/
│   └── audit_handler.py ← Client-specific
├── services/
│   ├── validation_coordinator.py
│   ├── *auditor*.py (8 files)
│   ├── policy_manager.py
│   ├── policy_detector.py
│   ├── report_generator.py
│   └── summary_formatter.py
├── models/
│   └── validation_report.py
├── schemas/
│   └── audit_message.py
├── config/
│   ├── policies.yaml
│   └── compliance.yaml
└── assets/
    └── logo_template.png
```

### Frontend Files (client/capital414)

```
apps/web/src/
├── components/
│   ├── chat/Audit*.tsx (4 files)
│   ├── validation/ (3 files)
├── hooks/
│   ├── useAuditFile.ts
│   └── useAuditFlow.ts
├── lib/stores/
│   └── audit-store.ts
└── types/
    └── validation.ts
```

## Deployment

### Open-Source Version

```bash
git checkout main
docker compose -f docker-compose.yml up -d
# Runs without audit system
```

### Client-Specific Version (Capital 414)

```bash
git checkout client/capital414
docker compose -f docker-compose.yml up -d
# Runs with full audit system
```

## Benefits

### For Open-Source Repo

- ✅ Clean codebase without proprietary features
- ✅ Easy to understand and contribute
- ✅ No client-specific dependencies
- ✅ Smaller bundle size

### For Client Fork

- ✅ Full access to all features
- ✅ Easy to sync upstream changes
- ✅ Client code isolated in specific branch
- ✅ No merge conflicts on shared files

### For Development Team

- ✅ Single pattern for all features
- ✅ Easy to add new client-specific handlers
- ✅ Clear separation of concerns
- ✅ Minimal code duplication

## Adding New Client-Specific Features

To add a new client-specific feature (e.g., custom reporting):

### 1. Create Handler

```python
# apps/api/src/domain/custom_report_handler.py
from .message_handlers import MessageHandler

class CustomReportHandler(MessageHandler):
    async def can_handle(self, context: ChatContext) -> bool:
        return context.message.startswith("Generar reporte:")

    async def process(self, context: ChatContext, **kwargs) -> ChatProcessingResult:
        # Implement custom report logic
        ...
```

### 2. Register in Chain (client branch only)

```python
# apps/api/src/domain/message_handlers.py (in client/capital414)
def create_handler_chain() -> MessageHandler:
    standard_handler = StandardChatHandler()

    # Chain: custom_report → audit → standard
    try:
        from .custom_report_handler import CustomReportHandler
        from .audit_handler import AuditCommandHandler

        audit = AuditCommandHandler(next_handler=standard_handler)
        return CustomReportHandler(next_handler=audit)
    except ImportError:
        return standard_handler
```

### 3. Add Feature Files

Create all necessary service/model/schema files in `client/capital414` branch only.

## Common Pitfalls

### Don't

- Hardcode client logic in `chat.py`
- Merge client branches to `main`
- Push client-specific files to upstream
- Use `--force` on shared branches

### Do

- Use handler chain for all message processing
- Keep client code in `client/capital414` branch
- Sync regularly from `upstream/main`
- Test both versions (with/without client features)
- Document all client-specific patterns

## Testing Strategy

### Open-Source Tests

```bash
# In main/develop branch
make test-api  # Should pass without audit system
```

### Client-Specific Tests

```bash
# In client/capital414 branch
make test-api  # Tests both base + audit features
make test-audit  # Tests only audit system
```

## Troubleshooting

### Issue: Merge conflicts on sync

```bash
# If chat.py has conflicts
git checkout develop
git merge upstream/main

# Conflicts in chat.py?
# Resolution: Keep handler chain approach, reject hardcoded logic
git checkout --ours apps/api/src/routers/chat.py
git add apps/api/src/routers/chat.py
git commit
```

### Issue: Handler not loading

```bash
# Check ImportError in logs
docker logs octavios-api 2>&1 | grep "audit handler"

# Should see:
# "Audit handler registered in chain" (client version)
# OR
# "Running open-source version" (main version)
```

### Issue: Client features in upstream PR

Before creating PR to upstream:

```bash
# Verify no client files
git diff main..upstream/main --name-only | grep -E "audit|validation_report|policy"

# Should return empty (no matches)
```

## Migration Path for Existing Code

If you have hardcoded client logic in `chat.py`:

1. **Create handler** in `apps/api/src/domain/custom_handler.py`
2. **Extract logic** from `chat.py` to handler's `process()` method
3. **Remove if/else** blocks from `chat.py`
4. **Use** `create_handler_chain()` in `chat.py`
5. **Test** both with and without handler present

## References

- [Design Patterns: Chain of Responsibility](https://refactoring.guru/design-patterns/chain-of-responsibility)
- [Git Fork Workflow](https://www.atlassian.com/git/tutorials/comparing-workflows/forking-workflow)
- [Feature Toggles](https://martinfowler.com/articles/feature-toggles.html)

---

**Last Updated**: 2025-11-10
**Authors**: Saptiva Engineering Team
**Status**: Active - This is the current architecture
