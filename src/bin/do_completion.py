#!/usr/bin/env python
"""
Direct LLM completion script for testing and debugging.

This script allows you to send prompts directly to the LLM through the OpenAI client,
bypassing the API and database layers. Useful for debugging Ollama or other LLM endpoints.

Usage:
    python -m src.bin.do_completion --prompt "Tell me about financial statements" --temperature 0.7
    python -m src.bin.do_completion --file prompt.txt --model llama3:latest --verbose
"""

import argparse
import sys
from typing import List

from src.llm.client import OpenAIClient
from src.llm.prompts import get_prompt_template, PromptType
from src.utils.config import settings
from src.utils.logging import configure_logging, get_logger

# Configure logging
logger = get_logger(__name__)

def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Send direct completion requests to the LLM")

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--prompt", "-p", type=str, help="Text prompt to send to the LLM")
    input_group.add_argument("--file", "-f", type=str, help="Text file containing prompt to send")
    input_group.add_argument("--template", "-t", type=str, choices=[pt.value for pt in PromptType],
                            help="Use a predefined prompt template")

    # LLM parameters
    parser.add_argument("--model", "-m", type=str, help="Model to use for completion (overrides config)")
    parser.add_argument("--system-prompt", "-s", type=str,
                       help="System prompt (instructions) for the LLM")
    parser.add_argument("--temperature", type=float, default=0.7,
                       help="Temperature setting (0.0-1.0)")
    parser.add_argument("--max-tokens", type=int, default=4000,
                       help="Maximum tokens to generate")

    # Context options
    parser.add_argument("--context-file", "-c", action="append",
                       help="File(s) containing context to include (can be used multiple times)")

    # Output options
    parser.add_argument("--output", "-o", type=str,
                       help="Output file to write results to (default: stdout)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging (DEBUG level)")
    parser.add_argument("--json-log", "-j", action="store_true",
                       help="Output logs in JSON format")

    return parser.parse_args()

def read_file_content(file_path: str) -> str:
    """Read content from a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        sys.exit(1)

def read_context_files(file_paths: List[str]) -> List[str]:
    """Read content from context files."""
    if not file_paths:
        return []

    return [read_file_content(path) for path in file_paths]

def main() -> None:
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()

    # Configure logging based on arguments
    log_level = "DEBUG" if args.verbose else settings.logging.level
    configure_logging(log_level=log_level, json_format=args.json_log)
    logger.info("Starting direct completion script")

    # Initialize OpenAI client
    client = OpenAIClient()
    logger.info(f"Initialized client, using endpoint: {client.base_url}")

    # Get system prompt
    system_prompt = args.system_prompt
    user_prompt = ""

    # Handle different input types
    if args.prompt:
        user_prompt = args.prompt
    elif args.file:
        user_prompt = read_file_content(args.file)
    elif args.template:
        # Use a predefined prompt template
        prompt_type = PromptType(args.template)
        template = get_prompt_template(prompt_type)
        system_prompt = system_prompt or template.system_prompt

        # Ask for required template parameters
        print(f"Using template: {template.name}")
        template_params = {}
        # Extract parameter names from the template
        import re
        param_names = re.findall(r'\{([^{}]+)\}', template.user_prompt_template)
        for param in param_names:
            if param != 'additional_instructions':  # Make this one optional
                value = input(f"Enter value for {param}: ")
                template_params[param] = value

        # Default for additional instructions
        template_params['additional_instructions'] = template_params.get('additional_instructions', '')

        # Format the template
        user_prompt = template.format_user_prompt(**template_params)

    # Default system prompt if none provided
    if not system_prompt:
        system_prompt = "You are a helpful assistant specializing in financial analysis."

    # Read context files if provided
    context_texts = read_context_files(args.context_file) if args.context_file else None

    # Prepare completion parameters
    model_name = args.model if args.model else settings.openai_api.default_model

    logger.info(f"Sending completion request to model: {model_name}")
    logger.debug(f"System prompt: {system_prompt[:100]}...")
    logger.debug(f"User prompt: {user_prompt[:100]}...")
    logger.debug(f"Temperature: {args.temperature}")
    logger.debug(f"Max tokens: {args.max_tokens}")

    # Generate completion
    try:
        completion = client.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context_texts=context_texts,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            model=model_name
        )

        # Output results
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(completion)
            logger.info(f"Output written to {args.output}")
        else:
            print("\n--- COMPLETION RESULT ---\n")
            print(completion)
            print("\n-----------------------\n")

        logger.info("Completion successful")

    except Exception as e:
        logger.error(f"Error generating completion: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()