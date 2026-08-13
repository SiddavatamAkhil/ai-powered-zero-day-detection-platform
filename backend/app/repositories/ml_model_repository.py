import uuid
from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ml_model import MLModel, TrainingRun, TrainingStatus


class AbstractMLModelRepository(ABC):
    @abstractmethod
    async def create_training_run(self, run: TrainingRun) -> TrainingRun: ...

    @abstractmethod
    async def update_training_status(self, run_id: uuid.UUID, status: TrainingStatus, error_message: str | None = None) -> None: ...

    @abstractmethod
    async def save_model(self, model: MLModel) -> MLModel: ...

    @abstractmethod
    async def get_model_by_id(self, model_id: uuid.UUID) -> MLModel | None: ...

    @abstractmethod
    async def list_models_for_dataset_training_runs(self, dataset_id: uuid.UUID) -> list[MLModel]: ...

    @abstractmethod
    async def get_training_run(self, run_id: uuid.UUID) -> TrainingRun | None: ...


class SqlAlchemyMLModelRepository(AbstractMLModelRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_training_run(self, run: TrainingRun) -> TrainingRun:
        self._session.add(run)
        await self._session.commit()
        await self._session.refresh(run)
        return run

    async def update_training_status(self, run_id: uuid.UUID, status: TrainingStatus, error_message: str | None = None) -> None:
        run = await self.get_training_run(run_id)
        if run:
            run.status = status
            if error_message:
                run.error_message = error_message
            if status in (TrainingStatus.COMPLETED, TrainingStatus.FAILED):
                from datetime import datetime, timezone
                run.completed_at = datetime.now(timezone.utc)
            await self._session.commit()

    async def save_model(self, model: MLModel) -> MLModel:
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return model

    async def get_model_by_id(self, model_id: uuid.UUID) -> MLModel | None:
        result = await self._session.execute(select(MLModel).where(MLModel.id == model_id))
        return result.scalar_one_or_none()

    async def list_models_for_dataset_training_runs(self, dataset_id: uuid.UUID) -> list[MLModel]:
        result = await self._session.execute(
            select(MLModel).join(TrainingRun).where(TrainingRun.dataset_id == dataset_id)
        )
        return list(result.scalars().all())

    async def get_training_run(self, run_id: uuid.UUID) -> TrainingRun | None:
        result = await self._session.execute(select(TrainingRun).where(TrainingRun.id == run_id))
        return result.scalar_one_or_none()
