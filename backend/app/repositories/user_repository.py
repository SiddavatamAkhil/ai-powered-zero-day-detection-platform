"""
Repository pattern for User / RefreshToken persistence.

The service layer depends on AbstractUserRepository instead of directly
depending on SQLAlchemy. This makes the application easier to test and
allows the repository implementation to be replaced if needed.
"""

import hashlib
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import RefreshToken, User, UserRole


class AbstractUserRepository(ABC):
    """
    Abstract repository interface for User and RefreshToken operations.
    """

    @abstractmethod
    async def get_by_email(
        self,
        email: str,
    ) -> User | None:
        ...

    @abstractmethod
    async def get_by_id(
        self,
        user_id: uuid.UUID,
    ) -> User | None:
        ...

    @abstractmethod
    async def count_users(self) -> int:
        ...

    @abstractmethod
    async def create(
        self,
        user: User,
    ) -> User:
        ...

    @abstractmethod
    async def update_user_role(
        self,
        user_id: uuid.UUID,
        role: UserRole,
    ) -> User | None:
        ...

    @abstractmethod
    async def store_refresh_token(
        self,
        user_id: uuid.UUID,
        raw_token: str,
        expires_at: datetime,
    ) -> None:
        ...

    @abstractmethod
    async def get_valid_refresh_token(
        self,
        raw_token: str,
    ) -> RefreshToken | None:
        ...

    @abstractmethod
    async def revoke_refresh_token(
        self,
        raw_token: str,
    ) -> None:
        ...


class SqlAlchemyUserRepository(AbstractUserRepository):
    """
    SQLAlchemy implementation of the User repository.
    """

    def __init__(
        self,
        session: AsyncSession,
    ):
        self._session = session

    @staticmethod
    def _hash_token(
        raw_token: str,
    ) -> str:
        """
        Hash refresh tokens before storing them in the database.
        """

        return hashlib.sha256(
            raw_token.encode("utf-8")
        ).hexdigest()

    async def get_by_email(
        self,
        email: str,
    ) -> User | None:
        """
        Get a user using their email address.
        """

        result = await self._session.execute(
            select(User).where(
                User.email == email
            )
        )

        return result.scalar_one_or_none()

    async def get_by_id(
        self,
        user_id: uuid.UUID,
    ) -> User | None:
        """
        Get a user using their UUID.
        """

        result = await self._session.execute(
            select(User).where(
                User.id == user_id
            )
        )

        return result.scalar_one_or_none()

    async def count_users(self) -> int:
        """
        Return the total number of users.
        """

        result = await self._session.execute(
            select(func.count()).select_from(User)
        )

        return result.scalar_one() or 0

    async def create(
        self,
        user: User,
    ) -> User:
        """
        Create a new user.
        """

        self._session.add(user)

        await self._session.commit()

        await self._session.refresh(user)

        return user

    async def update_user_role(
        self,
        user_id: uuid.UUID,
        role: UserRole,
    ) -> User | None:
        """
        Update the role of an existing user.

        This is used to promote the configured project owner
        from VIEWER to ADMIN.
        """

        user = await self.get_by_id(user_id)

        if user is None:
            return None

        user.role = role

        await self._session.commit()

        await self._session.refresh(user)

        return user

    async def store_refresh_token(
        self,
        user_id: uuid.UUID,
        raw_token: str,
        expires_at: datetime,
    ) -> None:
        """
        Store a hashed refresh token.
        """

        token = RefreshToken(
            user_id=user_id,
            token_hash=self._hash_token(raw_token),
            expires_at=expires_at,
            revoked=False,
        )

        self._session.add(token)

        await self._session.commit()

    async def get_valid_refresh_token(
        self,
        raw_token: str,
    ) -> RefreshToken | None:
        """
        Return the refresh token only if it exists,
        has not been revoked, and has not expired.
        """

        token_hash = self._hash_token(raw_token)

        result = await self._session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash
            )
        )

        token = result.scalar_one_or_none()

        if token is None:
            return None

        if token.revoked:
            return None

        if token.expires_at < datetime.now(timezone.utc):
            return None

        return token

    async def revoke_refresh_token(
        self,
        raw_token: str,
    ) -> None:
        """
        Revoke an existing refresh token.
        """

        token_hash = self._hash_token(raw_token)

        result = await self._session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash
            )
        )

        token = result.scalar_one_or_none()

        if token is not None:
            token.revoked = True

            await self._session.commit()