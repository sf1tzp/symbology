#!/usr/bin/env python3
"""
Initialize default prompts in the database using the API.

This script creates the default prompts defined in src/llm/prompts.py
through the Prompt API.
"""

import argparse
import os
import sys
from typing import Dict, List

import requests

# Add the project root to Python path so we can import modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.llm.prompts import SYSTEM_PROMPTS, USER_PROMPT_TEMPLATES
from src.utils.config import settings
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

# Get API URL from config
DEFAULT_API_HOST = settings.symbology_api.host
DEFAULT_API_PORT = settings.symbology_api.port
DEFAULT_API_URL = f"http://{DEFAULT_API_HOST}:{DEFAULT_API_PORT}"
DEFAULT_API_PREFIX = "/api"  # API prefix used in main.py


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Initialize default prompts in the database")
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"API URL (default: {DEFAULT_API_URL})"
    )
    parser.add_argument(
        "--api-prefix",
        default=DEFAULT_API_PREFIX,
        help=f"API prefix path (default: {DEFAULT_API_PREFIX})"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force creation of prompts even if they may already exist"
    )
    return parser.parse_args()


def extract_template_vars(template: str) -> List[str]:
    """
    Extract template variables from a prompt template string.

    Args:
        template: The prompt template string

    Returns:
        List of template variable names
    """
    import re
    try:
        # Find all patterns like {variable_name}
        matches = re.findall(r'\{([^}]+)\}', template)
        # Return unique variable names
        return list(set(matches))
    except Exception as e:
        logger.error("extract_template_vars_failed", error=str(e), exc_info=True)
        raise ValueError(f"Failed to extract template variables: {str(e)}") from e


def create_default_prompts(api_url: str, api_prefix: str, force: bool = False) -> Dict[str, str]:
    """
    Create default prompts using the API.

    Args:
        api_url: Base URL of the API
        api_prefix: API prefix path (e.g., /api)
        force: Whether to force creation even if prompts may already exist

    Returns:
        Dictionary mapping prompt types to their IDs
    """
    prompts_url = f"{api_url}{api_prefix}/prompts/"
    prompt_ids = {}

    # Create system prompts
    for prompt_type, system_prompt in SYSTEM_PROMPTS.items():
        prompt_name = f"System: {prompt_type.value.replace('_', ' ').title()}"
        template_vars = []

        try:
            logger.info("creating_system_prompt", prompt_type=prompt_type.value)

            response = requests.post(
                prompts_url,
                json={
                    "name": prompt_name,
                    "description": f"System prompt for {prompt_type.value} analysis",
                    "role": "system",
                    "template": system_prompt.strip(),
                    "template_vars": template_vars,
                    "default_vars": {}
                }
            )

            response.raise_for_status()  # Raise exception for 4xx and 5xx responses

            if response.status_code == 201:
                prompt_data = response.json()
                prompt_ids[f"system_{prompt_type.value}"] = prompt_data["id"]
                logger.info("created_system_prompt",
                           prompt_type=prompt_type.value,
                           prompt_id=prompt_data["id"])

        except requests.HTTPError as e:
            if e.response.status_code == 409 and not force:
                logger.warning("prompt_already_exists",
                              prompt_name=prompt_name,
                              status_code=e.response.status_code)
            else:
                logger.error("failed_to_create_prompt",
                            prompt_name=prompt_name,
                            status_code=e.response.status_code if hasattr(e, 'response') else None,
                            response=e.response.text if hasattr(e, 'response') else str(e))

        except Exception as e:
            logger.error("prompt_creation_error", prompt_name=prompt_name, error=str(e), exc_info=True)

    # Create user prompts
    for prompt_type, user_template in USER_PROMPT_TEMPLATES.items():
        prompt_name = f"User: {prompt_type.value.replace('_', ' ').title()}"

        try:
            template_vars = extract_template_vars(user_template)

            # Create default variables with empty strings
            default_vars = {var: "" for var in template_vars}

            logger.info("creating_user_prompt", prompt_type=prompt_type.value)

            response = requests.post(
                prompts_url,
                json={
                    "name": prompt_name,
                    "description": f"User prompt template for {prompt_type.value} analysis",
                    "role": "user",
                    "template": user_template.strip(),
                    "template_vars": template_vars,
                    "default_vars": default_vars
                }
            )

            response.raise_for_status()  # Raise exception for 4xx and 5xx responses

            if response.status_code == 201:
                prompt_data = response.json()
                prompt_ids[f"user_{prompt_type.value}"] = prompt_data["id"]
                logger.info("created_user_prompt",
                           prompt_type=prompt_type.value,
                           prompt_id=prompt_data["id"])

        except requests.HTTPError as e:
            if e.response.status_code == 409 and not force:
                logger.warning("prompt_already_exists",
                              prompt_name=prompt_name,
                              status_code=e.response.status_code)
            else:
                logger.error("failed_to_create_prompt",
                            prompt_name=prompt_name,
                            status_code=e.response.status_code if hasattr(e, 'response') else None,
                            response=e.response.text if hasattr(e, 'response') else str(e))

        except Exception as e:
            logger.error("prompt_creation_error", prompt_name=prompt_name, error=str(e), exc_info=True)

    return prompt_ids


def main():
    """Main entry point for the script."""
    args = parse_arguments()

    logger.info("initializing_prompts", api_url=args.api_url, api_prefix=args.api_prefix, force=args.force)

    try:
        # Create default prompts
        prompt_ids = create_default_prompts(args.api_url, args.api_prefix, args.force)

        if prompt_ids:
            logger.info("prompts_initialized", count=len(prompt_ids))
            print(f"Successfully initialized {len(prompt_ids)} prompts")
        else:
            logger.warning("no_prompts_created")
            print("No prompts were created")

    except Exception as e:
        logger.error("initialization_failed", error=str(e), exc_info=True)
        print(f"Error initializing prompts: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()