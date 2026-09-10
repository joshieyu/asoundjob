"""add requested_days to job_submissions

Revision ID: d3f5a72e9c14
Revises: c8e2f0a41b76
Create Date: 2026-09-03

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d3f5a72e9c14"
down_revision = "c8e2f0a41b76"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("job_submissions") as batch_op:
        batch_op.add_column(sa.Column("requested_days", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("job_submissions") as batch_op:
        batch_op.drop_column("requested_days")
