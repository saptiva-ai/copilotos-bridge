# SOLID Principles

> Applied examples for FastAPI + Next.js + MongoDB stack.

## Single Responsibility Principle (SRP)

**"A class should have only one reason to change."**

### ❌ Violation

```python
class ChatService:
    async def process_message(self, content: str) -> Message:
        # Validates input
        if not content.strip():
            raise ValueError("Empty message")

        # Logs analytics
        await self.db.log_analytics({"event": "message"})

        # Sends email notification
        await self.email_client.send_notification(...)

        # Generates response
        response = await self.llm.complete(content)

        # Saves to database
        await self.db.save(response)

        return response
```

### ✅ Correct

```python
# Each class has ONE responsibility
class MessageValidator:
    def validate(self, content: str) -> str:
        if not content.strip():
            raise ValueError("Empty message")
        return content.strip()

class AnalyticsService:
    async def log_event(self, event: dict) -> None:
        await self.db.log_analytics(event)

class NotificationService:
    async def notify(self, event: str, user_id: str) -> None:
        await self.email_client.send_notification(...)

class ChatService:
    """ONLY handles chat logic."""
    def __init__(
        self,
        validator: MessageValidator,
        llm: LLMClient,
        repository: MessageRepository,
    ):
        self._validator = validator
        self._llm = llm
        self._repo = repository

    async def process_message(self, content: str) -> Message:
        validated = self._validator.validate(content)
        response = await self._llm.complete(validated)
        return await self._repo.save(response)
```

## Open-Closed Principle (OCP)

**"Open for extension, closed for modification."**

### ❌ Violation

```python
class TokenProvider:
    def generate(self, provider: str, user: User) -> str:
        if provider == "jwt":
            return jwt.encode(...)
        elif provider == "opaque":
            return secrets.token_urlsafe(32)
        elif provider == "session":  # Adding new type = modify class
            return str(uuid.uuid4())
```

### ✅ Correct (Strategy Pattern)

```python
from typing import Protocol

class TokenStrategy(Protocol):
    def generate(self, user: User) -> str: ...

class JWTStrategy:
    def generate(self, user: User) -> str:
        return jwt.encode({"sub": user.id}, SECRET)

class OpaqueStrategy:
    def generate(self, user: User) -> str:
        return secrets.token_urlsafe(32)

class SessionStrategy:  # New strategy = new class, no modification
    def generate(self, user: User) -> str:
        return str(uuid.uuid4())

class TokenProvider:
    def __init__(self, strategy: TokenStrategy):
        self._strategy = strategy

    def generate(self, user: User) -> str:
        return self._strategy.generate(user)

# Usage - inject strategy
provider = TokenProvider(strategy=JWTStrategy())
```

## Liskov Substitution Principle (LSP)

**"Subtypes must be substitutable for their base types."**

### ❌ Violation

```python
class Bird:
    def fly(self) -> str:
        return "Flying"

class Penguin(Bird):
    def fly(self) -> str:
        raise NotImplementedError("Penguins can't fly")  # Breaks LSP!
```

### ✅ Correct

```python
class Bird:
    def move(self) -> str:
        raise NotImplementedError

class FlyingBird(Bird):
    def move(self) -> str:
        return "Flying"

class SwimmingBird(Bird):
    def move(self) -> str:
        return "Swimming"

class Penguin(SwimmingBird):
    pass  # Substitutable for SwimmingBird

# Or use composition
class Bird:
    def __init__(self, locomotion: Locomotion):
        self._locomotion = locomotion

    def move(self) -> str:
        return self._locomotion.move()
```

## Interface Segregation Principle (ISP)

**"Clients should not depend on interfaces they don't use."**

### ❌ Violation

```python
class Repository(Protocol):
    async def find_by_id(self, id: str) -> Model: ...
    async def find_all(self) -> list[Model]: ...
    async def save(self, model: Model) -> Model: ...
    async def delete(self, id: str) -> None: ...
    async def bulk_insert(self, models: list[Model]) -> None: ...  # Not all need this
    async def aggregate(self, pipeline: dict) -> list: ...  # Not all need this
```

### ✅ Correct

```python
class ReadRepository(Protocol):
    async def find_by_id(self, id: str) -> Model: ...
    async def find_all(self) -> list[Model]: ...

class WriteRepository(Protocol):
    async def save(self, model: Model) -> Model: ...
    async def delete(self, id: str) -> None: ...

class BulkRepository(Protocol):
    async def bulk_insert(self, models: list[Model]) -> None: ...

class AggregateRepository(Protocol):
    async def aggregate(self, pipeline: dict) -> list: ...

# Service only depends on what it needs
class ReadOnlyService:
    def __init__(self, repo: ReadRepository):  # Only read operations
        self._repo = repo
```

## Dependency Inversion Principle (DIP)

**"Depend on abstractions, not concretions."**

### ❌ Violation

```python
class ChatService:
    def __init__(self):
        self.llm = SaptivaClient()  # Concrete dependency
        self.db = MongoDB()  # Concrete dependency
```

### ✅ Correct

```python
from typing import Protocol

# Abstract interfaces
class LLMClient(Protocol):
    async def complete(self, prompt: str) -> str: ...

class Database(Protocol):
    async def save(self, data: dict) -> None: ...
    async def find(self, query: dict) -> list: ...

# Service depends on abstractions
class ChatService:
    def __init__(
        self,
        llm: LLMClient,  # Injected abstraction
        db: Database,    # Injected abstraction
    ):
        self._llm = llm
        self._db = db

# Dependency injection in FastAPI
async def get_chat_service(
    llm: LLMClient = Depends(get_saptiva_client),
    db: Database = Depends(get_mongodb),
) -> ChatService:
    return ChatService(llm=llm, db=db)
```

## SOLID Checklist for Code Review

| Principle | Question | If No |
|-----------|----------|-------|
| **SRP** | Does this class/function have only ONE reason to change? | Split responsibilities |
| **OCP** | Can I add new behavior without modifying existing code? | Introduce abstractions |
| **LSP** | Can I substitute any subclass for its parent? | Fix inheritance or use composition |
| **ISP** | Does this interface have methods all clients use? | Split into smaller interfaces |
| **DIP** | Am I depending on abstractions, not concretions? | Inject interfaces |

## Quick Smell Detection

| Smell | Likely Violation | Fix |
|-------|-----------------|-----|
| Class > 200 lines | SRP | Extract classes |
| Method > 20 lines | SRP | Extract methods |
| `if/elif` chains | OCP | Strategy pattern |
| `isinstance` checks | LSP | Fix type hierarchy |
| Fat interfaces | ISP | Split protocols |
| `import ConcreteClass` in service | DIP | Inject protocol |
