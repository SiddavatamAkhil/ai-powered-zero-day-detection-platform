"""
MLModel: a trained model artifact + its evaluation metrics.
TrainingRun: one training job (may produce zero or one MLModel — failed
runs produce none).

Kept separate from the `ml/` package's in-memory objects deliberately —
these are persistence records (paths + metrics), not the model itself.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ModelArchitecture(str, enum.Enum):
    CNN = "cnn"
    BILSTM = "bilstm"
    CNN_BILSTM = "cnn_bilstm"
    TRANSFORMER = "transformer"
    AUTOENCODER = "autoencoder"
    VAE = "vae"
    ISOLATION_FOREST = "isolation_forest"


class TrainingStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Explicitly use enum VALUES rather than Python enum member names.
#
# PostgreSQL currently contains:
#   cnn
#   bilstm
#   cnn_bilstm
#   transformer
#   autoencoder
#   vae
#   isolation_forest
#
# Without values_callable, SQLAlchemy would try to insert "CNN"
# instead of "cnn", causing:
#   invalid input value for enum modelarchitecture: "CNN"
MODEL_ARCHITECTURE_ENUM = Enum(
    ModelArchitecture,
    name="modelarchitecture",
    values_callable=lambda enum_class: [
        member.value for member in enum_class
    ],
)


class TrainingRun(Base):
    __tablename__ = "training_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id"),
        nullable=False,
    )

    architecture: Mapped[ModelArchitecture] = mapped_column(
        MODEL_ARCHITECTURE_ENUM,
        nullable=False,
    )

    status: Mapped[TrainingStatus] = mapped_column(
        Enum(
            TrainingStatus,
            name="trainingstatus",
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
        ),
        default=TrainingStatus.QUEUED,
        nullable=False,
    )

    hyperparameters: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
    )

    error_message: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    triggered_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    model: Mapped["MLModel | None"] = relationship(
        back_populates="training_run",
        uselist=False,
    )


class MLModel(Base):
    __tablename__ = "ml_models"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    training_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("training_runs.id"),
        nullable=False,
    )

    architecture: Mapped[ModelArchitecture] = mapped_column(
        MODEL_ARCHITECTURE_ENUM,
        nullable=False,
    )

    artifact_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    openmax_path: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    background_data_path: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    feature_names: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    class_names: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Evaluation metrics
    # Flattened columns allow the model-comparison dashboard
    # to sort and filter using normal SQL queries.

    accuracy: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    precision: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    recall: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    f1: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    mcc: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    roc_auc: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    false_positive_rate: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    unknown_attack_recall: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    training_time_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    inference_time_ms_per_sample: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    memory_usage_mb: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    num_features: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    num_classes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    training_run: Mapped["TrainingRun"] = relationship(
        back_populates="model",
    )