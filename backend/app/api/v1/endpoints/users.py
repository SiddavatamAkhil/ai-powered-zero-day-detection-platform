"""
User management endpoints — admin-only. Reuses SqlAlchemyUserRepository
from Phase 1 rather than introducing a parallel repository, since Users
already have one and this is the same table.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.system import UserActiveUpdate, UserRoleUpdate
from app.schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["User Management"])
_admin_only = require_role(UserRole.ADMIN)


@router.get("", response_model=list[UserRead])
async def list_users(admin: User = Depends(_admin_only), session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(User))
    return list(result.scalars().all())


@router.patch("/{user_id}/role", response_model=UserRead)
async def update_user_role(
    user_id: uuid.UUID,
    payload: UserRoleUpdate,
    admin: User = Depends(_admin_only),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found.")
    user.role = payload.role
    await session.commit()
    await session.refresh(user)
    return user


@router.patch("/{user_id}/active", response_model=UserRead)
async def update_user_active_status(
    user_id: uuid.UUID,
    payload: UserActiveUpdate,
    admin: User = Depends(_admin_only),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found.")
    if user.id == admin.id and not payload.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate your own account.")
    user.is_active = payload.is_active
    await session.commit()
    await session.refresh(user)
    return user
