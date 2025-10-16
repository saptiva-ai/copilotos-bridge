"""
Unit tests for FileMetadata typed model and validation

Tests the new typed metadata system that replaces Dict[str, Any]
with explicit Pydantic models for type safety and BSON compatibility.

Test Coverage:
- FileMetadata Pydantic validation (success and failure cases)
- ChatMessage model with explicit files field
- add_user_message with typed file metadata
- BSON serialization compatibility
- Graceful degradation when validation fails
- Backwards compatibility with legacy metadata
- Schema version tracking
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime
from pydantic import ValidationError
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'src'))

from models.chat import FileMetadata, ChatMessage, MessageRole, ChatSession
from services.chat_service import ChatService
from core.config import Settings


@pytest.mark.unit
class TestFileMetadataModel:
    """Test FileMetadata Pydantic model validation"""

    def test_valid_file_metadata_pdf(self):
        """Should validate complete PDF metadata"""
        file_meta = FileMetadata(
            file_id="68efdd89b60a74cfc6c79a3c",
            filename="document.pdf",
            bytes=1024000,
            pages=10,
            mimetype="application/pdf"
        )

        assert file_meta.file_id == "68efdd89b60a74cfc6c79a3c"
        assert file_meta.filename == "document.pdf"
        assert file_meta.bytes == 1024000
        assert file_meta.pages == 10
        assert file_meta.mimetype == "application/pdf"

    def test_valid_file_metadata_image(self):
        """Should validate image metadata without pages field"""
        file_meta = FileMetadata(
            file_id="abc123",
            filename="photo.jpg",
            bytes=512000,
            mimetype="image/jpeg"
        )

        assert file_meta.file_id == "abc123"
        assert file_meta.filename == "photo.jpg"
        assert file_meta.bytes == 512000
        assert file_meta.pages is None  # Optional for images
        assert file_meta.mimetype == "image/jpeg"

    def test_missing_required_field_filename(self):
        """Should fail validation when filename is missing"""
        with pytest.raises(ValidationError) as exc_info:
            FileMetadata(
                file_id="abc123",
                # filename missing
                bytes=1024,
                mimetype="application/pdf"
            )

        errors = exc_info.value.errors()
        assert any(e['loc'] == ('filename',) for e in errors)
        assert any(e['type'] == 'missing' for e in errors)

    def test_missing_required_field_bytes(self):
        """Should fail validation when bytes is missing"""
        with pytest.raises(ValidationError) as exc_info:
            FileMetadata(
                file_id="abc123",
                filename="test.pdf"
                # bytes missing
            )

        errors = exc_info.value.errors()
        assert any(e['loc'] == ('bytes',) for e in errors)

    def test_invalid_type_for_bytes(self):
        """Should fail validation when bytes is not an integer"""
        with pytest.raises(ValidationError) as exc_info:
            FileMetadata(
                file_id="abc123",
                filename="test.pdf",
                bytes="not-a-number",  # Invalid type
                mimetype="application/pdf"
            )

        errors = exc_info.value.errors()
        assert any('bytes' in str(e['loc']) for e in errors)

    def test_optional_fields_can_be_none(self):
        """Should allow pages and mimetype to be None"""
        file_meta = FileMetadata(
            file_id="abc123",
            filename="test.txt",
            bytes=100
            # pages and mimetype not provided
        )

        assert file_meta.pages is None
        assert file_meta.mimetype is None

    def test_serializes_to_dict_correctly(self):
        """Should serialize to dict for MongoDB storage"""
        file_meta = FileMetadata(
            file_id="68efdd89b60a74cfc6c79a3c",
            filename="doc.pdf",
            bytes=2048,
            pages=5,
            mimetype="application/pdf"
        )

        dict_repr = file_meta.model_dump()

        assert isinstance(dict_repr, dict)
        assert dict_repr["file_id"] == "68efdd89b60a74cfc6c79a3c"
        assert dict_repr["filename"] == "doc.pdf"
        assert dict_repr["bytes"] == 2048
        assert dict_repr["pages"] == 5
        assert dict_repr["mimetype"] == "application/pdf"

    def test_model_validate_from_dict(self):
        """Should validate from dictionary (common API input)"""
        raw_dict = {
            "file_id": "68efdd89b60a74cfc6c79a3c",
            "filename": "uploaded.pdf",
            "bytes": 7639221,
            "pages": 76,
            "mimetype": "application/pdf"
        }

        file_meta = FileMetadata.model_validate(raw_dict)

        assert file_meta.file_id == "68efdd89b60a74cfc6c79a3c"
        assert file_meta.filename == "uploaded.pdf"
        assert file_meta.bytes == 7639221
        assert file_meta.pages == 76


@pytest.mark.unit
class TestChatMessageWithFiles:
    """Test ChatMessage model with explicit files field"""

    def test_create_message_with_files_field(self):
        """Should create ChatMessage with explicit files list"""
        files = [
            FileMetadata(
                file_id="file-1",
                filename="doc1.pdf",
                bytes=1024,
                pages=2,
                mimetype="application/pdf"
            ),
            FileMetadata(
                file_id="file-2",
                filename="doc2.pdf",
                bytes=2048,
                pages=5,
                mimetype="application/pdf"
            )
        ]

        message = ChatMessage(
            chat_id="chat-123",
            role=MessageRole.USER,
            content="Analyze these documents",
            file_ids=["file-1", "file-2"],
            files=files,
            schema_version=2
        )

        assert len(message.files) == 2
        assert len(message.file_ids) == 2
        assert message.files[0].filename == "doc1.pdf"
        assert message.files[1].filename == "doc2.pdf"
        assert message.schema_version == 2

    def test_default_values_for_files_field(self):
        """Should have empty lists as default for files and file_ids"""
        message = ChatMessage(
            chat_id="chat-123",
            role=MessageRole.USER,
            content="Simple message"
        )

        assert message.file_ids == []
        assert message.files == []
        assert message.schema_version == 2  # Default schema version

    def test_backwards_compatible_with_legacy_metadata(self):
        """Should still support legacy metadata field"""
        message = ChatMessage(
            chat_id="chat-123",
            role=MessageRole.USER,
            content="Message",
            metadata={"source": "api", "legacy_field": "value"}
        )

        assert message.metadata is not None
        assert message.metadata["source"] == "api"
        assert message.metadata["legacy_field"] == "value"
        # New fields should have defaults
        assert message.files == []
        assert message.file_ids == []

    def test_message_with_both_files_and_legacy_metadata(self):
        """Should support both new files field and legacy metadata"""
        files = [
            FileMetadata(
                file_id="file-1",
                filename="doc.pdf",
                bytes=1024,
                pages=1,
                mimetype="application/pdf"
            )
        ]

        message = ChatMessage(
            chat_id="chat-123",
            role=MessageRole.USER,
            content="Message",
            file_ids=["file-1"],
            files=files,
            metadata={"source": "api", "additional_info": "value"}
        )

        # Both should coexist
        assert len(message.files) == 1
        assert message.files[0].filename == "doc.pdf"
        assert message.metadata["source"] == "api"
        assert message.metadata["additional_info"] == "value"


@pytest.mark.unit
class TestAddUserMessageWithTypedMetadata:
    """Test add_user_message with typed file metadata validation"""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings"""
        settings = Mock(spec=Settings)
        settings.saptiva_base_url = "https://api.test.com"
        settings.saptiva_api_key = "test-key"
        return settings

    @pytest.fixture
    def chat_service(self, mock_settings):
        """Create ChatService instance"""
        return ChatService(mock_settings)

    @pytest.fixture
    def mock_chat_session(self):
        """Create mock chat session"""
        session = AsyncMock(spec=ChatSession)
        session.id = "chat-123"
        session.user_id = "user-123"
        session.message_count = 0
        session.save = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_add_user_message_with_valid_files(self, chat_service, mock_chat_session):
        """Should successfully add user message with validated files"""
        metadata = {
            "file_ids": ["file-1", "file-2"],
            "files": [
                {
                    "file_id": "file-1",
                    "filename": "doc1.pdf",
                    "bytes": 1024,
                    "pages": 2,
                    "mimetype": "application/pdf"
                },
                {
                    "file_id": "file-2",
                    "filename": "doc2.pdf",
                    "bytes": 2048,
                    "pages": 5,
                    "mimetype": "application/pdf"
                }
            ]
        }

        with patch('services.chat_service.get_redis_cache') as mock_get_cache, \
             patch('services.chat_service.ChatMessageModel') as MockChatMessage:

            # Mock cache
            mock_cache = AsyncMock()
            mock_cache.invalidate_chat_history = AsyncMock()
            mock_get_cache.return_value = mock_cache

            # Mock message creation
            mock_message = AsyncMock()
            mock_message.id = "msg-123"
            mock_message.insert = AsyncMock()
            MockChatMessage.return_value = mock_message

            result = await chat_service.add_user_message(
                chat_session=mock_chat_session,
                content="Analyze these",
                metadata=metadata
            )

            # Should create message with validated FileMetadata models
            MockChatMessage.assert_called_once()
            call_args = MockChatMessage.call_args.kwargs

            assert call_args["chat_id"] == "chat-123"
            assert call_args["role"] == MessageRole.USER
            assert call_args["content"] == "Analyze these"
            assert len(call_args["file_ids"]) == 2
            assert len(call_args["files"]) == 2
            assert isinstance(call_args["files"][0], FileMetadata)
            assert call_args["files"][0].filename == "doc1.pdf"
            assert call_args["schema_version"] == 2

            # Should insert message
            mock_message.insert.assert_called_once()

            # Should invalidate cache
            mock_cache.invalidate_chat_history.assert_called_once_with("chat-123")

    @pytest.mark.asyncio
    async def test_add_user_message_with_invalid_files_falls_back(self, chat_service, mock_chat_session):
        """Should fall back to file_ids only when file validation fails"""
        metadata = {
            "file_ids": ["file-1", "file-2"],
            "files": [
                {
                    "file_id": "file-1",
                    # filename missing - invalid!
                    "bytes": 1024,
                    "mimetype": "application/pdf"
                }
            ]
        }

        with patch('services.chat_service.get_redis_cache') as mock_get_cache, \
             patch('services.chat_service.ChatMessageModel') as MockChatMessage:

            mock_cache = AsyncMock()
            mock_cache.invalidate_chat_history = AsyncMock()
            mock_get_cache.return_value = mock_cache

            mock_message = AsyncMock()
            mock_message.id = "msg-123"
            mock_message.insert = AsyncMock()
            MockChatMessage.return_value = mock_message

            result = await chat_service.add_user_message(
                chat_session=mock_chat_session,
                content="Message",
                metadata=metadata
            )

            # Should create message but files list should be empty (fallback)
            call_args = MockChatMessage.call_args.kwargs
            assert len(call_args["file_ids"]) == 2  # file_ids preserved
            assert call_args["files"] == []  # files validation failed, empty list

    @pytest.mark.asyncio
    async def test_add_user_message_without_metadata(self, chat_service, mock_chat_session):
        """Should handle messages without any metadata"""
        with patch('services.chat_service.get_redis_cache') as mock_get_cache, \
             patch('services.chat_service.ChatMessageModel') as MockChatMessage:

            mock_cache = AsyncMock()
            mock_cache.invalidate_chat_history = AsyncMock()
            mock_get_cache.return_value = mock_cache

            mock_message = AsyncMock()
            mock_message.id = "msg-123"
            mock_message.insert = AsyncMock()
            MockChatMessage.return_value = mock_message

            result = await chat_service.add_user_message(
                chat_session=mock_chat_session,
                content="Simple message",
                metadata=None
            )

            # Should create message with empty files
            call_args = MockChatMessage.call_args.kwargs
            assert call_args["file_ids"] == []
            assert call_args["files"] == []
            assert call_args["schema_version"] == 2

    @pytest.mark.asyncio
    async def test_bson_serialization_check(self, chat_service, mock_chat_session):
        """Should verify BSON serialization before MongoDB insertion"""
        metadata = {
            "file_ids": ["file-1"],
            "files": [
                {
                    "file_id": "file-1",
                    "filename": "doc.pdf",
                    "bytes": 1024,
                    "pages": 1,
                    "mimetype": "application/pdf"
                }
            ]
        }

        with patch('services.chat_service.get_redis_cache') as mock_get_cache, \
             patch('services.chat_service.ChatMessageModel') as MockChatMessage, \
             patch('services.chat_service.jsonable_encoder') as mock_encoder:

            mock_cache = AsyncMock()
            mock_cache.invalidate_chat_history = AsyncMock()
            mock_get_cache.return_value = mock_cache

            mock_message = AsyncMock()
            mock_message.id = "msg-123"
            mock_message.insert = AsyncMock()
            MockChatMessage.return_value = mock_message

            # jsonable_encoder should be called to verify serialization
            mock_encoder.return_value = {"_id": "msg-123", "content": "test"}

            result = await chat_service.add_user_message(
                chat_session=mock_chat_session,
                content="Test",
                metadata=metadata
            )

            # Should call jsonable_encoder to test BSON compatibility
            mock_encoder.assert_called_once()
            encoder_args = mock_encoder.call_args
            assert encoder_args.kwargs.get("by_alias") is True

    @pytest.mark.asyncio
    async def test_updates_session_stats(self, chat_service, mock_chat_session):
        """Should update session message_count and timestamps"""
        with patch('services.chat_service.get_redis_cache') as mock_get_cache, \
             patch('services.chat_service.ChatMessageModel') as MockChatMessage:

            mock_cache = AsyncMock()
            mock_cache.invalidate_chat_history = AsyncMock()
            mock_get_cache.return_value = mock_cache

            mock_message = AsyncMock()
            mock_message.id = "msg-123"
            mock_message.insert = AsyncMock()
            MockChatMessage.return_value = mock_message

            # Initial message count
            assert mock_chat_session.message_count == 0

            await chat_service.add_user_message(
                chat_session=mock_chat_session,
                content="Test",
                metadata=None
            )

            # Should update session stats
            assert mock_chat_session.message_count == 1
            mock_chat_session.save.assert_called_once()


