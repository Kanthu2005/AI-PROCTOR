"""009_exam_invitations

Revision ID: 009_exam_invitations
Revises: 008_safe_exam_browser_mode
Create Date: 2026-10-17 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '009_exam_invitations'
down_revision: Union[str, Sequence[str], None] = '008_safe_exam_browser_mode'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create exam_invitations table
    op.create_table(
        'exam_invitations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('assessment_id', sa.String(36), sa.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('candidate_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('candidate_invitation_id', sa.String(36), sa.ForeignKey('candidate_invitations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('recipient_email', sa.String(255), nullable=False),
        sa.Column('recipient_name', sa.String(255), nullable=False),
        sa.Column('invitation_token_hash', sa.String(64), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('opened_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('provider_message_id', sa.String(255), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_exam_invitations_id', 'exam_invitations', ['id'])
    op.create_index('ix_exam_invitations_assessment_id', 'exam_invitations', ['assessment_id'])
    op.create_index('ix_exam_invitations_candidate_id', 'exam_invitations', ['candidate_id'])
    op.create_index('ix_exam_invitations_candidate_invitation_id', 'exam_invitations', ['candidate_invitation_id'])
    op.create_index('ix_exam_invitations_recipient_email', 'exam_invitations', ['recipient_email'])
    op.create_index('ix_exam_invitations_invitation_token_hash', 'exam_invitations', ['invitation_token_hash'])
    op.create_index('ix_exam_invitations_status', 'exam_invitations', ['status'])
    op.create_index('ix_exam_invitations_expires_at', 'exam_invitations', ['expires_at'])
    op.create_index('ix_exam_invitations_provider_message_id', 'exam_invitations', ['provider_message_id'])

    # 2. Create invitation_delivery_attempts table
    op.create_table(
        'invitation_delivery_attempts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('invitation_id', sa.String(36), sa.ForeignKey('exam_invitations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('attempt_type', sa.String(50), nullable=False, server_default='INITIAL'),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('provider_message_id', sa.String(255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
    )
    op.create_index('ix_invitation_delivery_attempts_id', 'invitation_delivery_attempts', ['id'])
    op.create_index('ix_invitation_delivery_attempts_invitation_id', 'invitation_delivery_attempts', ['invitation_id'])


def downgrade() -> None:
    op.drop_table('invitation_delivery_attempts')
    op.drop_table('exam_invitations')
