"""011_multilang_coding_and_result_release

Revision ID: 011_multilang_coding_and_result_release
Revises: 010_candidate_verification_and_policies
Create Date: 2026-10-21 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '011_multilang_coding_and_result_release'
down_revision: Union[str, Sequence[str], None] = '010_candidate_verification_and_policies'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create ResultReleasePolicy enum if PostgreSQL dialect
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'resultreleasepolicy') THEN
                    CREATE TYPE resultreleasepolicy AS ENUM ('MANUAL', 'SCHEDULED', 'AFTER_REVIEW');
                END IF;
            END$$;
        """)

    # 2. Add result release policy columns to assessments
    with op.batch_alter_table('assessments', schema=None) as batch_op:
        if bind.dialect.name == 'postgresql':
            batch_op.add_column(sa.Column(
                'result_release_policy',
                postgresql.ENUM('MANUAL', 'SCHEDULED', 'AFTER_REVIEW', name='resultreleasepolicy', create_type=False),
                nullable=False,
                server_default='MANUAL'
            ))
        else:
            batch_op.add_column(sa.Column(
                'result_release_policy',
                sa.String(50),
                nullable=False,
                server_default='MANUAL'
            ))
        batch_op.add_column(sa.Column('results_release_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('is_results_released', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('allow_candidate_answer_review', sa.Boolean(), nullable=False, server_default=sa.false()))

    # 3. Add code_drafts JSON column to attempt_answers
    with op.batch_alter_table('attempt_answers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('code_drafts', sa.JSON(), nullable=False, server_default='{}'))


def downgrade() -> None:
    with op.batch_alter_table('attempt_answers', schema=None) as batch_op:
        batch_op.drop_column('code_drafts')

    with op.batch_alter_table('assessments', schema=None) as batch_op:
        batch_op.drop_column('allow_candidate_answer_review')
        batch_op.drop_column('is_results_released')
        batch_op.drop_column('results_release_at')
        batch_op.drop_column('result_release_policy')

    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("DROP TYPE IF EXISTS resultreleasepolicy;")
