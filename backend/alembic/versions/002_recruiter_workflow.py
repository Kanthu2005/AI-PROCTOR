"""002_recruiter_workflow

Revision ID: 002_recruiter_workflow
Revises: 001_initial_schema
Create Date: 2026-10-10 22:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_recruiter_workflow'
down_revision: Union[str, Sequence[str], None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add lifecycle columns to assessments table
    with op.batch_alter_table('assessments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(50), nullable=False, server_default='DRAFT'))
        batch_op.add_column(sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('total_marks', sa.Float(), nullable=False, server_default='100.0'))
        batch_op.add_column(sa.Column('start_time', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('end_time', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('result_publication_policy', sa.String(50), nullable=False, server_default='IMMEDIATE'))
        batch_op.create_index('ix_assessments_status', ['status'], unique=False)

    # 2. Add explanation and review_status to question_versions table
    with op.batch_alter_table('question_versions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('explanation', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('review_status', sa.String(50), nullable=False, server_default='APPROVED'))
        batch_op.create_index('ix_question_versions_review_status', ['review_status'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('question_versions', schema=None) as batch_op:
        batch_op.drop_index('ix_question_versions_review_status')
        batch_op.drop_column('review_status')
        batch_op.drop_column('explanation')

    with op.batch_alter_table('assessments', schema=None) as batch_op:
        batch_op.drop_index('ix_assessments_status')
        batch_op.drop_column('result_publication_policy')
        batch_op.drop_column('max_attempts')
        batch_op.drop_column('end_time')
        batch_op.drop_column('start_time')
        batch_op.drop_column('total_marks')
        batch_op.drop_column('version')
        batch_op.drop_column('status')
