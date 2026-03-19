# Test Patterns

## Backend (pytest)

### Basic Unit Test

```python
import pytest
from unittest.mock import AsyncMock, patch

class TestChatService:
    """Tests for ChatService."""

    @pytest.fixture
    def mock_saptiva_client(self):
        """Mock SAPTIVA client."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_process_message_success(self, mock_saptiva_client):
        """Valid message returns response."""
        mock_saptiva_client.complete.return_value = "Response"
        result = await chat_service.process("Hello")
        assert result.content == "Response"
        mock_saptiva_client.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_empty_raises(self):
        """Empty message raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            await chat_service.process("")
```

### Testing FastAPI Endpoints

```python
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_chat_requires_auth(client):
    response = await client.post("/api/chat", json={"message": "hi"})
    assert response.status_code == 401
```

### Testing with MongoDB (Beanie)

```python
import pytest
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie
from src.models import User

@pytest.fixture
async def db():
    client = AsyncMongoMockClient()
    await init_beanie(
        database=client.test_db,
        document_models=[User]
    )
    yield client.test_db
    await client.close()

@pytest.mark.asyncio
async def test_create_user(db):
    user = User(email="test@example.com", name="Test")
    await user.insert()
    found = await User.find_one(User.email == "test@example.com")
    assert found is not None
    assert found.name == "Test"
```

### Parametrized Tests

```python
import pytest

@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("", ""),
    ("MiXeD", "MIXED"),
])
def test_uppercase(input, expected):
    assert input.upper() == expected

@pytest.mark.parametrize("status_code,is_error", [
    (200, False),
    (201, False),
    (400, True),
    (500, True),
])
def test_is_error_response(status_code, is_error):
    assert is_error_response(status_code) == is_error
```

## Frontend (Jest + RTL)

### Basic Component Test

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatMessage } from './ChatMessage';

describe('ChatMessage', () => {
  const mockMessage = {
    id: '1',
    content: 'Hello world',
    role: 'assistant'
  };

  it('renders message content', () => {
    render(<ChatMessage message={mockMessage} />);
    expect(screen.getByText('Hello world')).toBeInTheDocument();
  });

  it('calls onFeedback when thumbs up clicked', () => {
    const onFeedback = jest.fn();
    render(<ChatMessage message={mockMessage} onFeedback={onFeedback} />);
    fireEvent.click(screen.getByRole('button', { name: /thumbs up/i }));
    expect(onFeedback).toHaveBeenCalledWith('up');
  });
});
```

### Testing Async Components

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import { ChatList } from './ChatList';

// Mock fetch
global.fetch = jest.fn();

describe('ChatList', () => {
  beforeEach(() => {
    (fetch as jest.Mock).mockClear();
  });

  it('displays loading state initially', () => {
    (fetch as jest.Mock).mockImplementation(() => new Promise(() => {}));
    render(<ChatList />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('displays messages after fetch', async () => {
    (fetch as jest.Mock).mockResolvedValue({
      json: () => Promise.resolve([{ id: '1', content: 'Hello' }])
    });

    render(<ChatList />);

    await waitFor(() => {
      expect(screen.getByText('Hello')).toBeInTheDocument();
    });
  });
});
```

### Testing Hooks

```typescript
import { renderHook, act } from '@testing-library/react';
import { useCounter } from './useCounter';

describe('useCounter', () => {
  it('initializes with default value', () => {
    const { result } = renderHook(() => useCounter());
    expect(result.current.count).toBe(0);
  });

  it('increments count', () => {
    const { result } = renderHook(() => useCounter());
    act(() => {
      result.current.increment();
    });
    expect(result.current.count).toBe(1);
  });
});
```

## E2E (Playwright)

### Basic E2E Test

```typescript
import { test, expect } from '@playwright/test';

test.describe('Login Flow', () => {
  test('user can login with valid credentials', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="email"]', 'user@example.com');
    await page.fill('[data-testid="password"]', 'password123');
    await page.click('[data-testid="submit"]');

    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('[data-testid="welcome"]')).toContainText('Welcome');
  });

  test('shows error for invalid password', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="email"]', 'user@example.com');
    await page.fill('[data-testid="password"]', 'wrong');
    await page.click('[data-testid="submit"]');

    await expect(page.locator('[data-testid="error"]')).toBeVisible();
  });
});
```

## Test Naming Convention

```python
# Pattern: test_<ca_id>_<what>_<condition>_<expected>
def test_ca01_login_with_valid_email_succeeds():
    ...

def test_ca02_login_with_invalid_password_shows_error():
    ...

def test_ca03_logout_clears_session():
    ...
```
