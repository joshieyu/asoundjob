"""add priority to companies

Revision ID: d4a7c3e9f215
Revises: b539a9545442
Create Date: 2026-11-13

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d4a7c3e9f215"
down_revision = "b539a9545442"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("companies") as batch_op:
        batch_op.add_column(
            sa.Column(
                "priority",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("companies") as batch_op:
        batch_op.drop_column("priority")
