"""add scrape_blocked to companies

Revision ID: 19f87bb5f7ac
Revises: d3f5a72e9c14
Create Date: 2026-09-08

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "19f87bb5f7ac"
down_revision = "d3f5a72e9c14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("companies") as batch_op:
        batch_op.add_column(
            sa.Column(
                "scrape_blocked",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("companies") as batch_op:
        batch_op.drop_column("scrape_blocked")
