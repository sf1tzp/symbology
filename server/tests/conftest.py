import os
import sys

import pytest

from symbology.llm.client import reset_shutdown_flag
from symbology.utils.logging import get_logger

# Add the project root directory to the Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = get_logger(__name__)


@pytest.fixture(autouse=True)
def _reset_worker_shutdown_flag():
    """Keep the worker's module-global shutdown flag from leaking across tests.

    ``tests/worker/test_worker.py`` exercises the shutdown path, which sets a
    module-level flag in ``symbology.llm.client``; without a reset it poisons
    ``retry_backoff`` in later-ordered tests (e.g. the LLM client tests).
    """
    reset_shutdown_flag()
    yield
    reset_shutdown_flag()
