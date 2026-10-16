import os
import sys
import logging

# Ensure backend root is on sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.database import engine, Base, SessionLocal
from app.models.user import User, Organization
from app.models.question import Question
from app.models.assessment import Assessment
from app.models.candidate import CandidateInvitation
from app.models.attempt import Attempt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("wipe_clean")

def wipe_and_init_clean():
    logger.info("Dropping all existing database tables and wiping all old data...")
    Base.metadata.drop_all(bind=engine)
    logger.info("Creating all tables cleanly with latest up-to-date schema...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        org_count = db.query(Organization).count()
        q_count = db.query(Question).count()
        a_count = db.query(Assessment).count()
        inv_count = db.query(CandidateInvitation).count()
        att_count = db.query(Attempt).count()
        
        logger.info(f"Database wiped clean successfully! Current counts:")
        logger.info(f"  Users: {user_count}")
        logger.info(f"  Organizations: {org_count}")
        logger.info(f"  Questions: {q_count}")
        logger.info(f"  Assessments: {a_count}")
        logger.info(f"  Candidate Invitations: {inv_count}")
        logger.info(f"  Attempts: {att_count}")
    finally:
        db.close()

if __name__ == "__main__":
    wipe_and_init_clean()
