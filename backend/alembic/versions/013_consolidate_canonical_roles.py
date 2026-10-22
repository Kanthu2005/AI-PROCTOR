"""013_consolidate_canonical_roles

Revision ID: 013_consolidate_canonical_roles
Revises: 012_individual_result_release
Create Date: 2026-10-22 13:40:00.000000

Consolidates all legacy administrative, author, and proctor roles into RECRUITER.
Enforces exactly three canonical roles: PLATFORM_ADMIN, RECRUITER, CANDIDATE.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '013_consolidate_canonical_roles'
down_revision: Union[str, Sequence[str], None] = '012_individual_result_release'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Safely migrate legacy roles to RECRUITER without deleting any accounts
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE users 
            SET role = 'RECRUITER' 
            WHERE role IN ('QUESTION_AUTHOR', 'PROCTOR', 'ORG_ADMIN', 'ADMIN_RECRUITER')
            """
        )
    )


def downgrade() -> None:
    # Downgrade is a no-op to preserve consolidated role data safely
    pass
