"""
Development-only seed command for clearly documented demo accounts.
Usage:
    python -m app.seed_demo_accounts
"""
import sys
import logging
from app.database import engine, Base, SessionLocal
from app.models.user import Organization, User, Role
from app.utils.security import hash_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("proctorai.seed")

DEMO_ACCOUNTS = [
    {
        "role": Role.PLATFORM_ADMIN,
        "email": "admin@intellitest.ai",
        "password": "Admin@12345",
        "full_name": "Alexander Vance (Platform Superadmin)",
        "org_slug": None
    },
    {
        "role": Role.ORG_ADMIN,
        "email": "orgadmin@acme.com",
        "password": "Acme@12345",
        "full_name": "Sophia Chen (Acme Org Admin)",
        "org_slug": "acme"
    },
    {
        "role": Role.RECRUITER,
        "email": "recruiter@acme.com",
        "password": "Recruit@12345",
        "full_name": "Kanthu Naik (Acme Recruiter)",
        "org_slug": "acme"
    },
    {
        "role": Role.QUESTION_AUTHOR,
        "email": "author@acme.com",
        "password": "Author@12345",
        "full_name": "Carol Question Author (Acme Author)",
        "org_slug": "acme"
    },
    {
        "role": Role.PROCTOR,
        "email": "proctor@acme.com",
        "password": "Proctor@12345",
        "full_name": "David AI Proctor (Acme Proctor)",
        "org_slug": "acme"
    },
    {
        "role": Role.CANDIDATE,
        "email": "candidate@example.com",
        "password": "Candidate@12345",
        "full_name": "Rahul Sharma (Candidate)",
        "org_slug": "acme"
    },
    # Secondary organization for testing cross-tenant isolation
    {
        "role": Role.RECRUITER,
        "email": "recruiter@beta.com",
        "password": "BetaRecruit@12345",
        "full_name": "Bob Beta Recruiter (Beta Corp)",
        "org_slug": "beta"
    }
]


def seed_demo_accounts():
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Seed Organizations
        org_map = {}
        for org_data in [
            {"name": "Acme Corp", "slug": "acme", "domain": "acme.com"},
            {"name": "Beta Technologies", "slug": "beta", "domain": "beta.com"}
        ]:
            org = db.query(Organization).filter(Organization.slug == org_data["slug"]).first()
            if not org:
                org = Organization(
                    name=org_data["name"],
                    slug=org_data["slug"],
                    domain=org_data["domain"],
                    is_active=True
                )
                db.add(org)
                db.flush()
                logger.info(f"Created organization: {org.name} ({org.slug})")
            org_map[org_data["slug"]] = org

        # 2. Seed Demo Accounts
        print("\n" + "=" * 70)
        print("  PROCTORAI DEVELOPMENT DEMO ACCOUNTS (Argon2id Hashed)")
        print("=" * 70)
        print(f"{'Role':<18} | {'Email':<25} | {'Password':<16} | Org")
        print("-" * 70)

        for account in DEMO_ACCOUNTS:
            user = db.query(User).filter(User.email == account["email"].lower()).first()
            org_id = org_map[account["org_slug"]].id if account["org_slug"] else None
            hashed_pwd = hash_password(account["password"])

            if not user:
                user = User(
                    email=account["email"].lower(),
                    hashed_password=hashed_pwd,
                    full_name=account["full_name"],
                    role=account["role"],
                    org_id=org_id,
                    is_active=True
                )
                db.add(user)
                action = "CREATED"
            else:
                user.hashed_password = hashed_pwd
                user.role = account["role"]
                user.org_id = org_id
                user.is_active = True
                action = "UPDATED"

            org_display = account["org_slug"] or "GLOBAL"
            print(f"{account['role'].value:<18} | {account['email']:<25} | {account['password']:<16} | {org_display} ({action})")

        db.commit()
        print("=" * 70)
        print("Successfully seeded all demo accounts with Argon2id passwords.\n")

    except Exception as e:
        logger.error(f"Error seeding demo accounts: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_accounts()
