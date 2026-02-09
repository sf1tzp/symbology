import os
import sys

from symbology.utils.logging import get_logger

# Add the project root directory to the Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = get_logger(__name__)
