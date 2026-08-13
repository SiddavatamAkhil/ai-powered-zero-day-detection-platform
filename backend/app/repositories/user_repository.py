"""
Repository pattern for User / RefreshToken persistence.

Why an ABC: the service layer depends on `AbstractUserRepository`, never on
`SqlAlchemyUserRepository` directly. In tests we swap in an in-memory fake
repo (see tests/test_auth.py) with zero changes to AuthService — that's the
whole point of the pattern.
"""
import hashlib
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import RefreshToken, User


class AbstractUserRepository(ABC):
    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...

    @abstractmethod
    async def create(self, user: User) -> User: ...

    @abstractmethod
    async def store_refresh_token(self, user_id: uuid.UUID, raw_token: str, expires_at: datetime) -> None: ...

    @abstractmethod
    async def get_valid_refresh_token(self, raw_token: str) -> RefreshToken | None: ...

    @abstractmethod
    async def revoke_refresh_token(self, raw_token: str) -> None: ...


class SqlAlchemyUserRepository(AbstractUserRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        # Refresh tokens are stored hashed (like passwords) — if the DB
        # leaks, stored tokens alone can't be replayed.
        return hashlib.sha256(raw_token.encode()).hexdigest()

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def store_refresh_token(self, user_id: uuid.UUID, raw_token: str, expires_at: datetime) -> None:
        token = RefreshToken(
            user_id=user_id,
            token_hash=self._hash_token(raw_token),
            expires_at=expires_at,
        )
        self._session.add(token)
        await self._session.commit()

    async def get_valid_refresh_token(self, raw_token: str) -> RefreshToken | None:
        token_hash = self._hash_token(raw_token)
        result = await self._session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        token = result.scalar_one_or_none()
        if token is None or token.revoked or token.expires_at < datetime.now(timezone.utc):
            return None
        return token

    async def revoke_refresh_token(self, raw_token: str) -> None:
        token = await self.get_valid_refresh_token(raw_token)
        if token:
            token.revoked = True
            await self._session.commit()
