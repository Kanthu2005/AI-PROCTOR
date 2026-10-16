"""004_attempt_receipt_and_constraints
 
Revision ID: 004_attempt_receipt_and_constraints
Revises: 003_add_question_topic
Create Date: 2026-10-16 22:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '004_attempt_receipt_and_constraints'
down_revision: Union[str, Sequence[str], None] = '003_add_question_topic'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('attempts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('submission_receipt', sa.String(64), nullable=True))
        batch_op.add_column(sa.Column('submission_type', sa.String(20), nullable=True, server_default='MANUAL'))
        batch_op.add_column(sa.Column('last_activity_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('current_question_id', sa.String(36), nullable=True))
        batch_op.create_index('ix_attempts_submission_receipt', ['submission_receipt'], unique=True)

    with op.batch_alter_table('attempt_answers', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_attempt_answer_question', ['attempt_id', 'question_id'])


def downgrade() -> None:
    with op.batch_alter_table('attempt_answers', schema=None) as batch_op:
        batch_op.drop_constraint('uq_attempt_answer_question', type_='unique')

    with op.batch_alter_table('attempts', schema=None) as batch_op:
        batch_op.drop_index('ix_attempts_submission_receipt')
        batch_op.drop_column('current_question_id')
        batch_op.drop_column('last_activity_at')
        batch_op.drop_column('submission_type')
        batch_op.drop_column('submission_receipt')
