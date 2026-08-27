"""
Auth business logic.

Routers call this service; this service communicates with the repository.
No HTTP or SQL logic should exist here.
"""

import uuid
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.security import (
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserRole
from app.repositories.user_repository import AbstractUserRepository
from app.schemas.user import TokenPair, UserCreate


class AuthError(Exception):
    """Raised for authentication or registration failures."""


class AuthService:
    def __init__(self, repo: AbstractUserRepository):
        self._repo = repo

    async def register(self, data: UserCreate) -> User:
        """
        Register a new user.

        For this project/demo version, every newly registered user
        is given ADMIN access so the user can test all platform features.
        """

        existing = await self._repo.get_by_email(data.email)

        if existing:
            raise AuthError("A user with this email already exists.")

        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),

            # Give admin access for project/demo usage
            role=UserRole.ADMIN,

            is_active=True,
        )

        return await self._repo.create(user)

    async def authenticate(
        self,
        email: str,
        password: str,
    ) -> TokenPair:
        """
        Authenticate a user and return access + refresh tokens.
        """

        user = await self._repo.get_by_email(email)

        if not user or not verify_password(
            password,
            user.hashed_password,
        ):
            raise AuthError("Invalid email or password.")

        if not user.is_active:
            raise AuthError(
                "This account has been deactivated."
            )

        return await self._issue_token_pair(user)

    async def refresh(
        self,
        raw_refresh_token: str,
    ) -> TokenPair:
        """
        Validate and rotate a refresh token.
        """

        payload = decode_token(raw_refresh_token)

        if not payload or payload.get("type") != "refresh":
            raise AuthError(
                "Invalid refresh token."
            )

        stored = await self._repo.get_valid_refresh_token(
            raw_refresh_token
        )

        if not stored:
            raise AuthError(
                "Refresh token expired or revoked."
            )

        try:
            user_id = uuid.UUID(payload["sub"])
        except (KeyError, ValueError, TypeError):
            raise AuthError(
                "Invalid refresh token."
            )

        user = await self._repo.get_by_id(user_id)

        if not user or not user.is_active:
            raise AuthError(
                "User not found or inactive."
            )

        # Revoke the old refresh token
        await self._repo.revoke_refresh_token(
            raw_refresh_token
        )

        # Issue a completely new access + refresh pair
        return await self._issue_token_pair(user)

    async def logout(
        self,
        raw_refresh_token: str,
    ) -> None:
        """
        Revoke the refresh token during logout.
        """

        await self._repo.revoke_refresh_token(
            raw_refresh_token
        )

    async def _issue_token_pair(
        self,
        user: User,
    ) -> TokenPair:
        """
        Create access and refresh JWT tokens.
        """

        access = create_token(
            subject=str(user.id),
            role=user.role.value,
            token_type="access",
        )

        refresh = create_token(
            subject=str(user.id),
            role=user.role.value,
            token_type="refresh",
        )

        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        )

        await self._repo.store_refresh_token(
            user.id,
            refresh,
            expires_at,
        )

        return TokenPair(
            access_token=access,
            refresh_token=refresh,
        )