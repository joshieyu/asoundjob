"""add is_active_override to jobs

Revision ID: a41c6b0e7d92
Revises: 19f87bb5f7ac
Create Date: 2026-09-12

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a41c6b0e7d92"
down_revision = "19f87bb5f7ac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.add_column(sa.Column("is_active_override", sa.Boolean(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.drop_column("is_active_override")
