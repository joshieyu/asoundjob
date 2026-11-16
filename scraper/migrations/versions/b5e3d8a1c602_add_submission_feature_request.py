"""add feature request fields to job_submissions

Revision ID: b5e3d8a1c602
Revises: f2c6a9d1b384
Create Date: 2026-11-16

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b5e3d8a1c602"
down_revision = "f2c6a9d1b384"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("job_submissions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "feature_requested", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )
        batch_op.add_column(sa.Column("feature_days", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("feature_note", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("job_submissions") as batch_op:
        batch_op.drop_column("feature_note")
        batch_op.drop_column("feature_days")
        batch_op.drop_column("feature_requested")
