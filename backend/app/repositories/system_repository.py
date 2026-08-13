import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system import AuditLog, Notification, NotificationLevel


class SystemRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_notification(self, user_id: uuid.UUID, message: str, level: NotificationLevel = NotificationLevel.INFO) -> Notification:
        notification = Notification(user_id=user_id, message=message, level=level)
        self._session.add(notification)
        await self._session.commit()
        await self._session.refresh(notification)
        return notification

    async def list_notifications(self, user_id: uuid.UUID, unread_only: bool = False) -> list[Notification]:
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.read.is_(False))
        query = query.order_by(Notification.created_at.desc())
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def mark_read(self, notification_id: uuid.UUID) -> None:
        result = await self._session.execute(select(Notification).where(Notification.id == notification_id))
        notification = result.scalar_one_or_none()
        if notification:
            notification.read = True
            await self._session.commit()

    async def log_action(self, action: str, user_id: uuid.UUID | None = None, details: str | None = None) -> AuditLog:
        entry = AuditLog(user_id=user_id, action=action, details=details)
        self._session.add(entry)
        await self._session.commit()
        return entry

    async def list_logs(self, limit: int = 200) -> list[AuditLog]:
        result = await self._session.execute(
            select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
