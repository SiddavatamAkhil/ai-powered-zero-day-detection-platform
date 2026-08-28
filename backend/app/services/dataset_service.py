"""
Dataset orchestration service.

This is the only layer that touches the filesystem and coordinates between
the two repositories (Postgres metadata + Mongo profile) and the pure
DataProcessingService. Routers stay thin; DataProcessingService stays pure.
"""
import os
import uuid

import joblib
import pandas as pd

from app.core.config import settings
from app.models.dataset import ClassSplit, Dataset, DatasetStatus
from app.repositories.dataset_profile_repository import DatasetProfileRepository
from app.repositories.dataset_repository import AbstractDatasetRepository
from app.schemas.dataset import OpenSetSplitConfig
from app.services.data_processing_service import DataProcessingService

# Labels treated as "normal traffic" across common IDS datasets. Never
# eligible for unknown-holdout (enforced again in the repository as a
# second guard — defense in depth).
BENIGN_LABELS = {"benign", "normal", "normal."}

ALLOWED_EXTENSIONS = {".csv"}
MIN_ROWS_REQUIRED = 10
MAX_COLUMNS_ALLOWED = 500  # sanity ceiling — a legitimate flow-feature dataset won't exceed this


class DatasetError(Exception):
    pass


class DatasetService:
    def __init__(self, repo: AbstractDatasetRepository, profile_repo: DatasetProfileRepository):
        self._repo = repo
        self._profile_repo = profile_repo
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        os.makedirs(settings.PROCESSED_DIR, exist_ok=True)

    async def upload(
        self,
        name: str,
        label_column: str,
        original_filename: str,
        file_bytes: bytes,
        uploaded_by: uuid.UUID,
    ) -> Dataset:
        _, ext = os.path.splitext(original_filename.lower())
        if ext not in ALLOWED_EXTENSIONS:
            raise DatasetError(f"Unsupported file type '{ext}'. Only CSV files are accepted.")
        if len(file_bytes) == 0:
            raise DatasetError("Uploaded file is empty.")

        existing = await self._repo.find_by_filename(original_filename)
        if existing:
            raise DatasetError(f"A dataset with the filename '{original_filename}' already exists. Delete it first or rename the file.")

        # Strip any directory components the client sent (e.g. "../../etc/passwd.csv")
        # before building a path — never trust a client-supplied filename for path construction.
        safe_filename = os.path.basename(original_filename)

        dataset_id = uuid.uuid4()
        raw_path = os.path.join(settings.UPLOAD_DIR, f"{dataset_id}_{safe_filename}")

        with open(raw_path, "wb") as f:
            f.write(file_bytes)

        try:
            df = pd.read_csv(raw_path, nrows=1000)
        except Exception as exc:
            os.remove(raw_path)
            raise DatasetError(f"Could not parse file as CSV: {exc}") from exc

        if label_column not in df.columns:
            os.remove(raw_path)
            raise DatasetError(f"Label column '{label_column}' not found. Available columns: {list(df.columns)}")

        if len(df.columns) > MAX_COLUMNS_ALLOWED:
            os.remove(raw_path)
            raise DatasetError(f"File has {len(df.columns)} columns, exceeding the {MAX_COLUMNS_ALLOWED} limit.")

        if len(df) < MIN_ROWS_REQUIRED:
            os.remove(raw_path)
            raise DatasetError(f"File must contain at least {MIN_ROWS_REQUIRED} rows to be usable for training.")

        if df[label_column].nunique() < 2:
            os.remove(raw_path)
            raise DatasetError("Label column must contain at least 2 distinct classes.")

        dataset = Dataset(
            id=dataset_id,
            name=name,
            original_filename=original_filename,
            raw_path=raw_path,
            label_column=label_column,
            status=DatasetStatus.UPLOADED,
            uploaded_by=uploaded_by,
        )
        return await self._repo.create(dataset)

    async def profile_and_register_classes(self, dataset_id: uuid.UUID) -> dict:
        dataset = await self._require_dataset(dataset_id)
        df = pd.read_csv(dataset.raw_path)

        profile = DataProcessingService.profile(df, dataset.label_column)
        await self._profile_repo.save_profile(str(dataset_id), profile)

        class_counts = {str(k): int(v) for k, v in profile["class_distribution"].items()}
        benign_found = {c for c in class_counts if c.strip().lower() in BENIGN_LABELS}
        await self._repo.upsert_classes(dataset_id, class_counts, benign_found)
        await self._repo.update_status(dataset_id, DatasetStatus.PROFILED)

        return profile

    async def clean(self, dataset_id: uuid.UUID):
        dataset = await self._require_dataset(dataset_id)
        df = pd.read_csv(dataset.raw_path)

        cleaned_df, report = DataProcessingService.clean(df, dataset.label_column)

        cleaned_path = os.path.join(settings.PROCESSED_DIR, f"{dataset_id}_cleaned.csv")
        cleaned_df.to_csv(cleaned_path, index=False)

        await self._repo.set_cleaned_path(dataset_id, cleaned_path, len(cleaned_df))
        return report

    async def engineer_features(self, dataset_id: uuid.UUID):
        dataset = await self._require_dataset(dataset_id)
        if not dataset.cleaned_path:
            raise DatasetError("Dataset must be cleaned before feature engineering.")

        df = pd.read_csv(dataset.cleaned_path)
        result = DataProcessingService.engineer_features(df, dataset.label_column)

        features_path = os.path.join(settings.PROCESSED_DIR, f"{dataset_id}_features.parquet")
        scaler_path = os.path.join(settings.PROCESSED_DIR, f"{dataset_id}_scaler.joblib")

        combined = result.features.copy()
        combined[dataset.label_column] = result.labels.values
        combined.to_parquet(features_path, index=False)
        joblib.dump(result.scaler, scaler_path)

        await self._repo.set_features_path(dataset_id, features_path, scaler_path, len(result.feature_columns))
        return result

    async def configure_open_set_split(self, dataset_id: uuid.UUID, config: OpenSetSplitConfig):
        await self._require_dataset(dataset_id)
        assignments = {a.class_name: a.split for a in config.assignments}
        await self._repo.assign_splits(dataset_id, assignments)
        await self._repo.update_status(dataset_id, DatasetStatus.SPLIT_CONFIGURED)

        return {
            "known_classes": await self._repo.get_known_classes(dataset_id),
            "unknown_classes": await self._repo.get_unknown_classes(dataset_id),
        }

    async def get(self, dataset_id: uuid.UUID) -> Dataset:
        return await self._require_dataset(dataset_id)

    async def list_all(self) -> list[Dataset]:
        return await self._repo.list_all()

    async def delete(self, dataset_id: uuid.UUID) -> None:
        import sqlalchemy as sa
        from app.models.ml_model import MLModel, TrainingRun

        dataset = await self._require_dataset(dataset_id)

        # Delete files from disk
        for path in [dataset.raw_path, dataset.cleaned_path, dataset.features_path, dataset.scaler_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

        # Cascade: delete ml_models → training_runs → dataset_classes → dataset
        session = self._repo._session
        run_ids = (await session.execute(
            sa.select(TrainingRun.id).where(TrainingRun.dataset_id == dataset_id)
        )).scalars().all()

        if run_ids:
            # Delete model artifact files and model rows
            models = (await session.execute(
                sa.select(MLModel).where(MLModel.training_run_id.in_(run_ids))
            )).scalars().all()
            for m in models:
                for path in [m.artifact_path, m.openmax_path, m.background_data_path]:
                    if path and os.path.exists(path):
                        try:
                            os.remove(path)
                        except OSError:
                            pass
                await session.delete(m)

            await session.execute(
                sa.delete(TrainingRun).where(TrainingRun.dataset_id == dataset_id)
            )

        await self._repo.delete(dataset_id)

    async def _require_dataset(self, dataset_id: uuid.UUID) -> Dataset:
        dataset = await self._repo.get_by_id(dataset_id)
        if dataset is None:
            raise DatasetError("Dataset not found.")
        return dataset
