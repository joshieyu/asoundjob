"""add feedback tables and job overrides

Revision ID: a3f7c9e2b1d4
Revises: c1088da01d25
Create Date: 2026-09-02 00:00:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql

revision: str = 'a3f7c9e2b1d4'
down_revision: str | None = 'c1088da01d25'
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table('job_feedback',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('suggested_categories', sa.JSON().with_variant(postgresql.ARRAY(Text()), 'postgresql'), nullable=True),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('submitter_email', sa.Text(), nullable=True),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reviewed_by', sa.Text(), nullable=True),
    sa.Column('reject_reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('job_feedback', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_job_feedback_job_id'), ['job_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_job_feedback_kind'), ['kind'], unique=False)
        batch_op.create_index(batch_op.f('ix_job_feedback_status'), ['status'], unique=False)

    op.create_table('site_feedback',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('company_name', sa.Text(), nullable=True),
    sa.Column('company_url', sa.Text(), nullable=True),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('submitter_email', sa.Text(), nullable=True),
    sa.Column('page_path', sa.Text(), nullable=True),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reviewed_by', sa.Text(), nullable=True),
    sa.Column('reject_reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('site_feedback', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_site_feedback_kind'), ['kind'], unique=False)
        batch_op.create_index(batch_op.f('ix_site_feedback_status'), ['status'], unique=False)

    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'categories_override',
                sa.JSON().with_variant(postgresql.ARRAY(Text()), 'postgresql'),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column('is_audio_related_override', sa.Boolean(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_column('is_audio_related_override')
        batch_op.drop_column('categories_override')

    with op.batch_alter_table('site_feedback', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_site_feedback_status'))
        batch_op.drop_index(batch_op.f('ix_site_feedback_kind'))
    op.drop_table('site_feedback')

    with op.batch_alter_table('job_feedback', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_job_feedback_status'))
        batch_op.drop_index(batch_op.f('ix_job_feedback_kind'))
        batch_op.drop_index(batch_op.f('ix_job_feedback_job_id'))
    op.drop_table('job_feedback')
