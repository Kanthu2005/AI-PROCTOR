"""005_eval_and_scoring

Revision ID: 005_eval_and_scoring
Revises: 004_attempt_constraints
Create Date: 2026-10-16 23:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '005_eval_and_scoring'
down_revision: Union[str, Sequence[str], None] = '004_attempt_constraints'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('attempts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('evaluation_status', sa.String(32), nullable=True, server_default='PENDING'))
        batch_op.add_column(sa.Column('section_scores', sa.JSON(), nullable=True))
        batch_op.create_index('ix_attempts_evaluation_status', ['evaluation_status'], unique=False)

    with op.batch_alter_table('attempt_answers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('reviewer_comments', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('evaluated_by_id', sa.String(36), nullable=True))
        batch_op.add_column(sa.Column('evaluated_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('is_manually_evaluated', sa.Boolean(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('ai_suggested_marks', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('ai_suggestion_rationale', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('ai_suggestion_confidence', sa.Float(), nullable=True))

    with op.batch_alter_table('assessment_rules', schema=None) as batch_op:
        batch_op.add_column(sa.Column('multiple_select_policy', sa.String(50), nullable=True, server_default='PARTIAL_WITH_PENALTY'))


def downgrade() -> None:
    with op.batch_alter_table('assessment_rules', schema=None) as batch_op:
        batch_op.drop_column('multiple_select_policy')

    with op.batch_alter_table('attempt_answers', schema=None) as batch_op:
        batch_op.drop_column('ai_suggestion_confidence')
        batch_op.drop_column('ai_suggestion_rationale')
        batch_op.drop_column('ai_suggested_marks')
        batch_op.drop_column('is_manually_evaluated')
        batch_op.drop_column('evaluated_at')
        batch_op.drop_column('evaluated_by_id')
        batch_op.drop_column('reviewer_comments')

    with op.batch_alter_table('attempts', schema=None) as batch_op:
        batch_op.drop_index('ix_attempts_evaluation_status')
        batch_op.drop_column('section_scores')
        batch_op.drop_column('evaluation_status')
