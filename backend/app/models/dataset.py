"""
Dataset and DatasetClass ORM models.

DatasetClass is the structural enforcement point for open-set recognition:
every class label discovered in an uploaded dataset gets a row here with a
`split` of KNOWN or UNKNOWN_HOLDOUT.

Phase 3 training queries only KNOWN classes.
Phase 4 OpenMax evaluation can use both KNOWN and UNKNOWN_HOLDOUT classes.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class DatasetStatus(str, enum.Enum):
    """
    Current processing status of a dataset.
    """

    UPLOADED = "uploaded"
    PROFILED = "profiled"
    CLEANED = "cleaned"
    FEATURE_ENGINEERED = "feature_engineered"
    SPLIT_CONFIGURED = "split_configured"
    FAILED = "failed"


class ClassSplit(str, enum.Enum):
    """
    Open-set split for dataset classes.
    """

    KNOWN = "known"
    UNKNOWN_HOLDOUT = "unknown_holdout"


class Dataset(Base):
    """
    Main dataset table.
    """

    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    original_filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    raw_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    cleaned_path: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    features_path: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    scaler_path: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    label_column: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    num_rows: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    num_features: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    status: Mapped[DatasetStatus] = mapped_column(
        Enum(
            DatasetStatus,
            name="datasetstatus",
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
        ),
        default=DatasetStatus.UPLOADED,
        nullable=False,
    )

    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # IMPORTANT:
    # selectin prevents the MissingGreenlet error when FastAPI
    # serializes Dataset objects in async SQLAlchemy.
    classes: Mapped[list["DatasetClass"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class DatasetClass(Base):
    """
    Individual class/label discovered inside a dataset.
    """

    __tablename__ = "dataset_classes"

    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "class_name",
            name="uq_dataset_class",
        ),
    )

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

    class_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    sample_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    split: Mapped[ClassSplit] = mapped_column(
        Enum(
            ClassSplit,
            name="classsplit",
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
        ),
        default=ClassSplit.KNOWN,
        nullable=False,
    )

    # Benign/normal traffic should never be held out.
    is_benign: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    dataset: Mapped["Dataset"] = relationship(
        back_populates="classes",
    )