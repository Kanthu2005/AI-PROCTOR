"""010_candidate_verification_and_policies

Revision ID: 010_candidate_verification_and_policies
Revises: 009_exam_invitations
Create Date: 2026-10-19 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '010_candidate_verification_and_policies'
down_revision: Union[str, Sequence[str], None] = '009_exam_invitations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add policy columns to assessment_rules
    with op.batch_alter_table('assessment_rules', schema=None) as batch_op:
        batch_op.add_column(sa.Column('mic_required', sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column('record_tab_switches', sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column('record_face_absence', sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column('record_multiple_faces', sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column('identity_match_enabled', sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column('identity_match_threshold', sa.Float(), nullable=False, server_default='0.70'))
        batch_op.add_column(sa.Column('require_manual_approval', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('warning_threshold', sa.Integer(), nullable=False, server_default='3'))
        batch_op.add_column(sa.Column('policy_version', sa.Integer(), nullable=False, server_default='1'))

    # 2. Add descriptive_details to question_versions
    with op.batch_alter_table('question_versions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('descriptive_details', sa.JSON(), nullable=False, server_default='{}'))

    # 3. Add verification_data & manual_approval to candidate_invitations
    with op.batch_alter_table('candidate_invitations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('verification_data', sa.JSON(), nullable=False, server_default='{}'))
        batch_op.add_column(sa.Column('manual_approval_granted', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('manual_approval_by', sa.String(36), nullable=True))
        batch_op.add_column(sa.Column('manual_approval_reason', sa.Text(), nullable=True))

    # 4. Create assessment_policy_audits table
    op.create_table(
        'assessment_policy_audits',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('assessment_id', sa.String(36), sa.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('changed_by_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('policy_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('previous_rules', sa.JSON(), nullable=False),
        sa.Column('new_rules', sa.JSON(), nullable=False),
    )
    op.create_index('ix_assessment_policy_audits_id', 'assessment_policy_audits', ['id'])
    op.create_index('ix_assessment_policy_audits_assessment_id', 'assessment_policy_audits', ['assessment_id'])

    # 5. Role consolidation: map legacy roles to ADMIN_RECRUITER
    bind = op.get_bind()
    bind.execute(
        sa.text("UPDATE users SET role = 'ADMIN_RECRUITER' WHERE role IN ('RECRUITER', 'ORG_ADMIN', 'QUESTION_AUTHOR', 'PROCTOR')")
    )


def downgrade() -> None:
    op.drop_table('assessment_policy_audits')
    with op.batch_alter_table('candidate_invitations', schema=None) as batch_op:
        batch_op.drop_column('manual_approval_reason')
        batch_op.drop_column('manual_approval_by')
        batch_op.drop_column('manual_approval_granted')
        batch_op.drop_column('verification_data')
    with op.batch_alter_table('question_versions', schema=None) as batch_op:
        batch_op.drop_column('descriptive_details')
    with op.batch_alter_table('assessment_rules', schema=None) as batch_op:
        batch_op.drop_column('policy_version')
        batch_op.drop_column('warning_threshold')
        batch_op.drop_column('require_manual_approval')
        batch_op.drop_column('identity_match_threshold')
        batch_op.drop_column('identity_match_enabled')
        batch_op.drop_column('record_multiple_faces')
        batch_op.drop_column('record_face_absence')
        batch_op.drop_column('record_tab_switches')
        batch_op.drop_column('mic_required')
