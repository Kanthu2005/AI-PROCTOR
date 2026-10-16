import sqlite3
import os
import sys

# Ensure backend root is on sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.database import engine, Base, SessionLocal
from app.seed_proctorai import seed_database
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reset_reseed")

def reset_and_reseed():
    db = SessionLocal()
    try:
        logger.info("Step 1: Dropping and clearing previous data from database tables...")
        # Using SQLAlchemy metadata to safely drop and recreate all tables
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        logger.info("All previous tables cleared and recreated successfully.")
        
        logger.info("Step 2: Reseeding clean fresh baseline data (users, assessments, questions, candidate invitations)...")
        seed_database()
        logger.info("Database reseeded successfully!")
        
        # Verify counts
        from app.models.user import User, Organization
        from app.models.assessment import Assessment
        from app.models.question import Question
        from app.models.candidate import CandidateInvitation
        from app.models.attempt import Attempt
        from app.models.proctoring import ProctoringIncident
        
        counts = {
            "organizations": db.query(Organization).count(),
            "users": db.query(User).count(),
            "questions": db.query(Question).count(),
            "assessments": db.query(Assessment).count(),
            "candidate_invitations": db.query(CandidateInvitation).count(),
            "attempts": db.query(Attempt).count(),
            "proctoring_incidents": db.query(ProctoringIncident).count(),
        }
        logger.info("Current Table Counts after Reset & Reseed:")
        for tbl, cnt in counts.items():
            logger.info(f" - {tbl}: {cnt}")
            
        print("SUCCESS: Database reset and clean reseed completed.")
    except Exception as e:
        logger.error(f"Error during reset and reseed: {e}")
        db.rollback()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    reset_and_reseed()
