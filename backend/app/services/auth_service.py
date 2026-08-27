"""
Auth business logic. Routers call this; this calls the repository.
No SQL, no HTTP concerns — just rules.
"""
import uuid
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.repositories.user_repository import AbstractUserRepository
from app.schemas.user import TokenPair, UserCreate


class AuthError(Exception):
    """Raised for any auth failure; routers translate this to HTTP 401/409."""


class AuthService:
    def __init__(self, repo: AbstractUserRepository):
        self._repo = repo

    async def register(self, data: UserCreate) -> User:
        existing = await self._repo.get_by_email(data.email)
        if existing:
            raise AuthError("A user with this email already exists.")

        # First registered user becomes admin; everyone else defaults to
        # viewer and is promoted later via the User Management module.
        user_count = await self._repo.count_users()
        role = UserRole.ADMIN if user_count == 0 else UserRole.VIEWER

        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            role=role,
            is_active=True,
        )
        return await self._repo.create(user)

    async def authenticate(self, email: str, password: str) -> TokenPair:
        user = await self._repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise AuthError("Invalid email or password.")
        if not user.is_active:
            raise AuthError("This account has been deactivated.")

        return await self._issue_token_pair(user)

    async def refresh(self, raw_refresh_token: str) -> TokenPair:
        payload = decode_token(raw_refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise AuthError("Invalid refresh token.")

        stored = await self._repo.get_valid_refresh_token(raw_refresh_token)
        if not stored:
            raise AuthError("Refresh token expired or revoked.")

        user = await self._repo.get_by_id(uuid.UUID(payload["sub"]))
        if not user or not user.is_active:
            raise AuthError("User not found or inactive.")

        # Rotate: revoke the used token, issue a brand new pair. Prevents
        # replay of a stolen refresh token after it's been legitimately used.
        await self._repo.revoke_refresh_token(raw_refresh_token)
        return await self._issue_token_pair(user)

    async def logout(self, raw_refresh_token: str) -> None:
        await self._repo.revoke_refresh_token(raw_refresh_token)

    async def _issue_token_pair(self, user: User) -> TokenPair:
        access = create_token(str(user.id), user.role.value, "access")
        refresh = create_token(str(user.id), user.role.value, "refresh")
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self._repo.store_refresh_token(user.id, refresh, expires_at)
        return TokenPair(access_token=access, refresh_token=refresh)
