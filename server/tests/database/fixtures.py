import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Import the models and settings
from symbology.database import base
from symbology.database.base import Base
from symbology.utils.logging import configure_logging, get_logger

from symbology.utils.config import settings

# Configure logging for tests
configure_logging(log_level="INFO")
logger = get_logger(__name__)

# # Add the project root directory to the Python path for imports
# project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)


# Use PostgreSQL for testing with a separate test database
TEST_DATABASE_NAME = "symbology-test"
TEST_DATABASE_URL = f"postgresql://{settings.database.user}:{settings.database.password}@{settings.database.host}:{settings.database.port}/{TEST_DATABASE_NAME}"

@pytest.fixture(scope="session", autouse=True)
def create_test_database():
    """Create and drop the test database before and after all tests."""
    # Connect to default PostgreSQL database to create/drop test database
    default_db_url = f"postgresql://{settings.database.user}:{settings.database.password}@{settings.database.host}:{settings.database.port}/postgres"
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

    # Create an engine connected to the test database and create the tables.
    # Enable pgvector first — the schema has vector embedding columns, and a
    # database freshly cloned from template1 doesn't carry the extension.
    test_engine = create_engine(TEST_DATABASE_URL)
    with test_engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
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
    """A transactional, isolated session for each test.

    Opens an outer transaction on a dedicated connection and binds the session
    with ``join_transaction_mode="create_savepoint"`` so that ``commit()`` calls
    inside the code under test become SAVEPOINT releases — the outer transaction
    is rolled back on teardown, fully isolating each test (committing accessors
    no longer leak rows into the shared test database).

    Also points the application's ``base.db_session`` at this session for the
    duration of the test, so ``get_db_session()`` returns it everywhere —
    accessor functions *and* handlers — without per-test monkeypatching.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    saved_session = base.db_session
    base.db_session = session

    try:
        yield session
    finally:
        base.db_session = saved_session
        session.close()
        # Roll back the outer transaction, discarding everything the test wrote.
        if transaction.is_active:
            transaction.rollback()
        connection.close()
