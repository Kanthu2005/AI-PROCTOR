"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-10 22:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. organizations
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('domain', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
    )
    op.create_index('ix_organizations_id', 'organizations', ['id'])
    op.create_index('ix_organizations_slug', 'organizations', ['slug'])

    # 2. users
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('org_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_role', 'users', ['role'])

    # 3. questions
    op.create_table(
        'questions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('org_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_type', sa.String(50), nullable=False),
        sa.Column('current_version_number', sa.Integer(), nullable=False, default=1),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
    )
    op.create_index('ix_questions_id', 'questions', ['id'])
    op.create_index('ix_questions_org_id', 'questions', ['org_id'])
    op.create_index('ix_questions_question_type', 'questions', ['question_type'])

    # 4. question_versions
    op.create_table(
        'question_versions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('question_id', sa.String(36), sa.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('question_type', sa.String(50), nullable=False),
        sa.Column('difficulty', sa.String(50), nullable=False),
        sa.Column('default_positive_marks', sa.Float(), nullable=False, default=1.0),
        sa.Column('default_negative_marks', sa.Float(), nullable=False, default=0.0),
        sa.Column('tags', sa.JSON(), nullable=False),
        sa.Column('options', sa.JSON(), nullable=False),
        sa.Column('coding_details', sa.JSON(), nullable=False),
        sa.Column('sql_details', sa.JSON(), nullable=False),
        sa.Column('is_published', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_by_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_question_versions_id', 'question_versions', ['id'])
    op.create_index('ix_question_versions_question_id', 'question_versions', ['question_id'])
    op.create_index('ix_question_versions_version_number', 'question_versions', ['version_number'])

    # 5. assessments
    op.create_table(
        'assessments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('org_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('total_duration_minutes', sa.Integer(), nullable=False, default=60),
        sa.Column('passing_percentage', sa.Float(), nullable=False, default=50.0),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_by_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_assessments_id', 'assessments', ['id'])
    op.create_index('ix_assessments_org_id', 'assessments', ['org_id'])

    # 6. assessment_rules
    op.create_table(
        'assessment_rules',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('assessment_id', sa.String(36), sa.ForeignKey('assessments.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('navigation_mode', sa.String(50), nullable=False),
        sa.Column('section_wise_breaks', sa.Boolean(), nullable=False, default=False),
        sa.Column('randomize_questions', sa.Boolean(), nullable=False, default=False),
        sa.Column('randomize_options', sa.Boolean(), nullable=False, default=False),
        sa.Column('negative_marking_enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('negative_marking_formula', sa.String(255), nullable=False),
        sa.Column('full_screen_enforced', sa.Boolean(), nullable=False, default=True),
        sa.Column('max_tab_switches_allowed', sa.Integer(), nullable=False, default=3),
        sa.Column('webcam_proctoring_enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('devtools_block_enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('copy_paste_blocked', sa.Boolean(), nullable=False, default=True),
    )
    op.create_index('ix_assessment_rules_id', 'assessment_rules', ['id'])

    # 7. sections
    op.create_table(
        'sections',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('assessment_id', sa.String(36), sa.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False, default=0),
        sa.Column('cut_off_marks', sa.Float(), nullable=False, default=0.0),
    )
    op.create_index('ix_sections_id', 'sections', ['id'])
    op.create_index('ix_sections_assessment_id', 'sections', ['assessment_id'])

    # 8. section_questions
    op.create_table(
        'section_questions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('section_id', sa.String(36), sa.ForeignKey('sections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_id', sa.String(36), sa.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_version_id', sa.String(36), sa.ForeignKey('question_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('positive_marks', sa.Float(), nullable=False, default=1.0),
        sa.Column('negative_marks', sa.Float(), nullable=False, default=0.0),
        sa.Column('order_index', sa.Integer(), nullable=False, default=0),
    )
    op.create_index('ix_section_questions_id', 'section_questions', ['id'])
    op.create_index('ix_section_questions_section_id', 'section_questions', ['section_id'])
    op.create_index('ix_section_questions_question_id', 'section_questions', ['question_id'])
    op.create_index('ix_section_questions_question_version_id', 'section_questions', ['question_version_id'])

    # 9. candidate_invitations
    op.create_table(
        'candidate_invitations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('assessment_id', sa.String(36), sa.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('org_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('invitation_token', sa.String(128), unique=True, nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('system_check_passed', sa.Boolean(), nullable=False, default=False),
        sa.Column('verified_face_reference', sa.Text(), nullable=True),
    )
    op.create_index('ix_candidate_invitations_id', 'candidate_invitations', ['id'])
    op.create_index('ix_candidate_invitations_assessment_id', 'candidate_invitations', ['assessment_id'])
    op.create_index('ix_candidate_invitations_org_id', 'candidate_invitations', ['org_id'])
    op.create_index('ix_candidate_invitations_email', 'candidate_invitations', ['email'])
    op.create_index('ix_candidate_invitations_invitation_token', 'candidate_invitations', ['invitation_token'])
    op.create_index('ix_candidate_invitations_status', 'candidate_invitations', ['status'])

    # 10. attempts
    op.create_table(
        'attempts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('invitation_id', sa.String(36), sa.ForeignKey('candidate_invitations.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('assessment_id', sa.String(36), sa.ForeignKey('assessments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('candidate_email', sa.String(255), nullable=False),
        sa.Column('candidate_name', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('server_expiry_at', sa.DateTime(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('total_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('total_max_marks', sa.Float(), nullable=False, default=0.0),
        sa.Column('percentage', sa.Float(), nullable=False, default=0.0),
        sa.Column('is_passed', sa.Boolean(), nullable=False, default=False),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('percentile', sa.Float(), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=False, default=0.0),
        sa.Column('risk_level', sa.String(50), nullable=False),
        sa.Column('human_review_status', sa.String(50), nullable=False),
        sa.Column('proctor_notes', sa.Text(), nullable=True),
        sa.Column('tab_switch_count', sa.Integer(), nullable=False, default=0),
        sa.Column('disqualified_reason', sa.String(255), nullable=True),
    )
    op.create_index('ix_attempts_id', 'attempts', ['id'])
    op.create_index('ix_attempts_assessment_id', 'attempts', ['assessment_id'])
    op.create_index('ix_attempts_status', 'attempts', ['status'])
    op.create_index('ix_attempts_server_expiry_at', 'attempts', ['server_expiry_at'])
    op.create_index('ix_attempts_risk_level', 'attempts', ['risk_level'])
    op.create_index('ix_attempts_human_review_status', 'attempts', ['human_review_status'])

    # 11. attempt_answers
    op.create_table(
        'attempt_answers',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('attempt_id', sa.String(36), sa.ForeignKey('attempts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_id', sa.String(36), sa.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_version_id', sa.String(36), sa.ForeignKey('question_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('section_id', sa.String(36), sa.ForeignKey('sections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('selected_option_ids', sa.JSON(), nullable=False),
        sa.Column('text_response', sa.Text(), nullable=True),
        sa.Column('code_response', sa.Text(), nullable=True),
        sa.Column('language', sa.String(50), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('marks_awarded', sa.Float(), nullable=False, default=0.0),
        sa.Column('execution_result', sa.JSON(), nullable=False),
        sa.Column('time_spent_seconds', sa.Integer(), nullable=False, default=0),
        sa.Column('is_flagged_for_review', sa.Boolean(), nullable=False, default=False),
    )
    op.create_index('ix_attempt_answers_id', 'attempt_answers', ['id'])
    op.create_index('ix_attempt_answers_attempt_id', 'attempt_answers', ['attempt_id'])
    op.create_index('ix_attempt_answers_question_id', 'attempt_answers', ['question_id'])
    op.create_index('ix_attempt_answers_question_version_id', 'attempt_answers', ['question_version_id'])
    op.create_index('ix_attempt_answers_section_id', 'attempt_answers', ['section_id'])

    # 12. proctoring_incidents
    op.create_table(
        'proctoring_incidents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('attempt_id', sa.String(36), sa.ForeignKey('attempts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(50), nullable=False),
        sa.Column('risk_points', sa.Float(), nullable=False, default=5.0),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('snapshot_data', sa.String(500), nullable=True),
        sa.Column('occurred_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_proctoring_incidents_id', 'proctoring_incidents', ['id'])
    op.create_index('ix_proctoring_incidents_attempt_id', 'proctoring_incidents', ['attempt_id'])
    op.create_index('ix_proctoring_incidents_event_type', 'proctoring_incidents', ['event_type'])


def downgrade() -> None:
    op.drop_table('proctoring_incidents')
    op.drop_table('attempt_answers')
    op.drop_table('attempts')
    op.drop_table('candidate_invitations')
    op.drop_table('section_questions')
    op.drop_table('sections')
    op.drop_table('assessment_rules')
    op.drop_table('assessments')
    op.drop_table('question_versions')
    op.drop_table('questions')
    op.drop_table('users')
    op.drop_table('organizations')
