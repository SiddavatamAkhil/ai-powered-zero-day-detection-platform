"""
Unit tests for AuthService against a FAKE repository — no Postgres needed.

This is the payoff of the repository pattern: AuthService only depends on
AbstractUserRepository, so we can swap in an in-memory implementation here
and test all business rules (duplicate email, wrong password, inactive
account, refresh rotation) in milliseconds.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.core.security import hash_password
from app.models.user import RefreshToken, User, UserRole
from app.repositories.user_repository import AbstractUserRepository
from app.schemas.user import UserCreate
from app.services.auth_service import AuthError, AuthService


class FakeUserRepository(AbstractUserRepository):
    def __init__(self):
        self.users: dict[str, User] = {}
        self.tokens: dict[str, RefreshToken] = {}

    async def get_by_email(self, email):
        return next((u for u in self.users.values() if u.email == email), None)

    async def get_by_id(self, user_id):
        return self.users.get(str(user_id))

    async def create(self, user):
        user.id = user.id or uuid.uuid4()
        self.users[str(user.id)] = user
        return user

    async def store_refresh_token(self, user_id, raw_token, expires_at):
        self.tokens[raw_token] = RefreshToken(
            id=uuid.uuid4(), user_id=user_id, token_hash=raw_token,
            revoked=False, expires_at=expires_at,
        )

    async def get_valid_refresh_token(self, raw_token):
        token = self.tokens.get(raw_token)
        if not token or token.revoked or token.expires_at < datetime.now(timezone.utc):
            return None
        return token

    async def revoke_refresh_token(self, raw_token):
        if raw_token in self.tokens:
            self.tokens[raw_token].revoked = True


@pytest.fixture
def repo():
    return FakeUserRepository()


@pytest.fixture
def service(repo):
    return AuthService(repo)


@pytest.mark.asyncio
async def test_register_creates_user(service):
    user = await service.register(UserCreate(email="a@test.com", full_name="A Test", password="password123"))
    assert user.email == "a@test.com"
    assert user.role == UserRole.VIEWER
    assert user.hashed_password != "password123"  # never store plaintext


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(service):
    payload = UserCreate(email="dup@test.com", full_name="Dup", password="password123")
    await service.register(payload)
    with pytest.raises(AuthError, match="already exists"):
        await service.register(payload)


@pytest.mark.asyncio
async def test_login_success_issues_token_pair(service):
    await service.register(UserCreate(email="b@test.com", full_name="B", password="password123"))
    tokens = await service.authenticate("b@test.com", "password123")
    assert tokens.access_token
    assert tokens.refresh_token


@pytest.mark.asyncio
async def test_login_wrong_password_rejected(service):
    await service.register(UserCreate(email="c@test.com", full_name="C", password="password123"))
    with pytest.raises(AuthError, match="Invalid email or password"):
        await service.authenticate("c@test.com", "wrong-password")


@pytest.mark.asyncio
async def test_login_inactive_account_rejected(service, repo):
    user = await service.register(UserCreate(email="d@test.com", full_name="D", password="password123"))
    user.is_active = False
    with pytest.raises(AuthError, match="deactivated"):
        await service.authenticate("d@test.com", "password123")


@pytest.mark.asyncio
async def test_refresh_rotates_token_and_revokes_old_one(service):
    await service.register(UserCreate(email="e@test.com", full_name="E", password="password123"))
    tokens = await service.authenticate("e@test.com", "password123")

    new_tokens = await service.refresh(tokens.refresh_token)
    assert new_tokens.refresh_token != tokens.refresh_token

    # Old refresh token must now be dead (replay protection)
    with pytest.raises(AuthError, match="expired or revoked"):
        await service.refresh(tokens.refresh_token)
