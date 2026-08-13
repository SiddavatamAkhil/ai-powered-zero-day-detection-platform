"""
Mongo-backed repository for dataset profiling documents.

Kept separate from SqlAlchemyDatasetRepository because it talks to a
different database entirely — mixing them into one repository would
violate single-responsibility and make the Postgres side untestable
without spinning up Mongo too.
"""
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase


class DatasetProfileRepository:
    def __init__(self, mongo_db: AsyncIOMotorDatabase):
        self._collection = mongo_db["dataset_profiles"]

    async def save_profile(self, dataset_id: str, profile: dict) -> None:
        document = {
            "dataset_id": dataset_id,
            "generated_at": datetime.now(timezone.utc),
            **profile,
        }
        await self._collection.update_one(
            {"dataset_id": dataset_id}, {"$set": document}, upsert=True
        )

    async def get_profile(self, dataset_id: str) -> dict | None:
        return await self._collection.find_one({"dataset_id": dataset_id}, {"_id": 0})
