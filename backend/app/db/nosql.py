"""
MongoDB and Redis client factories.

Both are async clients so they don't block the FastAPI event loop
(important once we're streaming live packet simulation events).
"""
import logging
import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

logger = logging.getLogger(__name__)

_mongo_client: AsyncIOMotorClient | None = None
_redis_client: aioredis.Redis | None = None


def get_mongo_db():
    global _mongo_client
    if _mongo_client is None:
        try:
            _mongo_client = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=2000)
        except Exception as exc:
            logger.warning("Could not initialize MongoDB client: %s", exc)
            return None
    try:
        return _mongo_client[settings.MONGO_DB_NAME]
    except Exception as exc:
        logger.warning("Error accessing MongoDB database: %s", exc)
        return None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2.0)
    return _redis_client
