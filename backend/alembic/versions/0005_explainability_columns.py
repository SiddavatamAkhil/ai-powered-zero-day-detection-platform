"""add explainability support columns to ml_models

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-03

"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ml_models", sa.Column("background_data_path", sa.String(1000), nullable=True))
    op.add_column("ml_models", sa.Column("feature_names", sa.JSON(), nullable=True))
    op.add_column("ml_models", sa.Column("class_names", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("ml_models", "class_names")
    op.drop_column("ml_models", "feature_names")
    op.drop_column("ml_models", "background_data_path")
