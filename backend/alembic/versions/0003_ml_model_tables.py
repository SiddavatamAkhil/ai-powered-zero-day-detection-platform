"""add training_runs and ml_models tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-02

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

ARCH_VALUES = ["cnn", "bilstm", "cnn_bilstm", "transformer", "autoencoder", "vae", "isolation_forest"]
STATUS_VALUES = ["queued", "running", "completed", "failed"]

arch_enum = postgresql.ENUM(*ARCH_VALUES, name="modelarchitecture")
status_enum = postgresql.ENUM(*STATUS_VALUES, name="trainingstatus")


def upgrade() -> None:
    arch_enum.create(op.get_bind(), checkfirst=True)
    status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "training_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("architecture", postgresql.ENUM(*ARCH_VALUES, name="modelarchitecture", create_type=False), nullable=False),
        sa.Column("status", postgresql.ENUM(*STATUS_VALUES, name="trainingstatus", create_type=False), nullable=False, server_default="queued"),
        sa.Column("hyperparameters", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.String(2000), nullable=True),
        sa.Column("triggered_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "ml_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("training_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("training_runs.id"), nullable=False),
        sa.Column("architecture", postgresql.ENUM(*ARCH_VALUES, name="modelarchitecture", create_type=False), nullable=False),
        sa.Column("artifact_path", sa.String(1000), nullable=False),
        sa.Column("openmax_path", sa.String(1000), nullable=True),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("precision", sa.Float(), nullable=True),
        sa.Column("recall", sa.Float(), nullable=True),
        sa.Column("f1", sa.Float(), nullable=True),
        sa.Column("mcc", sa.Float(), nullable=True),
        sa.Column("roc_auc", sa.Float(), nullable=True),
        sa.Column("false_positive_rate", sa.Float(), nullable=True),
        sa.Column("unknown_attack_recall", sa.Float(), nullable=True),
        sa.Column("training_time_seconds", sa.Float(), nullable=True),
        sa.Column("inference_time_ms_per_sample", sa.Float(), nullable=True),
        sa.Column("memory_usage_mb", sa.Float(), nullable=True),
        sa.Column("num_features", sa.Integer(), nullable=True),
        sa.Column("num_classes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("ml_models")
    op.drop_table("training_runs")
    status_enum.drop(op.get_bind(), checkfirst=True)
    arch_enum.drop(op.get_bind(), checkfirst=True)
