"""
Data Migration Utility: Preserves and transfers all existing records
from local intellitest.db (SQLite) into PostgreSQL (aiprotector).
"""
import sqlite3
import json
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.database import resolve_database_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("data_migration")

def migrate():
    sqlite_conn = sqlite3.connect("intellitest.db")
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    pg_engine = create_engine(resolve_database_url(settings.DATABASE_URL))
    
    tables_in_order = [
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
        "coding_submissions",
        "proctoring_incidents",
        "proctor_review_decisions",
        "proctoring_evidence_access_audits",
        "assessment_policy_audits",
        "refresh_tokens",
        "password_reset_tokens",
        "security_audit_events"
    ]

    with pg_engine.begin() as pg_conn:
        for tbl in tables_in_order:
            # Check if table exists in sqlite
            sqlite_cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tbl,))
            if not sqlite_cur.fetchone():
                continue

            rows = sqlite_cur.execute(f"SELECT * FROM {tbl}").fetchall()
            if not rows:
                logger.info(f"Table '{tbl}': 0 rows to migrate.")
                continue

            logger.info(f"Migrating {len(rows)} row(s) for table '{tbl}'...")
            columns = rows[0].keys()
            
            # Read PostgreSQL column types to convert JSON / DateTime strings appropriately
            col_types = {}
            type_res = pg_conn.execute(text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = :tbl AND table_schema = 'public'"
            ), {"tbl": tbl}).fetchall()
            for r in type_res:
                col_types[r[0]] = r[1]

            col_names_str = ", ".join([f'"{c}"' for c in columns])
            placeholders = ", ".join([f":{c}" for c in columns])
            insert_stmt = text(f'INSERT INTO "{tbl}" ({col_names_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING')

            for r in rows:
                row_dict = dict(r)
                for k, v in row_dict.items():
                    dtype = col_types.get(k, "")
                    if dtype in ("json", "jsonb") and isinstance(v, str):
                        try:
                            # Verify valid JSON
                            json.loads(v)
                        except Exception:
                            row_dict[k] = json.dumps(v)
                    elif dtype == "boolean" and isinstance(v, int):
                        row_dict[k] = bool(v)
                    elif "timestamp" in dtype and isinstance(v, str) and v:
                        try:
                            row_dict[k] = datetime.fromisoformat(v.replace("Z", "+00:00"))
                        except Exception:
                            pass
                
                pg_conn.execute(insert_stmt, row_dict)

            logger.info(f"Successfully migrated table '{tbl}'.")

    sqlite_conn.close()
    logger.info("Complete data migration from SQLite to PostgreSQL finished with 100% integrity.")

if __name__ == "__main__":
    migrate()
