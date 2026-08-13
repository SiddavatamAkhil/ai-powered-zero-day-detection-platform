"""add datasets and dataset_classes tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-02

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

dataset_status_enum = postgresql.ENUM(
    "uploaded", "profiled", "cleaned", "feature_engineered", "split_configured", "failed",
    name="datasetstatus",
)
class_split_enum = postgresql.ENUM("known", "unknown_holdout", name="classsplit")


def upgrade() -> None:
    dataset_status_enum.create(op.get_bind(), checkfirst=True)
    class_split_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("raw_path", sa.String(1000), nullable=False),
        sa.Column("cleaned_path", sa.String(1000), nullable=True),
        sa.Column("features_path", sa.String(1000), nullable=True),
        sa.Column("scaler_path", sa.String(1000), nullable=True),
        sa.Column("label_column", sa.String(255), nullable=False),
        sa.Column("num_rows", sa.Integer(), nullable=True),
        sa.Column("num_features", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "uploaded", "profiled", "cleaned", "feature_engineered", "split_configured", "failed",
                name="datasetstatus", create_type=False,
            ),
            nullable=False, server_default="uploaded",
        ),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "dataset_classes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("class_name", sa.String(255), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "split",
            postgresql.ENUM("known", "unknown_holdout", name="classsplit", create_type=False),
            nullable=False, server_default="known",
        ),
        sa.Column("is_benign", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("dataset_id", "class_name", name="uq_dataset_class"),
    )


def downgrade() -> None:
    op.drop_table("dataset_classes")
    op.drop_table("datasets")
    class_split_enum.drop(op.get_bind(), checkfirst=True)
    dataset_status_enum.drop(op.get_bind(), checkfirst=True)
