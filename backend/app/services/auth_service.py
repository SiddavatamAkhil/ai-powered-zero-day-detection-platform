"""
Auth business logic.

Routers call this service; the service talks to the repository.
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


from app.core.config import settings as _settings
ADMIN_EMAIL = _settings.ADMIN_EMAIL


class AuthError(Exception):
    """Raised for authentication-related failures."""


class AuthService:
    def __init__(self, repo: AbstractUserRepository):
        self._repo = repo

    async def register(self, data: UserCreate) -> User:
        existing = await self._repo.get_by_email(data.email)

        if existing:
            raise AuthError(
                "A user with this email already exists."
            )

        # Your account will always be created as ADMIN
        if data.email.strip().lower() == ADMIN_EMAIL.lower():
            role = UserRole.ADMIN
        else:
            user_count = await self._repo.count_users()

            # First user becomes admin
            role = (
                UserRole.ADMIN
                if user_count == 0
                else UserRole.VIEWER
            )

        user = User(
            email=data.email.strip().lower(),
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            role=role,
            is_active=True,
        )

        return await self._repo.create(user)

    async def authenticate(
        self,
        email: str,
        password: str,
    ) -> TokenPair:

        email = email.strip().lower()

        user = await self._repo.get_by_email(email)

        if not user:
            raise AuthError(
                "Invalid email or password."
            )

        if not verify_password(
            password,
            user.hashed_password,
        ):
            raise AuthError(
                "Invalid email or password."
            )

        if not user.is_active:
            raise AuthError(
                "This account has been deactivated."
            )

        # ==========================================
        # FORCE YOUR ACCOUNT TO ADMIN
        # ==========================================

        if user.email.strip().lower() == ADMIN_EMAIL.lower():

            if user.role != UserRole.ADMIN:
                user.role = UserRole.ADMIN

                # Save the updated role to database.
                # The SQLAlchemy repository already owns
                # the session, so we add a method below.
                await self._repo.update_user_role(
                    user.id,
                    UserRole.ADMIN,
                )

        return await self._issue_token_pair(user)

    async def refresh(
        self,
        raw_refresh_token: str,
    ) -> TokenPair:

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
        except (
            KeyError,
            ValueError,
            TypeError,
        ):
            raise AuthError(
                "Invalid refresh token."
            )

        user = await self._repo.get_by_id(user_id)

        if not user or not user.is_active:
            raise AuthError(
                "User not found or inactive."
            )

        # Make sure your account remains admin
        if user.email.strip().lower() == ADMIN_EMAIL.lower():

            if user.role != UserRole.ADMIN:
                user.role = UserRole.ADMIN

                await self._repo.update_user_role(
                    user.id,
                    UserRole.ADMIN,
                )

        # Rotate refresh token
        await self._repo.revoke_refresh_token(
            raw_refresh_token
        )

        return await self._issue_token_pair(user)

    async def logout(
        self,
        raw_refresh_token: str,
    ) -> None:

        await self._repo.revoke_refresh_token(
            raw_refresh_token
        )

    async def _issue_token_pair(
        self,
        user: User,
    ) -> TokenPair:

        access = create_token(
            str(user.id),
            user.role.value,
            "access",
        )

        refresh = create_token(
            str(user.id),
            user.role.value,
            "refresh",
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