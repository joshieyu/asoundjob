"""add extra_careers_urls to companies

Revision ID: b7d4e91c2a35
Revises: a3f7c9e2b1d4
Create Date: 2026-09-03

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY

revision = "b7d4e91c2a35"
down_revision = "a3f7c9e2b1d4"
branch_labels = None
depends_on = None

StringList = sa.JSON().with_variant(ARRAY(sa.Text()), "postgresql")


def upgrade() -> None:
    with op.batch_alter_table("companies") as batch_op:
        batch_op.add_column(sa.Column("extra_careers_urls", StringList, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("companies") as batch_op:
        batch_op.drop_column("extra_careers_urls")
