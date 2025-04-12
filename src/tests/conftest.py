import logging
import os
import sys
import pytest
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the project root directory to the Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the models and settings
from src.python.database.models import Base
from src.python.config import settings

# Use PostgreSQL for testing with a separate test database
TEST_DATABASE_NAME = "symbology-test"
TEST_DATABASE_URL = f"postgresql://{settings.database.postgres_user}:{settings.database.postgres_password}@{settings.database.host}:{settings.database.port}/{TEST_DATABASE_NAME}"

@pytest.fixture(scope="session", autouse=True)
def create_test_database():
    """Create and drop the test database before and after all tests."""
    # Connect to default PostgreSQL database to create/drop test database
    default_db_url = f"postgresql://{settings.database.postgres_user}:{settings.database.postgres_password}@{settings.database.host}:{settings.database.port}/postgres"
    default_engine = create_engine(default_db_url)

    # Create test database if it doesn't exist
    with default_engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        try:
            logger.info(f"Creating test database: {TEST_DATABASE_NAME}")
            conn.execute(text(f"DROP DATABASE IF EXISTS \"{TEST_DATABASE_NAME}\""))
            conn.execute(text(f"CREATE DATABASE \"{TEST_DATABASE_NAME}\""))
            logger.info("Test database created successfully")
        except Exception as e:
            logger.error(f"Error creating test database: {e}")
            raise

    # Create an engine connected to the test database and create the tables
    test_engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=test_engine)
    test_engine.dispose()

    # Log the list of created tables
    test_engine = create_engine(TEST_DATABASE_URL)
    from sqlalchemy import inspect
    inspector = inspect(test_engine)
    tables = inspector.get_table_names()
    logger.info(f"Tables in the test database: {tables}")
    test_engine.dispose()

    yield

    # Drop test database after all tests
    with default_engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        try:
            # Terminate any open connections to the test database
            conn.execute(text(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{TEST_DATABASE_NAME}'
                AND pid <> pg_backend_pid()
            """))

            # Drop the test database
            logger.info(f"Dropping test database: {TEST_DATABASE_NAME}")
            conn.execute(text(f"DROP DATABASE IF EXISTS \"{TEST_DATABASE_NAME}\""))
        except Exception as e:
            logger.error(f"Error dropping test database: {e}")

@pytest.fixture(scope="function")
def db_engine():
    """Create a database engine for testing."""
    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()

@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a fresh database session for each test."""
    connection = db_engine.connect()
    transaction = connection.begin()

    # Create a session factory
    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    try:
        yield session
    finally:
        # Cleanup
        session.close()
        # Only rollback if the transaction is still active
        if transaction.is_active:
            transaction.rollback()
        connection.close()

@pytest.fixture(scope="function")
def sample_company_data():
    """Sample company data for testing."""
    return {
        "cik": 1234567,
        "name": "Test Company Inc.",
        "tickers": ["TEST", "TSTC"],
        "exchanges": ["NYSE"],
        "sic": "7370",
        "sic_description": "Services-Computer Programming, Data Processing, Etc.",
        "category": "Technology",
        "fiscal_year_end": "1231",
        "entity_type": "Corporation",
        "phone": "123-456-7890",
        "business_address": "123 Test Street, Test City, TS 12345",
        "mailing_address": "P.O. Box 123, Test City, TS 12345"
    }

@pytest.fixture(scope="function")
def sample_filing_data():
    """Sample filing data for testing."""
    return {
        "company_id": 1,  # This will be overridden in tests
        "filing_type": "10-K",
        "accession_number": "0001234567-23-000123",
        "filing_date": datetime.strptime("2023-03-15", "%Y-%m-%d"),
        "report_date": datetime.strptime("2022-12-31", "%Y-%m-%d"),
        "form_name": "Annual Report",
        "file_number": "001-12345",
        "film_number": "23456789",
        "description": "Annual report for fiscal year ending December 31, 2022",
        "url": "https://www.sec.gov/Archives/edgar/data/1234567/000123456723000123/test-10k.htm",
        "data": {"key": "value"}
    }