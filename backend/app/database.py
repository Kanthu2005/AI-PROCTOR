import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

logger = logging.getLogger("proctorai.database")

def resolve_database_url(url: str) -> str:
    """
    Ensure PostgreSQL URLs use an installed DBAPI driver (psycopg or psycopg2).
    If url starts with 'postgresql://', detects which driver is available.
    """
    if url.startswith("postgresql://"):
        try:
            import psycopg  # noqa: F401
            return url
        except ImportError:
            try:
                import psycopg2  # noqa: F401
                return url.replace("postgresql://", "postgresql+psycopg2://", 1)
            except ImportError:
                return url
    return url


# SQLAlchemy setup
connect_args = {}
engine_kwargs = {
    "echo": False,
}

if settings.is_sqlite:
    connect_args["check_same_thread"] = False
    engine_kwargs["connect_args"] = connect_args
else:
    # Dedicated PostgreSQL Production-Grade Connection Pooling
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
    engine_kwargs["pool_timeout"] = settings.DB_POOL_TIMEOUT
    engine_kwargs["pool_recycle"] = settings.DB_POOL_RECYCLE

engine = create_engine(
    resolve_database_url(settings.DATABASE_URL),
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency for database session lifecycle management."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_db_connection() -> dict:
    """
    Lightweight health-check probe validating active database connectivity.
    Executes a SELECT 1 test query without leaking credentials.
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar()
            is_alive = result == 1
        return {
            "status": "connected" if is_alive else "degraded",
            "connected": is_alive,
            "dialect": engine.dialect.name
        }
    except Exception as e:
        logger.error(f"Database health probe failed: {e}")
        return {
            "status": "disconnected",
            "connected": False,
            "dialect": engine.dialect.name,
            "error": "Database connectivity failed"
        }


# MongoDB / Telemetry Store setup
# Fallback to mongomock when no live MongoDB daemon is running
_mongo_client = None
_mongo_db = None


def get_mongo_db():
    global _mongo_client, _mongo_db
    if _mongo_db is not None:
        return _mongo_db

    try:
        import pymongo
        client = pymongo.MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=1000)
        client.server_info()
        _mongo_client = client
        _mongo_db = client[settings.MONGODB_DB_NAME]
        logger.info("Connected to MongoDB for high-volume telemetry & proctoring logs.")
    except Exception as e:
        logger.warning(f"MongoDB not reachable ({e}). Falling back to in-memory mongomock for telemetry.")
        import mongomock
        _mongo_client = mongomock.MongoClient()
        _mongo_db = _mongo_client[settings.MONGODB_DB_NAME]

    return _mongo_db
