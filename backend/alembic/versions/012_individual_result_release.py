"""012_individual_result_release

Revision ID: 012_individual_result_release
Revises: 011_multilang_coding_and_result_release
Create Date: 2026-10-21 00:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '012_individual_result_release'
down_revision: Union[str, Sequence[str], None] = '011_multilang_coding_and_result_release'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('attempts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_result_released', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('result_released_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('result_decision', sa.String(32), nullable=True))
        batch_op.add_column(sa.Column('recruiter_feedback', sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('attempts', schema=None) as batch_op:
        batch_op.drop_column('recruiter_feedback')
        batch_op.drop_column('result_decision')
        batch_op.drop_column('result_released_at')
        batch_op.drop_column('is_result_released')
