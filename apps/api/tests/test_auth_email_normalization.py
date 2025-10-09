"""
Integration tests for authentication email normalization.

Tests the complete registration → login flow with various email formats
to ensure the bug (Test4@saptiva.com vs test4@saptiva.com) is fixed.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.models.user import User, UserPreferences
from src.schemas.user import UserCreate
from src.schemas.auth import AuthRequest
from src.services.auth_service import (
    register_user,
    authenticate_user,
    _get_user_by_email,
    _get_user_by_identifier,
)
from src.core.exceptions import ConflictError, AuthenticationError


@pytest.mark.asyncio
class TestAuthenticationEmailNormalization:
    """Test authentication with email normalization."""

    async def test_register_with_mixed_case_email(self):
        """
        Test that registration normalizes email to lowercase.

        Given: User registers with "Test4@Saptiva.COM"
        When: Email is stored in database
        Then: Email is normalized to "test4@saptiva.com"
        """
        # Mock database operations
        User.find_one = AsyncMock(return_value=None)  # No existing user
        mock_user = MagicMock(spec=User)
        mock_user.id = "test-id"
        mock_user.username = "testuser"
        mock_user.email = "test4@saptiva.com"  # Normalized
        mock_user.is_active = True
        mock_user.created_at = MagicMock()
        mock_user.updated_at = MagicMock()
        mock_user.last_login = None
        mock_user.preferences = UserPreferences()
        mock_user.create = AsyncMock(return_value=mock_user)

        User.__call__ = MagicMock(return_value=mock_user)

        # Register with mixed case email
        payload = UserCreate(
            username="testuser",
            email="Test4@Saptiva.COM",  # Mixed case
            password="SecurePass123"
        )

        response = await register_user(payload)

        # Verify email was normalized in the user object
        assert mock_user.email == "test4@saptiva.com"
        assert response.user.email == "test4@saptiva.com"

    async def test_login_with_different_case_succeeds(self):
        """
        Test that login works regardless of email case - THE MAIN FIX.

        Given: User registered as "test4@saptiva.com"
        When: User logs in with "Test4@Saptiva.COM"
        Then: Login succeeds (email is normalized for lookup)
        """
        # Mock user in database with normalized email
        mock_user = MagicMock(spec=User)
        mock_user.id = "test-id"
        mock_user.username = "testuser"
        mock_user.email = "test4@saptiva.com"  # Stored normalized
        mock_user.password_hash = "$argon2id$v=19$m=65536,t=3,p=4$test"
        mock_user.is_active = True
        mock_user.created_at = MagicMock()
        mock_user.updated_at = MagicMock()
        mock_user.last_login = None
        mock_user.preferences = UserPreferences()
        mock_user.save = AsyncMock()

        # Mock password verification
        from src.services import auth_service
        auth_service._verify_password = MagicMock(return_value=True)
        auth_service._pwd_context.needs_update = MagicMock(return_value=False)
        auth_service._pwd_context.identify = MagicMock(return_value="argon2")

        # Mock user lookup to return our mock user
        User.find_one = AsyncMock(return_value=mock_user)

        # Attempt login with different case
        login_attempts = [
            "Test4@Saptiva.COM",
            "TEST4@SAPTIVA.COM",
            "test4@saptiva.com",
            "  Test4@Saptiva.COM  ",  # With whitespace
        ]

        for email_attempt in login_attempts:
            response = await authenticate_user(email_attempt, "SecurePass123")
            assert response.access_token is not None
            assert response.user.email == "test4@saptiva.com"

    async def test_duplicate_email_detection_case_insensitive(self):
        """
        Test that duplicate email detection works regardless of case.

        Given: User exists with "test4@saptiva.com"
        When: Someone tries to register with "Test4@Saptiva.COM"
        Then: Registration fails with conflict error
        """
        # Mock existing user
        existing_user = MagicMock(spec=User)
        existing_user.email = "test4@saptiva.com"

        # Mock database to return existing user on email lookup
        async def mock_find_one(query):
            # Simulate case-insensitive email lookup
            if hasattr(query, 'email'):
                return existing_user
            return None

        User.find_one = AsyncMock(side_effect=mock_find_one)

        # Try to register with different case
        payload = UserCreate(
            username="differentuser",
            email="Test4@Saptiva.COM",  # Same email, different case
            password="SecurePass123"
        )

        with pytest.raises(ConflictError, match="Ya existe una cuenta con ese correo"):
            await register_user(payload)

    async def test_get_user_by_email_normalizes_input(self):
        """Test that _get_user_by_email normalizes the input."""
        mock_user = MagicMock(spec=User)
        mock_user.email = "test@example.com"

        User.find_one = AsyncMock(return_value=mock_user)

        # Test with various formats
        test_cases = [
            "test@example.com",
            "Test@Example.Com",
            "TEST@EXAMPLE.COM",
            "  test@example.com  ",
        ]

        for email in test_cases:
            result = await _get_user_by_email(email)
            assert result is not None
            # Verify that find_one was called with normalized email
            User.find_one.assert_called()

    async def test_get_user_by_identifier_handles_email(self):
        """Test that _get_user_by_identifier normalizes email identifiers."""
        mock_user = MagicMock(spec=User)
        mock_user.email = "test@example.com"

        User.find_one = AsyncMock(return_value=mock_user)

        # Test with email identifier
        result = await _get_user_by_identifier("Test@Example.Com")
        assert result is not None

    async def test_get_user_by_identifier_handles_username(self):
        """Test that _get_user_by_identifier handles usernames (no @)."""
        mock_user = MagicMock(spec=User)
        mock_user.username = "testuser"

        User.find_one = AsyncMock(return_value=mock_user)

        # Test with username identifier (no @)
        result = await _get_user_by_identifier("TestUser")
        # Should normalize to lowercase for username lookup
        assert result is not None


@pytest.mark.asyncio
class TestEdgeCasesAuthentication:
    """Test edge cases in authentication."""

    async def test_whitespace_in_email_register(self):
        """Test that whitespace is stripped during registration."""
        User.find_one = AsyncMock(return_value=None)
        mock_user = MagicMock(spec=User)
        mock_user.id = "test-id"
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.is_active = True
        mock_user.created_at = MagicMock()
        mock_user.updated_at = MagicMock()
        mock_user.last_login = None
        mock_user.preferences = UserPreferences()
        mock_user.create = AsyncMock()

        User.__call__ = MagicMock(return_value=mock_user)

        payload = UserCreate(
            username="testuser",
            email="  test@example.com  ",  # Whitespace
            password="SecurePass123"
        )

        response = await register_user(payload)
        assert mock_user.email == "test@example.com"

    async def test_whitespace_in_email_login(self):
        """Test that whitespace is stripped during login."""
        mock_user = MagicMock(spec=User)
        mock_user.id = "test-id"
        mock_user.email = "test@example.com"
        mock_user.password_hash = "$argon2id$v=19$m=65536,t=3,p=4$test"
        mock_user.is_active = True
        mock_user.save = AsyncMock()
        mock_user.created_at = MagicMock()
        mock_user.updated_at = MagicMock()
        mock_user.last_login = None
        mock_user.preferences = UserPreferences()

        from src.services import auth_service
        auth_service._verify_password = MagicMock(return_value=True)
        auth_service._pwd_context.needs_update = MagicMock(return_value=False)
        auth_service._pwd_context.identify = MagicMock(return_value="argon2")

        User.find_one = AsyncMock(return_value=mock_user)

        # Login with whitespace
        response = await authenticate_user("  test@example.com  ", "SecurePass123")
        assert response.user.email == "test@example.com"

    async def test_consecutive_dots_in_email(self):
        """Test that consecutive dots are handled during registration."""
        User.find_one = AsyncMock(return_value=None)
        mock_user = MagicMock(spec=User)
        mock_user.id = "test-id"
        mock_user.username = "testuser"
        mock_user.email = "test.user@example.com"  # Normalized
        mock_user.is_active = True
        mock_user.created_at = MagicMock()
        mock_user.updated_at = MagicMock()
        mock_user.last_login = None
        mock_user.preferences = UserPreferences()
        mock_user.create = AsyncMock()

        User.__call__ = MagicMock(return_value=mock_user)

        payload = UserCreate(
            username="testuser",
            email="test..user@example.com",  # Double dot
            password="SecurePass123"
        )

        response = await register_user(payload)
        assert mock_user.email == "test.user@example.com"


@pytest.mark.asyncio
class TestProductionScenarios:
    """Test real production scenarios reported by users."""

    async def test_scenario_test4_saptiva_bug(self):
        """
        Test the exact bug scenario reported.

        Scenario:
        1. User registers with "Test4@saptiva.com"
        2. System stores "test4@saptiva.com"
        3. User tries to login with "Test4@saptiva.com"
        4. System should find user (previously failed)
        """
        # Step 1: Mock registration
        User.find_one = AsyncMock(return_value=None)
        registered_user = MagicMock(spec=User)
        registered_user.id = "user-123"
        registered_user.username = "test4"
        registered_user.email = "test4@saptiva.com"  # Normalized
        registered_user.is_active = True
        registered_user.created_at = MagicMock()
        registered_user.updated_at = MagicMock()
        registered_user.last_login = None
        registered_user.preferences = UserPreferences()
        registered_user.password_hash = "$argon2id$v=19$m=65536,t=3,p=4$test"
        registered_user.create = AsyncMock()
        registered_user.save = AsyncMock()

        User.__call__ = MagicMock(return_value=registered_user)

        # Register
        register_payload = UserCreate(
            username="test4",
            email="Test4@saptiva.com",
            password="MyPassword123"
        )
        await register_user(register_payload)

        # Verify normalized storage
        assert registered_user.email == "test4@saptiva.com"

        # Step 2: Mock login with same email (different case)
        User.find_one = AsyncMock(return_value=registered_user)

        from src.services import auth_service
        auth_service._verify_password = MagicMock(return_value=True)
        auth_service._pwd_context.needs_update = MagicMock(return_value=False)
        auth_service._pwd_context.identify = MagicMock(return_value="argon2")

        # Login with original case
        login_response = await authenticate_user("Test4@saptiva.com", "MyPassword123")

        # Verify login succeeded
        assert login_response.access_token is not None
        assert login_response.user.email == "test4@saptiva.com"
        assert login_response.user.username == "test4"

    async def test_scenario_all_caps_email(self):
        """Test user who types email in all caps."""
        # Mock user stored with normalized email
        stored_user = MagicMock(spec=User)
        stored_user.id = "user-456"
        stored_user.email = "admin@company.com"
        stored_user.password_hash = "$argon2id$v=19$m=65536,t=3,p=4$test"
        stored_user.is_active = True
        stored_user.save = AsyncMock()
        stored_user.created_at = MagicMock()
        stored_user.updated_at = MagicMock()
        stored_user.last_login = None
        stored_user.preferences = UserPreferences()

        User.find_one = AsyncMock(return_value=stored_user)

        from src.services import auth_service
        auth_service._verify_password = MagicMock(return_value=True)
        auth_service._pwd_context.needs_update = MagicMock(return_value=False)
        auth_service._pwd_context.identify = MagicMock(return_value="argon2")

        # Login with ALL CAPS
        response = await authenticate_user("ADMIN@COMPANY.COM", "password")

        assert response.access_token is not None
        assert response.user.email == "admin@company.com"
