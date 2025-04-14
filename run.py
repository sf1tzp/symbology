#!/usr/bin/env python
"""
Wrapper script to run the application with the correct Python path.
"""
import os
import sys

# Add the src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# Now import and run the main module
from src.python.main import main

if __name__ == "__main__":
    main()