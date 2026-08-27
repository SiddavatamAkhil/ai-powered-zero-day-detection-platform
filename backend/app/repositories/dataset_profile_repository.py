"""
Mongo-backed repository for dataset profiling documents.

Kept separate from SqlAlchemyDatasetRepository because it talks to a
different database entirely — mixing them into one repository would
violate single-responsibility and make the Postgres side untestable
without spinning up Mongo too.
"""
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase


import logging

logger = logging.getLogger(__name__)


class DatasetProfileRepository:
    def __init__(self, mongo_db: AsyncIOMotorDatabase):
        self._collection = mongo_db["dataset_profiles"]

    async def save_profile(self, dataset_id: str, profile: dict) -> None:
        try:
            document = {
                "dataset_id": dataset_id,
                "generated_at": datetime.now(timezone.utc),
                **profile,
            }
            await self._collection.update_one(
                {"dataset_id": dataset_id}, {"$set": document}, upsert=True
            )
        except Exception as exc:
            logger.warning("MongoDB unavailable; skipping dataset profile persistence: %s", exc)

    async def get_profile(self, dataset_id: str) -> dict | None:
        try:
            return await self._collection.find_one({"dataset_id": dataset_id}, {"_id": 0})
        except Exception as exc:
            logger.warning("MongoDB unavailable; returning empty profile: %s", exc)
            return None
