"""006_coding_submissions

Revision ID: 006_coding_submissions
Revises: 005_evaluation_and_descriptive_scoring
Create Date: 2026-10-16 23:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '006_coding_submissions'
down_revision: Union[str, Sequence[str], None] = '005_evaluation_and_descriptive_scoring'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'coding_submissions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('attempt_id', sa.String(36), sa.ForeignKey('attempts.id', ondelete='CASCADE'), nullable=True),
        sa.Column('question_id', sa.String(36), sa.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_version_id', sa.String(36), sa.ForeignKey('question_versions.id', ondelete='CASCADE'), nullable=True),
        sa.Column('candidate_email', sa.String(255), nullable=True),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('language', sa.String(50), nullable=False, server_default='python'),
        sa.Column('status', sa.String(32), nullable=False, server_default='QUEUED'),
        sa.Column('total_test_cases', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('passed_test_cases', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('score_awarded', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('max_marks', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('execution_time_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('memory_used_kb', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('results', sa.JSON(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True)
    )
    op.create_index('ix_coding_submissions_attempt_id', 'coding_submissions', ['attempt_id'])
    op.create_index('ix_coding_submissions_question_id', 'coding_submissions', ['question_id'])
    op.create_index('ix_coding_submissions_candidate_email', 'coding_submissions', ['candidate_email'])
    op.create_index('ix_coding_submissions_status', 'coding_submissions', ['status'])


def downgrade() -> None:
    op.drop_index('ix_coding_submissions_status', table_name='coding_submissions')
    op.drop_index('ix_coding_submissions_candidate_email', table_name='coding_submissions')
    op.drop_index('ix_coding_submissions_question_id', table_name='coding_submissions')
    op.drop_index('ix_coding_submissions_attempt_id', table_name='coding_submissions')
    op.drop_table('coding_submissions')
