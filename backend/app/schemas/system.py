import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.system import NotificationLevel
from app.models.user import UserRole


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    level: NotificationLevel
    message: str
    read: bool
    created_at: datetime


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    details: str | None
    created_at: datetime


class UserRoleUpdate(BaseModel):
    role: UserRole


class UserActiveUpdate(BaseModel):
    is_active: bool
