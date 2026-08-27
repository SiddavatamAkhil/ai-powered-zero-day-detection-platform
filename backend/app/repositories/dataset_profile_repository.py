"""
Mongo-backed repository for dataset profiling documents.

Kept separate from SqlAlchemyDatasetRepository because it talks to a
different database entirely — mixing them into one repository would
violate single-responsibility and make the Postgres side untestable
without spinning up Mongo too.
"""
import logging
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class DatasetProfileRepository:
    def __init__(self, mongo_db: AsyncIOMotorDatabase | None):
        self._mongo_db = mongo_db

    async def save_profile(self, dataset_id: str, profile: dict) -> None:
        if self._mongo_db is None:
            logger.warning("MongoDB unavailable; skipping dataset profile persistence.")
            return
        try:
            document = {
                "dataset_id": dataset_id,
                "generated_at": datetime.now(timezone.utc),
                **profile,
            }
            await self._mongo_db["dataset_profiles"].update_one(
                {"dataset_id": dataset_id}, {"$set": document}, upsert=True
            )
        except Exception as exc:
            logger.warning("MongoDB unavailable; skipping dataset profile persistence: %s", exc)

    async def get_profile(self, dataset_id: str) -> dict | None:
        if self._mongo_db is None:
            return None
        try:
            return await self._mongo_db["dataset_profiles"].find_one({"dataset_id": dataset_id}, {"_id": 0})
        except Exception as exc:
            logger.warning("MongoDB unavailable; returning empty profile: %s", exc)
            return None
