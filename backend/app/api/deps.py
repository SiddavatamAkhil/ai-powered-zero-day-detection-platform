"""
Shared FastAPI dependencies: wiring (repo -> service) and auth guards.
"""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.nosql import get_mongo_db
from app.db.session import get_db
from app.models.user import User, UserRole
from app.repositories.dataset_profile_repository import (
    DatasetProfileRepository,
)
from app.repositories.dataset_repository import (
    SqlAlchemyDatasetRepository,
)
from app.repositories.ml_model_repository import (
    SqlAlchemyMLModelRepository,
)
from app.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from app.services.auth_service import AuthService
from app.services.dataset_service import DatasetService
from app.services.training_service import TrainingService


# OAuth2 token endpoint used by Swagger UI.
# IMPORTANT:
# This must point to the OAuth2-compatible /token endpoint,
# NOT the JSON /login endpoint.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token"
)


def get_auth_service(
    session: AsyncSession = Depends(get_db),
) -> AuthService:
    return AuthService(
        SqlAlchemyUserRepository(session)
    )


def get_dataset_service(
    session: AsyncSession = Depends(get_db),
) -> DatasetService:
    dataset_repo = SqlAlchemyDatasetRepository(session)
    profile_repo = DatasetProfileRepository(
        get_mongo_db()
    )

    return DatasetService(
        dataset_repo,
        profile_repo,
    )


def get_training_service(
    session: AsyncSession = Depends(get_db),
) -> TrainingService:
    return TrainingService(
        SqlAlchemyMLModelRepository(session),
        SqlAlchemyDatasetRepository(session),
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:

    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise credentials_error

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise credentials_error

    repo = SqlAlchemyUserRepository(session)

    user = await repo.get_by_id(user_id)

    if not user or not user.is_active:
        raise credentials_error

    return user


def require_role(
    *allowed_roles: UserRole,
):
    """
    Usage:

        Depends(require_role(UserRole.ADMIN))

    Allows access only to users whose role is included
    in allowed_roles.
    """

    async def checker(
        user: User = Depends(get_current_user),
    ) -> User:

        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return user

    return checker