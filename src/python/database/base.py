import logging
from typing import Optional, Tuple

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

# Configure logging
logger = logging.getLogger(__name__)

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
        logger.info("Database tables created successfully")

        return engine, db_session
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

def get_db_session():
    """Get the current database session.

    Returns:
        The current database session or raises an exception if not initialized
    """
    if db_session is None:
        raise RuntimeError("Database not initialized. Call init_db first.")
    return db_session

def close_session() -> None:
    """Close the current session and remove it from the registry.
    Call this when you're done with a series of database operations.
    """
    if db_session is not None:
        db_session.remove()
        logger.debug("Database session closed and removed")