"""add consecutive_failures to companies

Revision ID: b539a9545442
Revises: c73f2a5d81e0
Create Date: 2026-09-22

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b539a9545442"
down_revision = "c73f2a5d81e0"
branch_labels = None
depends_on = None


def _consecutive_failures(rows) -> dict[int, int]:
    counts: dict[int, int] = {}
    settled: set[int] = set()
    for company_id, status in rows:
        if company_id is None or company_id in settled:
            continue
        if status == "failed":
            counts[company_id] = counts.get(company_id, 0) + 1
        else:
            settled.add(company_id)
    return counts


def upgrade() -> None:
    with op.batch_alter_table("companies") as batch_op:
        batch_op.add_column(
            sa.Column(
                "consecutive_failures",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT company_id, status FROM scrape_log "
            "ORDER BY company_id, started_at DESC, id DESC"
        )
    ).fetchall()
    counts = _consecutive_failures(rows)
    if counts:
        bind.execute(
            sa.text(
                "UPDATE companies SET consecutive_failures = :count WHERE id = :company_id"
            ),
            [
                {"count": count, "company_id": company_id}
                for company_id, count in counts.items()
            ],
        )


def downgrade() -> None:
    with op.batch_alter_table("companies") as batch_op:
        batch_op.drop_column("consecutive_failures")
