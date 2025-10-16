"""
Unit tests for ChatService - Business Logic Layer

Tests the chat service methods independently from HTTP layer.
Uses mocks for all external dependencies.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'src'))

from services.chat_service import ChatService
from models.chat import ChatSession, ChatMessage, MessageRole, MessageStatus
from core.config import Settings


@pytest.fixture
def mock_settings():
    """Create mock settings"""
    settings = Mock(spec=Settings)
    settings.saptiva_base_url = "https://api.test.com"
    settings.saptiva_api_key = "test-key"
    return settings


@pytest.fixture
def chat_service(mock_settings):
    """Create ChatService instance with mocked settings"""
    return ChatService(mock_settings)


@pytest.fixture
def mock_chat_session():
    """Create a mock chat session"""
    session = AsyncMock(spec=ChatSession)
    session.id = "test-chat-id"
    session.user_id = "test-user"
    session.title = "Test Chat"
    session.tools_enabled = {"web_search": True}
    session.created_at = datetime.utcnow()
    session.updated_at = datetime.utcnow()
    session.message_count = 0
    session.add_message = AsyncMock(return_value=AsyncMock(spec=ChatMessage))
    return session


@pytest.mark.unit
class TestGetOrCreateSession:
    """Test get_or_create_session method"""

    @pytest.mark.asyncio
    async def test_creates_new_session_when_chat_id_is_none(self, chat_service):
        """Should create new session when chat_id is not provided"""
        with patch('services.chat_service.ChatSessionModel') as MockChatSession:
            mock_instance = AsyncMock()
            mock_instance.id = "new-chat-id"
            mock_instance.insert = AsyncMock()
            MockChatSession.return_value = mock_instance

            result = await chat_service.get_or_create_session(
                chat_id=None,
                user_id="user-123",
                first_message="Hello, world!",
                tools_enabled={"web_search": True}
            )

            # Should create new session
            MockChatSession.assert_called_once()
            mock_instance.insert.assert_called_once()
            assert result == mock_instance

    @pytest.mark.asyncio
    async def test_truncates_long_title(self, chat_service):
        """Should truncate title to 50 chars + '...'"""
        long_message = "a" * 100

        with patch('services.chat_service.ChatSessionModel') as MockChatSession:
            mock_instance = AsyncMock()
            mock_instance.insert = AsyncMock()
            MockChatSession.return_value = mock_instance

            await chat_service.get_or_create_session(
                chat_id=None,
                user_id="user-123",
                first_message=long_message,
                tools_enabled={}
            )

            # Check that title was truncated
            call_args = MockChatSession.call_args
            assert len(call_args.kwargs['title']) == 53  # 50 + "..."
            assert call_args.kwargs['title'].endswith("...")

    @pytest.mark.asyncio
    async def test_retrieves_existing_session(self, chat_service, mock_chat_session):
        """Should retrieve existing session when chat_id is provided"""
        with patch('services.chat_service.ChatSessionModel') as MockChatSession:
            MockChatSession.get = AsyncMock(return_value=mock_chat_session)

            result = await chat_service.get_or_create_session(
                chat_id="test-chat-id",
                user_id="test-user",
                first_message="New message",
                tools_enabled={"web_search": True}
            )

            MockChatSession.get.assert_called_once_with("test-chat-id")
            assert result == mock_chat_session

    @pytest.mark.asyncio
    async def test_raises_404_when_session_not_found(self, chat_service):
        """Should raise HTTPException 404 when session doesn't exist"""
        from fastapi import HTTPException

        with patch('services.chat_service.ChatSessionModel') as MockChatSession:
            MockChatSession.get = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await chat_service.get_or_create_session(
                    chat_id="nonexistent-id",
                    user_id="user-123",
                    first_message="Message",
                    tools_enabled={}
                )

            assert exc_info.value.status_code == 404
            assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_raises_403_when_user_unauthorized(self, chat_service, mock_chat_session):
        """Should raise HTTPException 403 when user doesn't own session"""
        from fastapi import HTTPException

        mock_chat_session.user_id = "other-user"

        with patch('services.chat_service.ChatSessionModel') as MockChatSession:
            MockChatSession.get = AsyncMock(return_value=mock_chat_session)

            with pytest.raises(HTTPException) as exc_info:
                await chat_service.get_or_create_session(
                    chat_id="test-chat-id",
                    user_id="current-user",
                    first_message="Message",
                    tools_enabled={}
                )

            assert exc_info.value.status_code == 403
            assert "access denied" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_updates_tools_when_changed(self, chat_service, mock_chat_session):
        """Should update tools_enabled when they differ from existing"""
        mock_chat_session.tools_enabled = {"web_search": False}
        mock_chat_session.update = AsyncMock()

        with patch('services.chat_service.ChatSessionModel') as MockChatSession:
            MockChatSession.get = AsyncMock(return_value=mock_chat_session)

            await chat_service.get_or_create_session(
                chat_id="test-chat-id",
                user_id="test-user",
                first_message="Message",
                tools_enabled={"web_search": True, "deep_research": False}
            )

            # Should update the session
            mock_chat_session.update.assert_called_once()
            update_call = mock_chat_session.update.call_args
            assert "$set" in update_call[0][0]
            assert "tools_enabled" in update_call[0][0]["$set"]


