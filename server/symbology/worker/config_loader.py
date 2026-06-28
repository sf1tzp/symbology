"""Declarative pipeline configuration loaded from ``prompts/model_configs.yaml``.

Replaces the hardcoded dicts in ``pipeline.py`` for the new content stages:
model configs (model + ``{max_tokens, temperature}``), stage->prompt paths,
per-document-type L1 prompts, and the form->document-types map. The YAML is the
source of truth for the *current* config; ModelConfig/Prompt rows are still
created lazily by ``ensure_*`` at run time and deduped by content hash.
"""
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml

from symbology.database.generated_content import ContentStage
from symbology.utils.logging import get_logger
from symbology.worker.pipeline import load_prompt_content

logger = get_logger(__name__)

DEFAULT_PROMPTS_DIR = Path("prompts")
CONFIG_FILENAME = "model_configs.yaml"

_REQUIRED_OPTION_KEYS = ("model", "max_tokens", "temperature")
_VALID_STAGES = {stage.value for stage in ContentStage}


@dataclass(frozen=True)
class PipelineConfig:
    """Parsed, validated pipeline configuration."""

    prompts_dir: Path
    model_configs: Dict[str, Dict]
    prompts: Dict[str, str]
    doc_type_prompts: Dict[str, str]
    form_document_types: Dict[str, List[str]]
    # Per-form document type the company main content (L3) is anchored on. A 10-K
    # leads with its business description; a 10-Q has none, so it leads with MD&A.
    form_main_content_source: Dict[str, str] = field(default_factory=dict)

    def main_content_source(self, form: str) -> str:
        """The change-report document type to anchor a form's company main content."""
        return self.form_main_content_source.get(form, "business_description")

    def model_config_options(self, stage: str) -> Dict:
        """The ``{model, max_tokens, temperature}`` for a stage."""
        cfg = self.model_configs[stage]
        return {
            "model": cfg["model"],
            "max_tokens": cfg["max_tokens"],
            "temperature": cfg["temperature"],
        }

    def prompt_path(self, stage: str) -> str:
        """The flat prompt path for a stage (e.g. ``"l2/change-report"``)."""
        return self.prompts[stage]

    def doc_type_prompt_path(self, doc_type: str) -> str:
        """The flat L1 prompt path for a document type."""
        return self.doc_type_prompts[doc_type]


def _validate(data: Dict, prompts_dir: Path) -> None:
    """Fail loudly on a malformed or drifted config."""
    for key in ("model_configs", "prompts", "doc_type_prompts", "form_document_types"):
        if key not in data or not isinstance(data[key], dict):
            raise ValueError(f"model_configs.yaml: missing or invalid '{key}' section")

    # model_configs keys are free-form profile names (e.g. "l1_document_summary"),
    # not ContentStage values — they're addressed directly by the pipelines.
    for profile, cfg in data["model_configs"].items():
        missing = [k for k in _REQUIRED_OPTION_KEYS if k not in cfg]
        if missing:
            raise ValueError(f"model_configs.yaml: profile '{profile}' missing option(s): {missing}")

    # prompts map a ContentStage -> prompt file, so their keys must be valid stages.
    for stage, path in data["prompts"].items():
        if stage not in _VALID_STAGES:
            raise ValueError(f"model_configs.yaml: unknown ContentStage '{stage}' in prompts")
        # Resolves the file (flat or legacy); raises FileNotFoundError if missing.
        load_prompt_content(path, prompts_dir)

    for doc_type, path in data["doc_type_prompts"].items():
        load_prompt_content(path, prompts_dir)


@lru_cache(maxsize=None)
def load_pipeline_config(prompts_dir: Optional[Union[str, Path]] = None) -> PipelineConfig:
    """Load and validate ``{prompts_dir}/model_configs.yaml`` (cached).

    Args:
        prompts_dir: Base prompts directory. Defaults to ``Path("prompts")``,
            relative to the working directory (worker/CLI run from ``server/``).

    Returns:
        The parsed, validated :class:`PipelineConfig`.

    Raises:
        FileNotFoundError: If the YAML or any referenced prompt file is missing.
        ValueError: If the config is malformed or references an unknown stage.
    """
    base = Path(prompts_dir) if prompts_dir else DEFAULT_PROMPTS_DIR
    config_file = base / CONFIG_FILENAME
    if not config_file.exists():
        raise FileNotFoundError(f"Pipeline config not found: {config_file}")

    data = yaml.safe_load(config_file.read_text()) or {}
    _validate(data, base)

    logger.info(
        "loaded_pipeline_config",
        stages=len(data["model_configs"]),
        prompts=len(data["prompts"]),
        doc_types=len(data["doc_type_prompts"]),
    )
    return PipelineConfig(
        prompts_dir=base,
        model_configs=data["model_configs"],
        prompts=data["prompts"],
        doc_type_prompts=data["doc_type_prompts"],
        form_document_types=data["form_document_types"],
        form_main_content_source=data.get("form_main_content_source", {}),
    )


def ensure_stage_model_config(stage: str, prompts_dir: Optional[Union[str, Path]] = None):
    """Get or create the ModelConfig for a stage from the YAML.

    Builds ``options_json`` as ``{max_tokens, temperature}`` directly (NOT via
    ``ModelConfig.create_default``, which would inject top_k/top_p) and delegates
    to ``get_or_create_model_config`` for content-hash dedup.
    """
    import json

    from symbology.database.model_configs import get_or_create_model_config

    cfg = load_pipeline_config(prompts_dir).model_config_options(stage)
    options = {"max_tokens": cfg["max_tokens"], "temperature": cfg["temperature"]}
    return get_or_create_model_config({
        "model": cfg["model"],
        "options_json": json.dumps(options, sort_keys=True),
    })


