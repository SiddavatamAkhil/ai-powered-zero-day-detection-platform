"""
Rate limiter backed by Redis.

If Redis is temporarily unavailable, authentication should still work.
The limiter will fail open rather than causing login/register endpoints
to return HTTP 500.
"""

import logging

from fastapi import HTTPException, Request, status

from app.db.nosql import get_redis

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        key_prefix: str,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix

    async def __call__(self, request: Request) -> None:
        client_ip = (
            request.client.host
            if request.client
            else "unknown"
        )

        key = f"ratelimit:{self.key_prefix}:{client_ip}"

        try:
            redis = await get_redis()

            current = await redis.incr(key)

            if current == 1:
                await redis.expire(
                    key,
                    self.window_seconds,
                )

            if current > self.max_requests:
                ttl = await redis.ttl(key)

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        "Too many requests. "
                        f"Try again in {max(ttl, 1)} seconds."
                    ),
                )

        except HTTPException:
            # Keep intentional rate-limit errors.
            raise

        except Exception as exc:
            # Redis failure must not break authentication.
            logger.warning(
                "Rate limiter unavailable; allowing request. "
                "Redis error: %s",
                exc,
            )

            return


login_rate_limiter = RateLimiter(
    max_requests=10,
    window_seconds=60,
    key_prefix="login",
)

register_rate_limiter = RateLimiter(
    max_requests=5,
    window_seconds=300,
    key_prefix="register",
)