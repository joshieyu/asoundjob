"""add careers_url, website_url and category to company_suggestions

Revision ID: c8a4e2f7b915
Revises: b5e3d8a1c602
Create Date: 2026-11-16

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c8a4e2f7b915"
down_revision = "b5e3d8a1c602"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("company_suggestions") as batch_op:
        batch_op.add_column(sa.Column("careers_url", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("website_url", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("category", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("company_suggestions") as batch_op:
        batch_op.drop_column("category")
        batch_op.drop_column("website_url")
        batch_op.drop_column("careers_url")
