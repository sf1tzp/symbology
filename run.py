#!/usr/bin/env python
"""
Wrapper script to run the application with the correct Python path.
"""
import os
import sys
import argparse

# Add the src directory to the Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)


def run_ingestion():
    """Run the data ingestion application."""
    from src.ingestion.main import main
    main()


def run_api():
    """Run the REST API server."""
    from src.api.main import start_api
    start_api()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Symbology Application')
    parser.add_argument('--api', action='store_true', help='Run the REST API server')
    parser.add_argument('--ingestion', action='store_true', help='Run the data ingestion application')

    args = parser.parse_args()

    if args.api:
        run_api()
    elif args.ingestion:
        run_ingestion()
    else:
        # Default to ingestion for backward compatibility
        print("No specific mode selected, defaulting to ingestion application")
        print("Use --api to run the API server or --ingestion for the data ingestion application")
        run_ingestion()