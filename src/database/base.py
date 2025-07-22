from typing import Generator, Tuple

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, Session, sessionmaker
from src.utils.logging import get_logger

# Initialize structlog
logger = get_logger(__name__)

# Create Base class for all models
Base = declarative_base()

# Initialize these variables as None; they will be set by init_db
engine = None
db_session = None
SessionLocal = None

def init_db(database_url: str) -> Tuple[object, object]:
    """Initialize the database with the provided connection URL.

    Args:
        database_url: Connection string for the database

    Returns:
        Tuple containing (engine, db_session)
    """
    global engine, db_session, SessionLocal

    try:
        # Create SQLAlchemy engine using the provided URL
        engine = create_engine(database_url)

        # Create a scoped session factory
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db_session = scoped_session(SessionLocal)

        # Create all tables
        Base.metadata.create_all(bind=engine)

        logger.debug("database_initialized")

        return engine, db_session
    except Exception as e:
        logger.error("database_initialization_failed", error=str(e), exc_info=True)
        raise

def get_db_session():
    """Get the current database session.

    Returns:
        The current database session or raises an exception if not initialized
    """
    if db_session is None:
        logger.error("database_session_error", error="Database not initialized")
        raise RuntimeError("Database not initialized. Call init_db first.")
    return db_session

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for getting a database session.

    This function is designed to be used with FastAPI's dependency injection.
    It yields a session that will be closed automatically after the request is complete.

    Yields:
        A SQLAlchemy session
    """
    if SessionLocal is None:
        logger.error("database_session_error", error="Database not initialized")
        raise RuntimeError("Database not initialized. Call init_db first.")

    db = SessionLocal()
    try:
        logger.debug("database_session_created_for_request")
        yield db
    finally:
        logger.debug("database_session_closed_after_request")
        db.close()

def close_session() -> None:
    """Close the current session and remove it from the registry.
    Call this when you're done with a series of database operations.
    """
    if db_session is not None:
        db_session.remove()
        logger.debug("database_session_closed")