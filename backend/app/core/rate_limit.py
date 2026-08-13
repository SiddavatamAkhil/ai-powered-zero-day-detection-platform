"""
Fixed-window rate limiter backed by Redis (already provisioned for
session cache / pub-sub — this reuses it rather than adding a new
dependency like slowapi).

Applied to /auth/login and /auth/register to blunt brute-force and
registration-spam attacks — previously these endpoints had zero rate
limiting, which is a real gap for anything calling itself
"enterprise-grade."
"""
from fastapi import HTTPException, Request, status

from app.db.nosql import get_redis


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int, key_prefix: str):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix

    async def __call__(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        redis = await get_redis()
        key = f"ratelimit:{self.key_prefix}:{client_ip}"

        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, self.window_seconds)

        if current > self.max_requests:
            ttl = await redis.ttl(key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests. Try again in {max(ttl, 1)} seconds.",
            )


# Tuned deliberately tighter than a typical API endpoint: login/register
# are the highest-value targets for credential stuffing and spam signups.
login_rate_limiter = RateLimiter(max_requests=10, window_seconds=60, key_prefix="login")
register_rate_limiter = RateLimiter(max_requests=5, window_seconds=300, key_prefix="register")
