"""add featured_at, featured_until and featured_note to jobs

Revision ID: e8b1f4c2a7d3
Revises: d4a7c3e9f215
Create Date: 2026-11-16

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e8b1f4c2a7d3"
down_revision = "d4a7c3e9f215"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.add_column(sa.Column("featured_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("featured_until", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("featured_note", sa.Text(), nullable=True))
        batch_op.create_index("ix_jobs_featured_until", ["featured_until"])


def downgrade() -> None:
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.drop_index("ix_jobs_featured_until")
        batch_op.drop_column("featured_note")
        batch_op.drop_column("featured_until")
        batch_op.drop_column("featured_at")
