"""008_safe_exam_browser_mode

Revision ID: 008_safe_exam_browser_mode
Revises: 007_proctoring_workflow
Create Date: 2026-10-17 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '008_safe_exam_browser_mode'
down_revision: Union[str, Sequence[str], None] = '007_proctoring_workflow'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update assessment_rules with SEB configuration
    op.add_column('assessment_rules', sa.Column('seb_required', sa.Boolean(), server_default='0', nullable=False))
    op.add_column('assessment_rules', sa.Column('seb_config_key', sa.String(64), nullable=True))
    op.add_column('assessment_rules', sa.Column('seb_browser_exam_keys', sa.JSON(), server_default='[]', nullable=False))
    op.add_column('assessment_rules', sa.Column('seb_allow_quit', sa.Boolean(), server_default='1', nullable=False))
    op.add_column('assessment_rules', sa.Column('seb_quit_url', sa.String(255), nullable=True))
    op.add_column('assessment_rules', sa.Column('seb_quit_password_hash', sa.String(128), nullable=True))

    # 2. Update attempts with SEB verification evidence
    op.add_column('attempts', sa.Column('seb_verified', sa.Boolean(), server_default='0', nullable=False))
    op.add_column('attempts', sa.Column('seb_client_platform', sa.String(50), nullable=True))
    op.add_column('attempts', sa.Column('seb_verification_mechanism', sa.String(50), nullable=True))
    op.add_column('attempts', sa.Column('seb_verified_at', sa.DateTime(), nullable=True))
    op.add_column('attempts', sa.Column('seb_client_user_agent', sa.String(255), nullable=True))


def downgrade() -> None:
    # Drop from attempts
    op.drop_column('attempts', 'seb_client_user_agent')
    op.drop_column('attempts', 'seb_verified_at')
    op.drop_column('attempts', 'seb_verification_mechanism')
    op.drop_column('attempts', 'seb_client_platform')
    op.drop_column('attempts', 'seb_verified')

    # Drop from assessment_rules
    op.drop_column('assessment_rules', 'seb_quit_password_hash')
    op.drop_column('assessment_rules', 'seb_quit_url')
    op.drop_column('assessment_rules', 'seb_allow_quit')
    op.drop_column('assessment_rules', 'seb_browser_exam_keys')
    op.drop_column('assessment_rules', 'seb_config_key')
    op.drop_column('assessment_rules', 'seb_required')
