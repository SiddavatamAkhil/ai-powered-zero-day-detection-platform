"""
Pydantic schemas for dataset upload, profiling, and open-set split config.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.dataset import ClassSplit, DatasetStatus


class DatasetClassRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    class_name: str
    sample_count: int
    split: ClassSplit
    is_benign: bool


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    original_filename: str
    label_column: str
    num_rows: int | None
    num_features: int | None
    status: DatasetStatus
    created_at: datetime
    classes: list[DatasetClassRead] = []


class DatasetUploadMeta(BaseModel):
    """Form fields accompanying the multipart file upload."""
    name: str = Field(min_length=1, max_length=255)
    label_column: str = Field(min_length=1, max_length=255, description="Name of the column containing the attack/benign label")


class ClassSplitAssignment(BaseModel):
    class_name: str
    split: ClassSplit


class OpenSetSplitConfig(BaseModel):
    """
    Body for POST /datasets/{id}/open-set-split.

    Client sends the desired split per class. Benign/normal traffic is
    validated server-side to always remain KNOWN — holding out benign
    traffic would make "unknown attack recall" meaningless.
    """
    assignments: list[ClassSplitAssignment]


class DatasetProfile(BaseModel):
    """Shape of the profiling document stored in MongoDB."""
    dataset_id: str
    columns: list[str]
    dtypes: dict[str, str]
    missing_value_pct: dict[str, float]
    class_distribution: dict[str, int]
    numeric_summary: dict[str, dict[str, float]]  # per-column min/max/mean/std
    generated_at: datetime
