import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["USE_DOCKER_SANDBOX"] = "False"  # Use isolated subprocess for fast unit test suite

from app.database import Base, get_db
from app.main import app
from app.models.user import Organization, User, Role
from app.utils.security import hash_password, create_access_token

# In-memory SQLite test database with StaticPool so all threads share the memory connection
engine_test = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def db():
    connection = engine_test.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_org(db):
    org = Organization(
        name="Test Corp",
        slug="testcorp",
        domain="testcorp.com",
        is_active=True
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@pytest.fixture
def platform_admin(db, test_org):
    user = User(
        email="p_admin@test.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Platform Admin",
        role=Role.PLATFORM_ADMIN,
        org_id=test_org.id,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def org_admin(db, test_org):
    user = User(
        email="org_admin@test.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Org Admin",
        role=Role.ORG_ADMIN,
        org_id=test_org.id,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def recruiter(db, test_org):
    user = User(
        email="recruiter@test.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Recruiter User",
        role=Role.RECRUITER,
        org_id=test_org.id,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def question_author(db, test_org):
    user = User(
        email="author@test.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Author User",
        role=Role.QUESTION_AUTHOR,
        org_id=test_org.id,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def proctor(db, test_org):
    user = User(
        email="proctor@test.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Proctor User",
        role=Role.PROCTOR,
        org_id=test_org.id,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def candidate_user(db, test_org):
    user = User(
        email="candidate_user@test.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Candidate User",
        role=Role.CANDIDATE,
        org_id=test_org.id,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_headers(user: User):
    token = create_access_token({
        "sub": user.id,
        "role": user.role.value,
        "org_id": user.org_id
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def platform_admin_headers(platform_admin):
    return make_headers(platform_admin)


@pytest.fixture
def org_admin_headers(org_admin):
    return make_headers(org_admin)


@pytest.fixture
def recruiter_headers(recruiter):
    return make_headers(recruiter)


@pytest.fixture
def author_headers(question_author):
    return make_headers(question_author)


@pytest.fixture
def proctor_headers(proctor):
    return make_headers(proctor)


@pytest.fixture
def candidate_headers(candidate_user):
    return make_headers(candidate_user)
