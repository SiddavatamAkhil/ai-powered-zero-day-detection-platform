"""
Audit logging middleware.

Deliberately implemented as middleware rather than a manual
`repo.log_action(...)` call sprinkled into every mutating endpoint —
that pattern is easy to forget on a new endpoint and silently leaves gaps
in the audit trail. Middleware guarantees every state-changing request
(POST/PATCH/PUT/DELETE) gets logged, with zero endpoint code needing to
know logging exists.

Read-only requests (GET) are skipped — logging every page view would
flood the table with low-value entries and isn't what "audit trail"
means for this platform.
"""
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.models.system import AuditLog

LOGGED_METHODS = {"POST", "PATCH", "PUT", "DELETE"}
# Auth endpoints are noisy (every login attempt) and already have their own
# rate-limit visibility; skip them here to keep the audit trail focused on
# platform actions (dataset/training/report/user-management operations).
SKIP_PATH_PREFIXES = ("/api/v1/auth",)


class AuditLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        should_log = (
            request.method in LOGGED_METHODS
            and not request.url.path.startswith(SKIP_PATH_PREFIXES)
            and response.status_code < 400  # only log actions that actually succeeded
        )
        if should_log:
            user_id = self._extract_user_id(request)
            await self._write_log(action=f"{request.method} {request.url.path}", user_id=user_id)

        return response

    @staticmethod
    def _extract_user_id(request: Request) -> uuid.UUID | None:
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        payload = decode_token(auth_header.removeprefix("Bearer "))
        if not payload:
            return None
        try:
            return uuid.UUID(payload.get("sub"))
        except (ValueError, TypeError):
            return None

    @staticmethod
    async def _write_log(action: str, user_id: uuid.UUID | None) -> None:
        # Best-effort: a logging failure must never break the actual
        # request that already succeeded and returned a response.
        try:
            async with AsyncSessionLocal() as session:
                session.add(AuditLog(user_id=user_id, action=action))
                await session.commit()
        except Exception:
            pass
