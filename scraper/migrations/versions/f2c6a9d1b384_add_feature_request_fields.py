"""add feature_days and feature_note to job_feedback

Revision ID: f2c6a9d1b384
Revises: e8b1f4c2a7d3
Create Date: 2026-11-16

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f2c6a9d1b384"
down_revision = "e8b1f4c2a7d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("job_feedback") as batch_op:
        batch_op.add_column(sa.Column("feature_days", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("feature_note", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("job_feedback") as batch_op:
        batch_op.drop_column("feature_note")
        batch_op.drop_column("feature_days")