@pytest.mark.unit
class TestFileMetadataIntegration:
    """Integration tests for complete file metadata flow"""

    def test_json_serialization_roundtrip(self):
        """Should serialize to JSON and deserialize correctly"""
        import json

        original = FileMetadata(
            file_id="68efdd89b60a74cfc6c79a3c",
            filename="tipografia_esp.pdf",
            bytes=7639221,
            pages=76,
            mimetype="application/pdf"
        )

        # Serialize to JSON
        json_str = json.dumps(original.model_dump())

        # Deserialize from JSON
        parsed_dict = json.loads(json_str)
        restored = FileMetadata.model_validate(parsed_dict)

        # Should match original
        assert restored.file_id == original.file_id
        assert restored.filename == original.filename
        assert restored.bytes == original.bytes
        assert restored.pages == original.pages
        assert restored.mimetype == original.mimetype

    def test_multiple_files_in_message(self):
        """Should handle multiple files in a single message"""
        files = [
            FileMetadata(
                file_id=f"file-{i}",
                filename=f"doc{i}.pdf",
                bytes=1024 * i,
                pages=i,
                mimetype="application/pdf"
            )
            for i in range(1, 6)  # 5 files
        ]

        message = ChatMessage(
            chat_id="chat-123",
            role=MessageRole.USER,
            content="Analyze all these",
            file_ids=[f"file-{i}" for i in range(1, 6)],
            files=files,
            schema_version=2
        )

        assert len(message.files) == 5
        assert len(message.file_ids) == 5
        for i, file_meta in enumerate(message.files, start=1):
            assert file_meta.filename == f"doc{i}.pdf"
            assert file_meta.bytes == 1024 * i
            assert file_meta.pages == i

    def test_schema_version_tracking(self):
        """Should track schema version for migrations"""
        # New message (schema v2)
        new_message = ChatMessage(
            chat_id="chat-123",
            role=MessageRole.USER,
            content="Test",
            files=[],
            file_ids=[]
        )

        assert new_message.schema_version == 2

        # Legacy message (could have schema_version=1 or None)
        legacy_message = ChatMessage(
            chat_id="chat-123",
            role=MessageRole.USER,
            content="Legacy",
            metadata={"file_ids": ["old-file"]}
        )

        # Even legacy messages get default schema_version=2
        assert legacy_message.schema_version == 2
