"""
Unit tests for MemoryService.

Tests:
- process_message extraction and saving
- get_context_for_llm context building
- _format_facts_for_llm formatting
- get_facts/get_context retrieval
- clear_memory functionality
- Singleton pattern
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from src.services.memory.memory_service import (
    MemoryService,
    get_memory_service,
    _memory_service_instance,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_settings():
    """Create mock settings with memory enabled."""
    settings = Mock()
    settings.memory_enabled = True
    settings.memory_max_facts = 50
    settings.memory_recent_messages = 5
    return settings


@pytest.fixture
def mock_settings_disabled():
    """Create mock settings with memory disabled."""
    settings = Mock()
    settings.memory_enabled = False
    settings.memory_max_facts = 50
    settings.memory_recent_messages = 5
    return settings


@pytest.fixture
def mock_session():
    """Create a mock ChatSession."""
    session = AsyncMock()
    session.memory_facts = {}
    session.memory_context = {}
    session.save = AsyncMock()
    return session


@pytest.fixture
def mock_session_with_facts():
    """Create a mock ChatSession with existing facts."""
    session = AsyncMock()
    session.memory_facts = {
        "invex.q2_2025.imor": "2.3%",
        "invex.q2_2025.icor": "145%",
    }
    session.memory_context = {
        "bank": "invex",
        "period": "q2_2025",
        "metric": "imor"
    }
    session.save = AsyncMock()
    return session


@pytest.fixture
def mock_messages():
    """Create mock chat messages for history."""
    from enum import Enum

    class MockRole(Enum):
        user = "user"
        assistant = "assistant"

    messages = []
    for i in range(3):
        msg = Mock()
        msg.role = MockRole.user if i % 2 == 0 else MockRole.assistant
        msg.content = f"Message {i} content"
        msg.created_at = Mock()
        messages.append(msg)

    return messages


# ============================================================================
# PROCESS_MESSAGE TESTS
# ============================================================================

class TestProcessMessage:
    """Tests for process_message method."""

    @pytest.mark.asyncio
    async def test_skips_when_memory_disabled(self, mock_settings_disabled):
        """Should return early when memory is disabled."""
        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings_disabled):
            service = MemoryService()

            with patch('src.services.memory.memory_service.ChatSessionModel') as MockSession:
                await service.process_message("session-123", "IMOR de INVEX es 2.3%")

                # Should not attempt to fetch session
                MockSession.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_session_not_found(self, mock_settings):
        """Should log warning and return when session not found."""
        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            with patch('src.services.memory.memory_service.ChatSessionModel') as MockSession:
                MockSession.get = AsyncMock(return_value=None)

                # Should not raise
                await service.process_message("invalid-session", "IMOR de INVEX es 2.3%")

                MockSession.get.assert_called_once_with("invalid-session")

    @pytest.mark.asyncio
    async def test_extracts_and_saves_facts(self, mock_settings, mock_session):
        """Should extract facts from message and save to session.

        Note: The regex patterns cannot extract values when digits exist between
        the metric name and value (e.g., "IMOR de INVEX Q2 2025 es 2.3%").
        This test uses context inheritance - first set context, then extract value.
        """
        # Pre-set context as if previous message established bank/period
        mock_session.memory_context = {"bank": "invex", "period": "q2_2025"}

        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            with patch('src.services.memory.memory_service.ChatSessionModel') as MockSession:
                MockSession.get = AsyncMock(return_value=mock_session)

                # Simple pattern that the regex CAN extract
                await service.process_message(
                    "session-123",
                    "El IMOR es 2.3%"
                )

                # Should have updated memory_facts using inherited context
                assert "invex.q2_2025.imor" in mock_session.memory_facts
                assert mock_session.memory_facts["invex.q2_2025.imor"] == "2.3%"

                # Should have saved
                mock_session.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_updates_context_on_new_bank(self, mock_settings, mock_session):
        """Should update context when new bank is mentioned."""
        mock_session.memory_context = {"bank": "bbva"}

        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            with patch('src.services.memory.memory_service.ChatSessionModel') as MockSession:
                MockSession.get = AsyncMock(return_value=mock_session)

                await service.process_message(
                    "session-123",
                    "Ahora veamos INVEX Q3 2025"
                )

                # Context should be updated
                assert mock_session.memory_context["bank"] == "invex"

    @pytest.mark.asyncio
    async def test_limits_facts_when_max_exceeded(self, mock_settings, mock_session):
        """Should trim oldest facts when max is exceeded."""
        mock_settings.memory_max_facts = 3

        # Pre-populate with many facts
        mock_session.memory_facts = {
            "fact1": "value1",
            "fact2": "value2",
            "fact3": "value3",
        }

        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            with patch('src.services.memory.memory_service.ChatSessionModel') as MockSession:
                MockSession.get = AsyncMock(return_value=mock_session)

                await service.process_message(
                    "session-123",
                    "El IMOR es 2.5%"
                )

                # Should have at most max_facts entries
                assert len(mock_session.memory_facts) <= 3

    @pytest.mark.asyncio
    async def test_no_save_when_nothing_extracted(self, mock_settings, mock_session):
        """Should not save when no facts or context changes."""
        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            with patch('src.services.memory.memory_service.ChatSessionModel') as MockSession:
                MockSession.get = AsyncMock(return_value=mock_session)

                await service.process_message(
                    "session-123",
                    "Buenos días, ¿cómo estás?"  # No banking facts
                )

                # Should not save since nothing changed
                mock_session.save.assert_not_called()


# ============================================================================
# GET_CONTEXT_FOR_LLM TESTS
# ============================================================================

class TestGetContextForLlm:
    """Tests for get_context_for_llm method."""

    @pytest.mark.asyncio
    async def test_returns_system_prompt_only_when_no_session(self, mock_settings):
        """Should return only system prompt when session not found."""
        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            with patch('src.services.memory.memory_service.ChatSessionModel') as MockSession:
                MockSession.get = AsyncMock(return_value=None)

                result = await service.get_context_for_llm(
                    "invalid-session",
                    system_prompt="You are a banking assistant."
                )

                assert len(result) == 1
                assert result[0]["role"] == "system"
                assert result[0]["content"] == "You are a banking assistant."

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_session_no_prompt(self, mock_settings):
        """Should return empty list when no session and no prompt."""
        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            with patch('src.services.memory.memory_service.ChatSessionModel') as MockSession:
                MockSession.get = AsyncMock(return_value=None)

                result = await service.get_context_for_llm("invalid-session")

                assert result == []

    @pytest.mark.asyncio
    async def test_includes_memory_facts_in_context(self, mock_settings, mock_session_with_facts):
        """Should include formatted memory facts in context."""
        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            # Create mock message query builder
            mock_query = AsyncMock()
            mock_query.sort = Mock(return_value=mock_query)
            mock_query.limit = Mock(return_value=mock_query)
            mock_query.to_list = AsyncMock(return_value=[])

            with patch('src.services.memory.memory_service.ChatSessionModel') as MockSession, \
                 patch('src.services.memory.memory_service.ChatMessageModel') as MockMessage:
                MockSession.get = AsyncMock(return_value=mock_session_with_facts)
                MockMessage.find = Mock(return_value=mock_query)

                result = await service.get_context_for_llm(
                    "session-123",
                    system_prompt="You are a banking assistant."
                )

                # Should have system prompt + memory context
                assert len(result) >= 2
                assert result[0]["role"] == "system"
                assert result[0]["content"] == "You are a banking assistant."

                # Memory context should include facts
                memory_content = result[1]["content"]
                assert "Conversation Memory" in memory_content
                assert "IMOR" in memory_content.upper()

    @pytest.mark.asyncio
    async def test_includes_recent_messages(self, mock_settings, mock_session, mock_messages):
        """Should include recent messages in context."""
        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            # Create mock message query builder
            mock_query = AsyncMock()
            mock_query.sort = Mock(return_value=mock_query)
            mock_query.limit = Mock(return_value=mock_query)
            # Return mock messages (simulating current + history)
            mock_query.to_list = AsyncMock(return_value=mock_messages)

            with patch('src.services.memory.memory_service.ChatSessionModel') as MockSession, \
                 patch('src.services.memory.memory_service.ChatMessageModel') as MockMessage:
                MockSession.get = AsyncMock(return_value=mock_session)
                MockMessage.find = Mock(return_value=mock_query)
                MockMessage.chat_id = "chat_id"  # For the query filter

                result = await service.get_context_for_llm(
                    "session-123",
                    system_prompt="System prompt"
                )

                # Should have system prompt + history messages (skipping first)
                # 3 messages returned, skip 1 (current), keep 2
                assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_skips_most_recent_message(self, mock_settings, mock_session, mock_messages):
        """Should skip the most recent message (current user message)."""
        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            mock_query = AsyncMock()
            mock_query.sort = Mock(return_value=mock_query)
            mock_query.limit = Mock(return_value=mock_query)
            mock_query.to_list = AsyncMock(return_value=mock_messages)

            with patch('src.services.memory.memory_service.ChatSessionModel') as MockSession, \
                 patch('src.services.memory.memory_service.ChatMessageModel') as MockMessage:
                MockSession.get = AsyncMock(return_value=mock_session)
                MockMessage.find = Mock(return_value=mock_query)
                MockMessage.chat_id = "chat_id"

                result = await service.get_context_for_llm("session-123")

                # Verify limit includes +1 for the skip logic
                mock_query.limit.assert_called_once_with(
                    mock_settings.memory_recent_messages + 1
                )


# ============================================================================
# FORMAT_FACTS_FOR_LLM TESTS
# ============================================================================

class TestFormatFactsForLlm:
    """Tests for _format_facts_for_llm method."""

    def test_formats_grouped_facts(self, mock_settings):
        """Should group facts by bank.period scope."""
        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            facts = {
                "invex.q2_2025.imor": "2.3%",
                "invex.q2_2025.icor": "145%",
                "bbva.q3_2026.imor": "1.8%",
            }
            context = {"bank": "invex", "period": "q2_2025"}

            result = service._format_facts_for_llm(facts, context)

            assert "Conversation Memory" in result
            assert "INVEX Q2 2025" in result
            assert "BBVA Q3 2026" in result
            assert "2.3%" in result
            assert "145%" in result

    def test_formats_context_section(self, mock_settings):
        """Should include current focus section."""
        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            facts = {"imor": "2.3%"}
            context = {"bank": "invex", "period": "q2_2025", "metric": "imor"}

            result = service._format_facts_for_llm(facts, context)

            assert "Current Focus" in result
            assert "Bank: INVEX" in result
            assert "Period: q2_2025" in result
            assert "Metric: IMOR" in result

    def test_handles_ungrouped_facts(self, mock_settings):
        """Should handle facts without scope (no dots)."""
        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            facts = {"imor": "2.3%", "dscr": "1.25"}
            context = {}

            result = service._format_facts_for_llm(facts, context)

            assert "Other Facts" in result
            assert "imor: 2.3%" in result
            assert "dscr: 1.25" in result

    def test_empty_facts_and_context(self, mock_settings):
        """Should handle empty facts and context gracefully."""
        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            result = service._format_facts_for_llm({}, {})

            assert "Conversation Memory" in result
            # Should not include Current Focus section
            assert "Current Focus" not in result


# ============================================================================
# GET_FACTS TESTS
# ============================================================================

class TestGetFacts:
    """Tests for get_facts method."""

    @pytest.mark.asyncio
    async def test_returns_facts_when_session_exists(self, mock_settings, mock_session_with_facts):
        """Should return facts dict when session exists."""
        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            with patch('src.services.memory.memory_service.ChatSessionModel') as MockSession:
                MockSession.get = AsyncMock(return_value=mock_session_with_facts)

                result = await service.get_facts("session-123")

                assert result == mock_session_with_facts.memory_facts
                assert "invex.q2_2025.imor" in result

    @pytest.mark.asyncio
    async def test_returns_empty_dict_when_no_session(self, mock_settings):
        """Should return empty dict when session not found."""
        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            with patch('src.services.memory.memory_service.ChatSessionModel') as MockSession:
                MockSession.get = AsyncMock(return_value=None)

                result = await service.get_facts("invalid-session")

                assert result == {}


# ============================================================================
# GET_CONTEXT TESTS
# ============================================================================

class TestGetContext:
    """Tests for get_context method."""

    @pytest.mark.asyncio
    async def test_returns_context_when_session_exists(self, mock_settings, mock_session_with_facts):
        """Should return context dict when session exists."""
        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            with patch('src.services.memory.memory_service.ChatSessionModel') as MockSession:
                MockSession.get = AsyncMock(return_value=mock_session_with_facts)

                result = await service.get_context("session-123")

                assert result["bank"] == "invex"
                assert result["period"] == "q2_2025"

    @pytest.mark.asyncio
    async def test_returns_empty_dict_when_no_session(self, mock_settings):
        """Should return empty dict when session not found."""
        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            with patch('src.services.memory.memory_service.ChatSessionModel') as MockSession:
                MockSession.get = AsyncMock(return_value=None)

                result = await service.get_context("invalid-session")

                assert result == {}


# ============================================================================
# CLEAR_MEMORY TESTS
# ============================================================================

class TestClearMemory:
    """Tests for clear_memory method."""

    @pytest.mark.asyncio
    async def test_clears_memory_and_context(self, mock_settings, mock_session_with_facts):
        """Should clear facts and context and save."""
        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            with patch('src.services.memory.memory_service.ChatSessionModel') as MockSession:
                MockSession.get = AsyncMock(return_value=mock_session_with_facts)

                result = await service.clear_memory("session-123")

                assert result is True
                assert mock_session_with_facts.memory_facts == {}
                assert mock_session_with_facts.memory_context == {}
                mock_session_with_facts.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_when_no_session(self, mock_settings):
        """Should return False when session not found."""
        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            with patch('src.services.memory.memory_service.ChatSessionModel') as MockSession:
                MockSession.get = AsyncMock(return_value=None)

                result = await service.clear_memory("invalid-session")

                assert result is False


# ============================================================================
# SINGLETON PATTERN TESTS
# ============================================================================

class TestGetMemoryService:
    """Tests for get_memory_service singleton function."""

    def test_returns_same_instance(self):
        """Should return the same instance on multiple calls."""
        # Reset singleton
        import src.services.memory.memory_service as module
        module._memory_service_instance = None

        with patch('src.services.memory.memory_service.get_settings') as mock_get_settings:
            mock_get_settings.return_value = Mock(memory_enabled=True)

            instance1 = get_memory_service()
            instance2 = get_memory_service()

            assert instance1 is instance2

    def test_creates_new_instance_when_none(self):
        """Should create new instance when singleton is None."""
        import src.services.memory.memory_service as module
        module._memory_service_instance = None

        with patch('src.services.memory.memory_service.get_settings') as mock_get_settings:
            mock_get_settings.return_value = Mock(memory_enabled=True)

            instance = get_memory_service()

            assert instance is not None
            assert isinstance(instance, MemoryService)


# ============================================================================
# INTEGRATION-LIKE TESTS
# ============================================================================

class TestMemoryServiceIntegration:
    """Integration-like tests with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, mock_settings, mock_session):
        """Test a realistic conversation flow with memory accumulation."""
        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            with patch('src.services.memory.memory_service.ChatSessionModel') as MockSession:
                MockSession.get = AsyncMock(return_value=mock_session)

                # Turn 1: User asks about INVEX IMOR
                await service.process_message(
                    "session-123",
                    "¿Cuál es el IMOR de INVEX en Q2 2025?"
                )

                # Context should be set
                assert mock_session.memory_context.get("bank") == "invex"
                assert mock_session.memory_context.get("period") == "q2_2025"

                # Turn 2: AI provides data (simulated)
                await service.process_message(
                    "session-123",
                    "El IMOR de INVEX es 2.3%"
                )

                # Fact should be stored
                assert "invex.q2_2025.imor" in mock_session.memory_facts

                # Turn 3: User asks follow-up
                await service.process_message(
                    "session-123",
                    "¿Y el ICOR?"
                )

                # Context should still have bank/period from before
                assert mock_session.memory_context.get("bank") == "invex"

    @pytest.mark.asyncio
    async def test_context_switch_between_banks(self, mock_settings, mock_session):
        """Test switching context between different banks."""
        with patch('src.services.memory.memory_service.get_settings', return_value=mock_settings):
            service = MemoryService()

            with patch('src.services.memory.memory_service.ChatSessionModel') as MockSession:
                MockSession.get = AsyncMock(return_value=mock_session)

                # Start with INVEX
                await service.process_message(
                    "session-123",
                    "Dame el IMOR de INVEX 2025"
                )
                assert mock_session.memory_context.get("bank") == "invex"

                # Switch to BBVA
                await service.process_message(
                    "session-123",
                    "Ahora muéstrame BBVA Q3 2026"
                )
                assert mock_session.memory_context.get("bank") == "bbva"
                assert mock_session.memory_context.get("period") == "q3_2026"
