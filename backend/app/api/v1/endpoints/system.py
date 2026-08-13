import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.repositories.system_repository import SystemRepository
from app.schemas.system import AuditLogRead, NotificationRead

router = APIRouter(tags=["Notifications & Logs"])


def get_system_repo(session: AsyncSession = Depends(get_db)) -> SystemRepository:
    return SystemRepository(session)


@router.get("/notifications", response_model=list[NotificationRead])
async def list_my_notifications(
    unread_only: bool = False,
    user: User = Depends(get_current_user),
    repo: SystemRepository = Depends(get_system_repo),
):
    return await repo.list_notifications(user.id, unread_only=unread_only)


@router.post("/notifications/{notification_id}/read", status_code=204)
async def mark_notification_read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    repo: SystemRepository = Depends(get_system_repo),
):
    await repo.mark_read(notification_id)


@router.get("/logs", response_model=list[AuditLogRead])
async def list_audit_logs(
    limit: int = 200,
    user: User = Depends(require_role(UserRole.ADMIN)),
    repo: SystemRepository = Depends(get_system_repo),
):
    """Admin-only: full audit trail across all users."""
    return await repo.list_logs(limit=limit)


@router.get("/activity-summary")
async def activity_summary(
    hours: int = 24,
    user: User = Depends(get_current_user),
    repo: SystemRepository = Depends(get_system_repo),
):
    """
    Real hourly action-count buckets from audit_logs, for the dashboard's
    activity chart. Replaces what was previously hardcoded placeholder
    data in the frontend — every point here reflects an actual logged
    action (dataset.upload, training.start, etc.), not a mock.
    """
    logs = await repo.list_logs(limit=5000)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent = [log for log in logs if log.created_at >= cutoff]

    bucket_counts = Counter(log.created_at.strftime("%H:00") for log in recent)
    buckets = sorted(bucket_counts.items())

    return {"hours": hours, "buckets": [{"time": t, "count": c} for t, c in buckets]}