def resolve_generation_model_config(model_config, prompt_text: str):
    """Offload oversized prompts from the local OpenAI endpoint to Anthropic.

    Returns the ModelConfig the caller should both **use and record**: the
    original when the request fits the local model, or an Anthropic ModelConfig
    (mirroring the original's ``max_tokens``/``temperature``) when the request's
    estimated context usage exceeds ``OPENAI_OVERFLOW_THRESHOLD_TOKENS`` (the
    local model's context ceiling).

    The fit check uses the same math as dynamic context sizing
    (``requested_context_tokens`` = ``(prompt + max_output) * safety_margin``),
    so the reroute decision and the local window sizer never disagree about what
    a request costs. Counting ``max_output`` is essential: the context window
    must hold prompt **and** completion, so a prompt that looks small on its own
    can still overflow once its output is reserved. Huge sections (e.g. a long
    risk_factors) are also slow to serve locally; Anthropic models have a far
    larger context.

    The swapped config is built like the YAML stage configs (``{max_tokens,
    temperature}`` only) so it dedups against any existing Anthropic config for
    the same model/options.

    No-op (returns the original) when overflow is disabled, the prompt fits, the
    model is already an Anthropic one, or no Anthropic API key is configured.
    """
    import json

    from symbology.llm.client import _provider_for
    from symbology.llm.model_loader import estimate_tokens, requested_context_tokens
    from symbology.utils.config import settings

    cfg = settings.openai
    threshold = cfg.overflow_threshold_tokens
    if not threshold:
        return model_config
    # Only offload local (OpenAI-compatible) requests; leave Anthropic ones be.
    if _provider_for(model_config.model) != "openai":
        return model_config

    options = json.loads(model_config.options_json)
    max_output = options.get("max_tokens", 4096)
    prompt_tokens = estimate_tokens(prompt_text)
    # Total context the request consumes (prompt + reserved output + margin),
    # compared against the local model's context ceiling.
    required = requested_context_tokens(prompt_tokens, max_output)
    if required <= threshold:
        return model_config

    overflow_config = build_overflow_model_config(model_config)
    if overflow_config is None:
        logger.warning(
            "overflow_skipped",
            reason="no_anthropic_model_or_key",
            prompt_tokens=prompt_tokens,
            max_output=max_output,
            required=required,
            threshold=threshold,
            model=model_config.model,
        )
        return model_config

    logger.info(
        "overflow_to_anthropic",
        prompt_tokens=prompt_tokens,
        max_output=max_output,
        required=required,
        threshold=threshold,
        from_model=model_config.model,
        to_model=overflow_config.model,
        to_config=overflow_config.get_short_hash(),
    )
    return overflow_config


def build_overflow_model_config(model_config):
    """Build the Anthropic overflow ModelConfig mirroring ``model_config``'s options.

    Shared by the preemptive offload (:func:`resolve_generation_model_config`) and
    the reactive fallback (:func:`generate_with_overflow`). The swapped config keeps
    only ``{max_tokens, temperature}`` so it dedups against any existing Anthropic
    config for the same model/options.

    Returns ``None`` when offload isn't possible: the model is already an Anthropic
    one, no overflow/default Anthropic model is configured, or no Anthropic API key
    is set.
    """
    import json

    from symbology.database.model_configs import get_or_create_model_config
    from symbology.llm.client import _provider_for
    from symbology.utils.config import settings

    if _provider_for(model_config.model) != "openai":
        return None

    overflow_model = settings.openai.overflow_model or settings.anthropic.default_model
    if not overflow_model or not settings.anthropic.api_key:
        return None

    options = json.loads(model_config.options_json)
    return get_or_create_model_config({
        "model": overflow_model,
        "options_json": json.dumps(
            {
                "max_tokens": options.get("max_tokens", 4096),
                "temperature": options.get("temperature", 0.8),
            },
            sort_keys=True,
        ),
    })


def generate_with_overflow(base_model_config, system_prompt: str, user_prompt: str):
    """Generate content, offloading oversized requests to Anthropic.

    Consolidates the offload-then-generate pattern shared by the worker content
    handlers into a single call with two layers of protection against the local
    model's context ceiling:

    1. **Preemptive** — :func:`resolve_generation_model_config` estimates the
       request's context usage and reroutes to Anthropic before calling if it
       looks too large.
    2. **Reactive** — if the estimate undershoots and the local endpoint returns
       ``Context size has been exceeded.``, swap to the Anthropic overflow model
       and retry once.

    Returns ``(response, warning, model_config_used)``. The returned config is the
    one the caller should **record**, so provenance (and dedup) reflect whichever
    model actually served the request — local or the reactive Anthropic fallback.
    """
    from symbology.llm.client import get_generate_response, is_context_overflow_error

    model_config = resolve_generation_model_config(
        base_model_config, f"{system_prompt}\n{user_prompt}"
    )
    try:
        response, warning = get_generate_response(
            model_config, system_prompt, user_prompt
        )
        return response, warning, model_config
    except Exception as e:
        if not is_context_overflow_error(e):
            raise
        overflow_config = build_overflow_model_config(model_config)
        if overflow_config is None:
            logger.warning(
                "context_overflow_no_fallback",
                model=model_config.model,
                error=str(e),
            )
            raise
        logger.warning(
            "context_overflow_reactive_fallback",
            from_model=model_config.model,
            to_model=overflow_config.model,
            to_config=overflow_config.get_short_hash(),
            error=str(e),
        )
        response, warning = get_generate_response(
            overflow_config, system_prompt, user_prompt
        )
        return response, warning, overflow_config
