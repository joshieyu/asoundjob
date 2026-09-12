"""add community_links to companies and the company_suggestions table

Revision ID: c73f2a5d81e0
Revises: a41c6b0e7d92
Create Date: 2026-09-12

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c73f2a5d81e0"
down_revision = "a41c6b0e7d92"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("companies") as batch_op:
        batch_op.add_column(sa.Column("community_links", sa.JSON(), nullable=True))

    op.create_table(
        "company_suggestions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("links", sa.JSON(), nullable=True),
        sa.Column("headquarters", sa.Text(), nullable=True),
        sa.Column("founded", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("submitter_email", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.Text(), nullable=True),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_company_suggestions_company_id", "company_suggestions", ["company_id"]
    )
    op.create_index("ix_company_suggestions_status", "company_suggestions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_company_suggestions_status", table_name="company_suggestions")
    op.drop_index("ix_company_suggestions_company_id", table_name="company_suggestions")
    op.drop_table("company_suggestions")
    with op.batch_alter_table("companies") as batch_op:
        batch_op.drop_column("community_links")