@pytest.mark.unit
class TestBuildMessageContext:
    """Test build_message_context method"""

    @pytest.mark.asyncio
    async def test_uses_provided_context(self, chat_service, mock_chat_session):
        """Should use provided context when available"""
        provided_context = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "First response"}
        ]

        result = await chat_service.build_message_context(
            chat_session=mock_chat_session,
            current_message="New message",
            provided_context=provided_context
        )

        assert len(result) == 3  # 2 from context + 1 current
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        assert result[2]["role"] == "user"
        assert result[2]["content"] == "New message"

    @pytest.mark.asyncio
    async def test_retrieves_recent_messages_from_db(self, chat_service, mock_chat_session):
        """Should retrieve recent messages when no context provided"""
        # Mock messages from database
        mock_messages = [
            AsyncMock(
                role=MessageRole.USER,
                content="Previous message",
                created_at=datetime.utcnow()
            ),
            AsyncMock(
                role=MessageRole.ASSISTANT,
                content="Previous response",
                created_at=datetime.utcnow()
            )
        ]

        with patch('services.chat_service.ChatMessageModel') as MockChatMessage:
            mock_find = AsyncMock()
            mock_find.sort = Mock(return_value=mock_find)
            mock_find.limit = Mock(return_value=mock_find)
            mock_find.to_list = AsyncMock(return_value=mock_messages)
            MockChatMessage.find = Mock(return_value=mock_find)

            result = await chat_service.build_message_context(
                chat_session=mock_chat_session,
                current_message="New message",
                provided_context=None
            )

            # Should retrieve from DB
            MockChatMessage.find.assert_called_once()
            assert len(result) == 3  # 2 from DB + 1 current

    @pytest.mark.asyncio
    async def test_limits_to_10_messages(self, chat_service, mock_chat_session):
        """Should limit retrieval to 10 recent messages"""
        with patch('services.chat_service.ChatMessageModel') as MockChatMessage:
            mock_find = AsyncMock()
            mock_find.sort = Mock(return_value=mock_find)
            mock_find.limit = Mock(return_value=mock_find)
            mock_find.to_list = AsyncMock(return_value=[])
            MockChatMessage.find = Mock(return_value=mock_find)

            await chat_service.build_message_context(
                chat_session=mock_chat_session,
                current_message="Message",
                provided_context=None
            )

            # Should limit to 10
            mock_find.limit.assert_called_once_with(10)


@pytest.mark.unit
class TestProcessWithSaptiva:
    """Test process_with_saptiva method"""

    @pytest.mark.asyncio
    async def test_builds_payload_and_calls_saptiva(self, chat_service):
        """Should build payload and call Saptiva client"""
        with patch('services.chat_service.build_payload') as mock_build_payload, \
             patch('services.chat_service.trace_span'), \
             patch.object(chat_service.saptiva_client, 'chat_completion', new_callable=AsyncMock) as mock_completion:

            mock_build_payload.return_value = (
                {
                    "messages": [{"role": "user", "content": "Hello"}],
                    "temperature": 0.7,
                    "max_tokens": 1024
                },
                {"request_id": "req-123", "system_hash": "hash"}
            )
            mock_completion.return_value = "AI response"

            result = await chat_service.process_with_saptiva(
                message="Hello",
                model="Saptiva Turbo",
                user_id="user-123",
                chat_id="chat-123",
                tools_enabled={"web_search": True}
            )

            # Should call build_payload
            mock_build_payload.assert_called_once()
            assert mock_build_payload.call_args.kwargs["model"] == "Saptiva Turbo"

            # Should call Saptiva
            mock_completion.assert_called_once()

            # Should return coordinated response format
            assert result["type"] == "chat"
            assert result["response"] == "AI response"
            assert "decision" in result
            assert "processing_time_ms" in result


@pytest.mark.unit
class TestAddMessages:
    """Test add_user_message and add_assistant_message methods"""

    @pytest.mark.asyncio
    async def test_add_user_message(self, chat_service, mock_chat_session):
        """Should add user message and invalidate cache"""
        mock_message = AsyncMock(spec=ChatMessage)
        mock_message.id = "msg-123"
        mock_chat_session.add_message = AsyncMock(return_value=mock_message)

        with patch('services.chat_service.get_redis_cache') as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.invalidate_chat_history = AsyncMock()
            mock_get_cache.return_value = mock_cache

            result = await chat_service.add_user_message(
                chat_session=mock_chat_session,
                content="User message"
            )

            # Should add message
            mock_chat_session.add_message.assert_called_once_with(
                role=MessageRole.USER,
                content="User message",
                metadata={"source": "api"}
            )

            # Should invalidate cache
            mock_cache.invalidate_chat_history.assert_called_once_with(mock_chat_session.id)

            assert result == mock_message

    @pytest.mark.asyncio
    async def test_add_assistant_message(self, chat_service, mock_chat_session):
        """Should add assistant message with metadata"""
        mock_message = AsyncMock(spec=ChatMessage)
        mock_message.id = "msg-456"
        mock_chat_session.add_message = AsyncMock(return_value=mock_message)

        with patch('services.chat_service.get_redis_cache') as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.invalidate_chat_history = AsyncMock()
            mock_cache.invalidate_research_tasks = AsyncMock()
            mock_get_cache.return_value = mock_cache

            result = await chat_service.add_assistant_message(
                chat_session=mock_chat_session,
                content="AI response",
                model="Saptiva Turbo",
                task_id="task-789",
                metadata={"confidence": 0.95},
                tokens={"prompt": 100, "completion": 50},
                latency_ms=500
            )

            # Should add message with all metadata
            call_args = mock_chat_session.add_message.call_args
            assert call_args.kwargs["role"] == MessageRole.ASSISTANT
            assert call_args.kwargs["content"] == "AI response"
            assert call_args.kwargs["model"] == "Saptiva Turbo"
            assert call_args.kwargs["task_id"] == "task-789"
            assert call_args.kwargs["tokens"] == {"prompt": 100, "completion": 50}

            # Should invalidate both caches when task_id present
            mock_cache.invalidate_chat_history.assert_called_once()
            mock_cache.invalidate_research_tasks.assert_called_once()

            assert result == mock_message
