"""Pipeline orchestration helpers.

Shared utilities for the FULL_PIPELINE job handler that replace shell-script
CLI calls (model-configs create, prompts create) with direct Python equivalents.
"""
import json
from pathlib import Path
from typing import Optional

from symbology.database.model_configs import ModelConfig, get_or_create_model_config
from symbology.database.prompts import Prompt, create_prompt
from symbology.utils.logging import get_logger

logger = get_logger(__name__)

# Default model tiers used by the ingestion pipeline
PIPELINE_MODEL_CONFIGS = {
    "single_summary": {"model": "claude-haiku-4-5-20251001", "max_tokens": 4096},
    "aggregate_summary": {"model": "claude-sonnet-4-5-20250929", "max_tokens": 4096},
    "frontpage_summary": {"model": "claude-sonnet-4-5-20250929", "max_tokens": 4096},
}

# Prompt names used at each pipeline stage
PIPELINE_PROMPTS = {
    "aggregate_summary": "aggregate-summary",
    "frontpage_summary": "general-summary",
}

# Document types per form (mirrors ingest.just)
FORM_DOCUMENT_TYPES = {
    "10-K": ["business_description", "risk_factors", "management_discussion", "controls_procedures"],
    "10-Q": ["risk_factors", "management_discussion", "controls_procedures", "market_risk"],
}


def ensure_model_config(
    model_name: str,
    max_tokens: Optional[int] = None,
    **option_overrides,
) -> ModelConfig:
    """Get or create a ModelConfig with the given settings.

    Starts from defaults, applies overrides, then delegates to
    ``get_or_create_model_config`` for content-hash deduplication.

    Args:
        model_name: Model identifier (e.g. "claude-haiku-4-5-20251001").
        max_tokens: Max tokens override.
        **option_overrides: Any additional option overrides
            (temperature, top_k, top_p, etc.).

    Returns:
        The existing or newly created ModelConfig.
    """
    default = ModelConfig.create_default(model_name)
    options = json.loads(default.options_json)

    if max_tokens is not None:
        options["max_tokens"] = max_tokens
    for key, value in option_overrides.items():
        if value is not None:
            options[key] = value

    model_config_data = {
        "model": model_name,
        "options_json": json.dumps(options, sort_keys=True),
    }
    mc = get_or_create_model_config(model_config_data)
    logger.info(
        "ensure_model_config",
        model=model_name,
        max_tokens=options.get("max_tokens"),
        content_hash=mc.get_short_hash(),
    )
    return mc


def ensure_prompt(
    prompt_name: str,
    prompts_dir: Optional[Path] = None,
    role: str = "system",
) -> Prompt:
    """Get or create a Prompt by loading it from the prompts directory.

    Mirrors the CLI ``prompts create`` command: reads
    ``{prompts_dir}/{name}/prompt.md``, appends any example files from
    ``{prompts_dir}/{name}/examples/*.md``, then delegates to
    ``create_prompt`` for content-hash deduplication.

    Args:
        prompt_name: Subdirectory name under prompts/ (e.g. "risk_factors").
        prompts_dir: Base prompts directory.  Defaults to ``Path("prompts")``,
            matching the CLI convention (relative to the working directory).
        role: Prompt role (system, user, assistant).  Defaults to "system".

    Returns:
        The existing or newly created Prompt.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    if prompts_dir is None:
        prompts_dir = Path("prompts")

    prompt_file = prompts_dir / prompt_name / "prompt.md"
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    content = prompt_file.read_text().strip()

    # Append examples if present (sorted for deterministic hashing)
    examples_dir = prompts_dir / prompt_name / "examples"
    if examples_dir.exists() and examples_dir.is_dir():
        for example_file in sorted(examples_dir.glob("*.md")):
            content += "\n\n"
            content += example_file.read_text().strip()

    prompt_data = {
        "name": prompt_name,
        "description": f"Prompt: {prompt_name}",
        "role": role,
        "content": content,
    }
    prompt, was_created = create_prompt(prompt_data)
    logger.info(
        "ensure_prompt",
        name=prompt_name,
        was_created=was_created,
        content_hash=prompt.get_short_hash(),
    )
    return prompt
