"""add country to jobs

Revision ID: c1088da01d25
Revises: 5e567cb936ed
Create Date: 2026-08-30 07:48:57.581777

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision: str = 'c1088da01d25'
down_revision: str | None = '5e567cb936ed'
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('country', sa.Text(), nullable=True))
        batch_op.create_index(batch_op.f('ix_jobs_country'), ['country'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_jobs_country'))
        batch_op.drop_column('country')

