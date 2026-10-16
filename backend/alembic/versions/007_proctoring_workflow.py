"""007_proctoring_workflow

Revision ID: 007_proctoring_workflow
Revises: 006_coding_submissions
Create Date: 2026-10-16 23:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '007_proctoring_workflow'
down_revision: Union[str, Sequence[str], None] = '006_coding_submissions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update proctoring_incidents with client_event_id, evidence_ref, is_deduplicated
    op.add_column('proctoring_incidents', sa.Column('client_event_id', sa.String(64), nullable=True))
    op.add_column('proctoring_incidents', sa.Column('evidence_ref', sa.String(255), nullable=True))
    op.add_column('proctoring_incidents', sa.Column('is_deduplicated', sa.Boolean(), server_default='0', nullable=False))
    op.create_index('ix_proctoring_incidents_client_event_id', 'proctoring_incidents', ['client_event_id'])

    # 2. Update attempts with risk_history, is_escalated, escalated_to_role
    op.add_column('attempts', sa.Column('risk_history', sa.JSON(), server_default='[]', nullable=True))
    op.add_column('attempts', sa.Column('is_escalated', sa.Boolean(), server_default='0', nullable=False))
    op.add_column('attempts', sa.Column('escalated_to_role', sa.String(50), nullable=True))

    # 3. Create proctor_review_decisions
    op.create_table(
        'proctor_review_decisions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('attempt_id', sa.String(36), sa.ForeignKey('attempts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('reviewer_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('decision', sa.String(50), nullable=False),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('is_escalated', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('escalated_to_role', sa.String(50), nullable=True),
        sa.Column('escalation_reason', sa.Text(), nullable=True),
        sa.Column('risk_score_snapshot', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('rule_version', sa.String(50), server_default='2026.1-explainable', nullable=False),
    )
    op.create_index('ix_proctor_review_decisions_attempt_id', 'proctor_review_decisions', ['attempt_id'])
    op.create_index('ix_proctor_review_decisions_reviewer_id', 'proctor_review_decisions', ['reviewer_id'])

    # 4. Create proctoring_evidence_access_audits
    op.create_table(
        'proctoring_evidence_access_audits',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('attempt_id', sa.String(36), sa.ForeignKey('attempts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('incident_id', sa.String(36), nullable=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('user_email', sa.String(255), nullable=True),
        sa.Column('user_role', sa.String(50), nullable=True),
        sa.Column('org_id', sa.String(36), nullable=True),
        sa.Column('action', sa.String(50), server_default='EVIDENCE_VIEW', nullable=False),
        sa.Column('ip_address', sa.String(100), nullable=True),
        sa.Column('user_agent', sa.String(255), nullable=True),
    )
    op.create_index('ix_proctoring_evidence_access_audits_attempt_id', 'proctoring_evidence_access_audits', ['attempt_id'])
    op.create_index('ix_proctoring_evidence_access_audits_user_id', 'proctoring_evidence_access_audits', ['user_id'])


def downgrade() -> None:
    op.drop_table('proctoring_evidence_access_audits')
    op.drop_table('proctor_review_decisions')
    op.drop_column('attempts', 'escalated_to_role')
    op.drop_column('attempts', 'is_escalated')
    op.drop_column('attempts', 'risk_history')
    op.drop_index('ix_proctoring_incidents_client_event_id', table_name='proctoring_incidents')
    op.drop_column('proctoring_incidents', 'is_deduplicated')
    op.drop_column('proctoring_incidents', 'evidence_ref')
    op.drop_column('proctoring_incidents', 'client_event_id')
