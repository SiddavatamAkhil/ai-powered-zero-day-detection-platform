"""
Repository pattern for Dataset / DatasetClass persistence — same shape as
UserRepository in Phase 1.
"""
import uuid
from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.dataset import ClassSplit, Dataset, DatasetClass, DatasetStatus


class AbstractDatasetRepository(ABC):
    @abstractmethod
    async def create(self, dataset: Dataset) -> Dataset: ...

    @abstractmethod
    async def get_by_id(self, dataset_id: uuid.UUID) -> Dataset | None: ...

    @abstractmethod
    async def list_all(self) -> list[Dataset]: ...

    @abstractmethod
    async def update_status(self, dataset_id: uuid.UUID, status: DatasetStatus) -> None: ...

    @abstractmethod
    async def set_cleaned_path(self, dataset_id: uuid.UUID, path: str, num_rows: int) -> None: ...

    @abstractmethod
    async def set_features_path(self, dataset_id: uuid.UUID, features_path: str, scaler_path: str, num_features: int) -> None: ...

    @abstractmethod
    async def upsert_classes(self, dataset_id: uuid.UUID, class_counts: dict[str, int], benign_labels: set[str]) -> None: ...

    @abstractmethod
    async def assign_splits(self, dataset_id: uuid.UUID, assignments: dict[str, ClassSplit]) -> None: ...

    @abstractmethod
    async def get_known_classes(self, dataset_id: uuid.UUID) -> list[str]: ...

    @abstractmethod
    async def get_unknown_classes(self, dataset_id: uuid.UUID) -> list[str]: ...

    @abstractmethod
    async def delete(self, dataset_id: uuid.UUID) -> None: ...

    @abstractmethod
    async def find_by_filename(self, original_filename: str) -> Dataset | None: ...


class SqlAlchemyDatasetRepository(AbstractDatasetRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, dataset: Dataset) -> Dataset:
        self._session.add(dataset)
        await self._session.commit()
        await self._session.refresh(dataset)
        return dataset

    async def get_by_id(self, dataset_id: uuid.UUID) -> Dataset | None:
        result = await self._session.execute(
            select(Dataset).options(selectinload(Dataset.classes)).where(Dataset.id == dataset_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Dataset]:
        result = await self._session.execute(select(Dataset).options(selectinload(Dataset.classes)))
        return list(result.scalars().all())

    async def update_status(self, dataset_id: uuid.UUID, status: DatasetStatus) -> None:
        dataset = await self.get_by_id(dataset_id)
        if dataset:
            dataset.status = status
            await self._session.commit()

    async def set_cleaned_path(self, dataset_id: uuid.UUID, path: str, num_rows: int) -> None:
        dataset = await self.get_by_id(dataset_id)
        if dataset:
            dataset.cleaned_path = path
            dataset.num_rows = num_rows
            dataset.status = DatasetStatus.CLEANED
            await self._session.commit()

    async def set_features_path(self, dataset_id: uuid.UUID, features_path: str, scaler_path: str, num_features: int) -> None:
        dataset = await self.get_by_id(dataset_id)
        if dataset:
            dataset.features_path = features_path
            dataset.scaler_path = scaler_path
            dataset.num_features = num_features
            dataset.status = DatasetStatus.FEATURE_ENGINEERED
            await self._session.commit()

    async def upsert_classes(self, dataset_id: uuid.UUID, class_counts: dict[str, int], benign_labels: set[str]) -> None:
        for class_name, count in class_counts.items():
            is_benign = class_name in benign_labels
            self._session.add(
                DatasetClass(
                    dataset_id=dataset_id,
                    class_name=class_name,
                    sample_count=count,
                    is_benign=is_benign,
                    split=ClassSplit.KNOWN,  # default; adjusted via assign_splits
                )
            )
        await self._session.commit()

    async def assign_splits(self, dataset_id: uuid.UUID, assignments: dict[str, ClassSplit]) -> None:
        result = await self._session.execute(
            select(DatasetClass).where(DatasetClass.dataset_id == dataset_id)
        )
        classes = {c.class_name: c for c in result.scalars().all()}
        for class_name, split in assignments.items():
            row = classes.get(class_name)
            if row is None:
                continue
            # Benign traffic must never be held out — "unknown attack
            # recall" is meaningless if normal traffic can be "unknown".
            if row.is_benign and split == ClassSplit.UNKNOWN_HOLDOUT:
                continue
            row.split = split
        await self._session.commit()

    async def get_known_classes(self, dataset_id: uuid.UUID) -> list[str]:
        result = await self._session.execute(
            select(DatasetClass.class_name).where(
                DatasetClass.dataset_id == dataset_id, DatasetClass.split == ClassSplit.KNOWN
            )
        )
        return [row[0] for row in result.all()]

    async def get_unknown_classes(self, dataset_id: uuid.UUID) -> list[str]:
        result = await self._session.execute(
            select(DatasetClass.class_name).where(
                DatasetClass.dataset_id == dataset_id, DatasetClass.split == ClassSplit.UNKNOWN_HOLDOUT
            )
        )
        return [row[0] for row in result.all()]

    async def delete(self, dataset_id: uuid.UUID) -> None:
        dataset = await self.get_by_id(dataset_id)
        if dataset:
            await self._session.delete(dataset)
            await self._session.commit()

    async def find_by_filename(self, original_filename: str) -> Dataset | None:
        result = await self._session.execute(
            select(Dataset).where(Dataset.original_filename == original_filename)
        )
        return result.scalar_one_or_none()
