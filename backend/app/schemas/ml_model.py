import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.ml_model import ModelArchitecture, TrainingStatus


class TrainingRequest(BaseModel):
    dataset_id: uuid.UUID
    architecture: ModelArchitecture
    epochs: int = Field(default=20, ge=1, le=500)
    batch_size: int = Field(default=128, ge=8, le=4096)
    learning_rate: float = Field(default=1e-3, gt=0, le=1)
    seed: int = Field(default=42, description="Random seed for reproducibility across repeated runs / ablations.")


class TrainingRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    architecture: ModelArchitecture
    status: TrainingStatus
    hyperparameters: dict
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class MLModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    architecture: ModelArchitecture
    accuracy: float | None
    precision: float | None
    recall: float | None
    f1: float | None
    mcc: float | None
    roc_auc: float | None
    false_positive_rate: float | None
    unknown_attack_recall: float | None
    training_time_seconds: float | None
    inference_time_ms_per_sample: float | None
    num_features: int | None
    num_classes: int | None
    created_at: datetime


class ExplanationRequest(BaseModel):
    model_id: uuid.UUID
    sample: list[float]
    method: str = Field(default="shap", pattern="^(shap|lime)$")
