"""
Security utilities for password reset tokens.
"""

from datetime import datetime, timedelta

import jwt
from fastapi import HTTPException, status
from jwt.exceptions import ExpiredSignatureError
from jwt.exceptions import PyJWTError as JWTError

from .config import get_settings

# Token constants
RESET_TOKEN_TYPE = "reset"
RESET_TOKEN_EXPIRE_MINUTES = 30


def create_password_reset_token(email: str) -> str:
    """
    Generates a JWT containing the email and expiration for password reset.

    Args:
        email: User's email address

    Returns:
        Encoded JWT string
    """
    settings = get_settings()
    expire = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expire, "sub": email, "type": RESET_TOKEN_TYPE}

    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


def verify_password_reset_token(token: str) -> str:
    """
    Decodes and validates the password reset token.

    Args:
        token: The JWT token string

    Returns:
        The email address from the token if valid

    Raises:
        HTTPException: If token is invalid, expired, or wrong type
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )

        token_type = payload.get("type")
        email = payload.get("sub")

        if token_type != RESET_TOKEN_TYPE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de token inválido"
            )

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token inválido: falta el correo electrónico",
            )

        return email

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El enlace de recuperación ha expirado",
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enlace de recuperación inválido",
        )
