import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import dotenv_values

from app.models.user import User, Role, Organization
from app.models.question import Question, QuestionVersion, QuestionType, DifficultyLevel
from app.models.assessment import Assessment, Section, SectionQuestion
from app.models.attempt import Attempt, AttemptAnswer, AttemptStatus
from app.models.candidate import CandidateInvitation, CandidateStatus
from app.models.invitation import ExamInvitation, ExamInvitationStatus
from datetime import datetime, timezone, timedelta

from app.database import resolve_database_url

# Load PostgreSQL database configuration with cascading fallbacks
env_dict = dotenv_values(".env") if os.path.exists(".env") else {}
pg_url = (
    os.environ.get("POSTGRES_DATABASE_URL")
    or os.environ.get("TEST_DATABASE_URL")
    or (os.environ.get("DATABASE_URL") if os.environ.get("DATABASE_URL", "").startswith("postgres") else None)
    or env_dict.get("POSTGRES_DATABASE_URL")
    or env_dict.get("DATABASE_URL")
    or "postgresql://postgres:Kanthu%402005@localhost:5432/aiprotector"
)
resolved_pg_url = resolve_database_url(pg_url)

pg_engine = create_engine(resolved_pg_url)
PgSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)


@pytest.fixture(autouse=True)
def require_postgresql_connection():
    """Skip PostgreSQL tests gracefully if the database server is not reachable with current credentials."""
    try:
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL integration test database unavailable: {exc}")


def test_postgresql_dialect_active():
    """Verify dialect is strictly postgresql."""
    assert pg_engine.dialect.name == "postgresql"
    with pg_engine.connect() as conn:
        res = conn.execute(text("SELECT 1")).scalar()
        assert res == 1


def test_postgresql_tables_exist():
    """Verify core relational tables exist in PostgreSQL information_schema."""
    with pg_engine.connect() as conn:
        res = conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )).fetchall()
        tables = {r[0] for r in res}
        
    expected_tables = {
        "organizations",
        "users",
        "questions",
        "question_versions",
        "assessments",
        "assessment_rules",
        "sections",
        "section_questions",
        "candidate_invitations",
        "exam_invitations",
        "invitation_delivery_attempts",
        "attempts",
        "attempt_answers",
        "proctoring_incidents",
        "proctor_review_decisions",
        "proctoring_evidence_access_audits",
        "security_audit_events",
        "alembic_version"
    }
    for et in expected_tables:
        assert et in tables, f"Expected table {et} missing from PostgreSQL"


def test_postgresql_transaction_and_foreign_keys():
    """Test relational integrity, transaction commit, and rollback behavior."""
    db = PgSessionLocal()
    try:
        # Check or create an existing organization
        org = db.query(Organization).first()
        if not org:
            org = Organization(name="Integration Org", slug="integration-org")
            db.add(org)
            db.commit()
            db.refresh(org)
        assert org is not None, "Organization must exist in PostgreSQL"
        
        # Test transaction rollback on foreign key violation
        try:
            fake_user = User(
                email="fail_test@proctorai.local",
                hashed_password="hash",
                full_name="Fail Test",
                role=Role.CANDIDATE,
                org_id="non-existent-org-uuid"  # Violates foreign key
            )
            db.add(fake_user)
            db.flush()
            pytest.fail("Should have raised ForeignKeyViolation")
        except Exception:
            db.rollback()
            
        # Verify database remained intact
        after_rollback = db.query(User).filter(User.email == "fail_test@proctorai.local").first()
        assert after_rollback is None
    finally:
        db.close()


def test_postgresql_unique_constraint_enforcement():
    """Test unique constraints prevent duplicate records."""
    db = PgSessionLocal()
    try:
        org = db.query(Organization).first()
        if not org:
            org = Organization(name="Unique Test Org", slug="unique-test-org")
            db.add(org)
            db.commit()
            db.refresh(org)

        existing_user = db.query(User).first()
        if not existing_user:
            existing_user = User(
                email="unique_test_user@proctorai.local",
                hashed_password="hash",
                full_name="Unique User",
                role=Role.CANDIDATE,
                org_id=org.id
            )
            db.add(existing_user)
            db.commit()
            db.refresh(existing_user)

        assert existing_user is not None
        
        duplicate_user = User(
            email=existing_user.email,  # Duplicate unique email
            hashed_password="newhash",
            full_name="Duplicate Name",
            role=Role.CANDIDATE,
            org_id=existing_user.org_id
        )
        db.add(duplicate_user)
        with pytest.raises(Exception):
            db.flush()
        db.rollback()
    finally:
        db.close()

