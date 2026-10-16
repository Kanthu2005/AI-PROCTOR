"""003_add_question_topic

Revision ID: 003_add_question_topic
Revises: 002_recruiter_workflow
Create Date: 2026-10-16 22:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '003_add_question_topic'
down_revision: Union[str, Sequence[str], None] = '002_recruiter_workflow'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('question_versions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('topic', sa.String(100), nullable=True, server_default='General'))
        batch_op.create_index('ix_question_versions_topic', ['topic'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('question_versions', schema=None) as batch_op:
        batch_op.drop_index('ix_question_versions_topic')
        batch_op.drop_column('topic')
