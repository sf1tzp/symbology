import os
import sys

from src.tests.database.fixtures import create_test_database, db_engine, db_session, TEST_DATABASE_NAME, TEST_DATABASE_URL
from src.utils.logging import get_logger

# Add the project root directory to the Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set PYTHONPATH for consistent imports between tests and coverage
# os.environ["PYTHONPATH"] = project_root

# Use the project's standard structured logging

logger = get_logger(__name__)

# Import and reexport database fixtures

