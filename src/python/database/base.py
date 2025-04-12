import logging

# Import config using absolute import
from ..config import settings
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

# Configure logging
logger = logging.getLogger(__name__)

# Create SQLAlchemy engine using the config settings
engine = create_engine(settings.database.url)

# Create a scoped session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)

# Create Base class for all models
Base = declarative_base()

def init_db() -> None:
    """Initialize the database by creating tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

def close_session() -> None:
    """Close the current session and remove it from the registry.
    Call this when you're done with a series of database operations.
    """
    db_session.remove()
    logger.debug("Database session closed and removed")