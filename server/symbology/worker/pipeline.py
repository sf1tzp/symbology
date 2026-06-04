"""Pipeline orchestration helpers.

Shared content-generation utilities used by the page, company-group, and diff
job handlers. Replaces shell-script CLI calls (model-configs create, prompts
create) with direct Python equivalents, and exposes composable functions for
each generation stage that can be called independently for selective
regeneration.
"""

import json
from pathlib import Path
from typing import List, Optional, Tuple
from uuid import UUID

from symbology.database.model_configs import ModelConfig, get_or_create_model_config
from symbology.database.prompts import Prompt, create_prompt
from symbology.llm.client import ShutdownRequested
from symbology.utils.logging import get_logger

logger = get_logger(__name__)

# Default model tiers used by the ingestion pipeline
PIPELINE_MODEL_CONFIGS = {
    "single_summary": {
        "model_name": "claude-haiku-4-5-20251001",
        "max_tokens": 2048,
        "temperature": 0.2,
    },
    "aggregate_summary": {
        "model_name": "claude-sonnet-4-5-20250929",
        "max_tokens": 4096,
        "temperature": 0.3,
    },
    "frontpage_summary": {
        "model_name": "claude-haiku-4-5-20251001",
        "max_tokens": 512,
        "temperature": 0.3,
    },
    "company_group_analysis": {
        "model_name": "claude-sonnet-4-5-20250929",
        "max_tokens": 8192,
        "temperature": 0.3,
    },
    "company_group_frontpage": {
        "model_name": "claude-haiku-4-5-20251001",
        "max_tokens": 512,
        "temperature": 0.3,
    },
}

# Prompt names used at each pipeline stage
PIPELINE_PROMPTS = {
    "aggregate_summary": "aggregate-summary",
    "frontpage_summary": "general-summary",
    "company_group_analysis": "company-group-analysis",
    "company_group_frontpage": "company-group-frontpage",
}

# Document types per form (mirrors ingest.just)
FORM_DOCUMENT_TYPES = {
    "10-K": [
        "business_description",
        "risk_factors",
        "management_discussion",
        "controls_procedures",
    ],
    "10-Q": [
        "risk_factors",
        "management_discussion",
        "controls_procedures",
        "market_risk",
    ],
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


def load_prompt_content(
    prompt_name: str,
    prompts_dir: Optional[Path] = None,
) -> str:
    """Read a prompt's text from disk (no DB).

    Prefers the flat layout ``{prompts_dir}/{name}.md`` (one self-contained file
    per prompt — ``name`` may be a nested path like ``"l2/change-report"``).
    Falls back to the legacy ``{prompts_dir}/{name}/prompt.md`` (+ appended
    ``examples/*.md``) for prototype prompts not yet migrated to the flat layout.

    Args:
        prompt_name: Flat path under prompts/ (e.g. "l2/change-report") or a
            legacy subdirectory name (e.g. "risk_factors").
        prompts_dir: Base prompts directory.  Defaults to ``Path("prompts")``,
            relative to the working directory.

    Returns:
        The assembled prompt content, stripped.

    Raises:
        FileNotFoundError: If neither the flat nor the legacy file exists.
    """
    if prompts_dir is None:
        prompts_dir = Path("prompts")

    flat_file = prompts_dir / f"{prompt_name}.md"
    if flat_file.exists():
        return flat_file.read_text().strip()

    legacy_file = prompts_dir / prompt_name / "prompt.md"
    if not legacy_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {flat_file} or {legacy_file}")

    content = legacy_file.read_text().strip()

    # Append examples if present (sorted for deterministic hashing). Legacy only.
    examples_dir = prompts_dir / prompt_name / "examples"
    if examples_dir.exists() and examples_dir.is_dir():
        for example_file in sorted(examples_dir.glob("*.md")):
            content += "\n\n"
            content += example_file.read_text().strip()

    return content


def ensure_prompt(
    prompt_name: str,
    prompts_dir: Optional[Path] = None,
    role: str = "system",
) -> Prompt:
    """Get or create a Prompt by loading it from the prompts directory.

    Reads the content via :func:`load_prompt_content` (flat layout preferred,
    legacy fallback) then delegates to ``create_prompt`` for content-hash
    deduplication.

    Args:
        prompt_name: Flat path (e.g. "l2/change-report") or legacy subdir name.
        prompts_dir: Base prompts directory.  Defaults to ``Path("prompts")``.
        role: Prompt role (system, user, assistant).  Defaults to "system".

    Returns:
        The existing or newly created Prompt.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    content = load_prompt_content(prompt_name, prompts_dir)

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


# ---------------------------------------------------------------------------
# Composable pipeline stage functions
# ---------------------------------------------------------------------------


def generate_single_summaries(
    company_id: str,
    ticker: str,
    form: str,
    doc_type_str: str,
    filings: list,
    prompt: Prompt,
    model_config: ModelConfig,
    force: bool = False,
) -> Tuple[List[str], int, int, int]:
    """Generate single-document summaries for each filing's document of the given type.

    Args:
        company_id: UUID string of the company.
        ticker: Company ticker symbol.
        form: Filing form type (e.g. "10-K").
        doc_type_str: Document type string (e.g. "risk_factors").
        filings: List of Filing ORM objects with documents loaded.
        prompt: System prompt for single summaries.
        model_config: Model configuration for single summaries.
        force: If True, skip dedup check and always regenerate.

    Returns:
        Tuple of (content_hashes, new_count, reused_count, failed_count).
    """
    from symbology.database.documents import DocumentType, select_substantive_document
    from symbology.database.generated_content import find_existing_content_for_document
    from symbology.worker.handlers import handle_content_generation

    doc_type = DocumentType(doc_type_str)
    content_hashes: List[str] = []
    new_count = 0
    reused_count = 0
    failed_count = 0

    for filing in filings:
        doc = select_substantive_document(filing.documents, doc_type)
        if doc is None:
            logger.debug(
                "pipeline_no_document", filing_id=str(filing.id), doc_type=doc_type_str
            )
            continue
        if not doc.content_hash:
            continue

        # Dedup check (skip if force)
        if not force:
            existing = find_existing_content_for_document(
                document_id=doc.id,
                system_prompt_id=prompt.id,
                model_config_id=model_config.id,
            )
            if existing and existing.content_hash:
                logger.info(
                    "pipeline_reuse_existing",
                    filing_id=str(filing.id),
                    doc_type=doc_type_str,
                    content_hash=existing.content_hash[:12],
                )
                content_hashes.append(existing.content_hash)
                reused_count += 1
                continue

        # Generate single summary
        try:
            gen_result = handle_content_generation(
                {
                    "system_prompt_hash": prompt.content_hash,
                    "model_config_hash": str(model_config.id),
                    "source_document_hashes": [doc.content_hash],
                    "company_ticker": ticker,
                    "description": f"{doc_type_str}_single_summary",
                    "document_type": doc_type_str,
                    "form_type": form,
                    "content_stage": "single_summary",
                }
            )
            if gen_result and gen_result.get("content_hash"):
                content_hashes.append(gen_result["content_hash"])
                new_count += 1
            else:
                failed_count += 1
        except ShutdownRequested:
            raise
        except Exception as e:
            failed_count += 1
            logger.error(
                "pipeline_single_summary_failed",
                filing_id=str(filing.id),
                doc_type=doc_type_str,
                error=str(e),
            )

    return content_hashes, new_count, reused_count, failed_count


def generate_aggregate_summary(
    company_id: str,
    ticker: str,
    form: str,
    doc_type_str: str,
    single_summary_hashes: List[str],
    prompt: Prompt,
    model_config: ModelConfig,
    force: bool = False,
) -> Tuple[Optional[str], bool]:
    """Generate an aggregate summary from single-document summaries.

    Args:
        company_id: UUID string of the company.
        ticker: Company ticker symbol.
        form: Filing form type (e.g. "10-K").
        doc_type_str: Document type string (e.g. "risk_factors").
        single_summary_hashes: Content hashes of single summaries to aggregate.
        prompt: System prompt for aggregate summaries.
        model_config: Model configuration for aggregate summaries.
        force: If True, bypass the "no new singles" early return.

    Returns:
        Tuple of (content_hash_or_None, success).
    """
    from symbology.worker.handlers import handle_content_generation

    if not single_summary_hashes:
        return None, False

    try:
        result = handle_content_generation(
            {
                "system_prompt_hash": prompt.content_hash,
                "model_config_hash": str(model_config.id),
                "source_content_hashes": single_summary_hashes,
                "company_ticker": ticker,
                "description": f"{doc_type_str}_aggregate_summary",
                "document_type": doc_type_str,
                "form_type": form,
                "content_stage": "aggregate_summary",
            }
        )
        if result and result.get("content_hash"):
            return result["content_hash"], True
        return None, False
    except ShutdownRequested:
        raise
    except Exception as e:
        logger.error(
            "pipeline_aggregate_summary_failed",
            doc_type=doc_type_str,
            form=form,
            error=str(e),
        )
        return None, False


def generate_frontpage_summary(
    company_id: str,
    ticker: str,
    form: str,
    doc_type_str: str,
    aggregate_hash: str,
    prompt: Prompt,
    model_config: ModelConfig,
    force: bool = False,
) -> Tuple[Optional[str], bool]:
    """Generate a frontpage summary from an aggregate summary.

    Args:
        company_id: UUID string of the company.
        ticker: Company ticker symbol.
        form: Filing form type (e.g. "10-K").
        doc_type_str: Document type string (e.g. "risk_factors").
        aggregate_hash: Content hash of the aggregate summary.
        prompt: System prompt for frontpage summaries.
        model_config: Model configuration for frontpage summaries.
        force: If True, always regenerate.

    Returns:
        Tuple of (content_hash_or_None, success).
    """
    from symbology.worker.handlers import handle_content_generation

    try:
        result = handle_content_generation(
            {
                "system_prompt_hash": prompt.content_hash,
                "model_config_hash": str(model_config.id),
                "source_content_hashes": [aggregate_hash],
                "company_ticker": ticker,
                "description": f"{doc_type_str}_frontpage_summary",
                "document_type": doc_type_str,
                "form_type": form,
                "content_stage": "frontpage_summary",
            }
        )
        if result and result.get("content_hash"):
            return result["content_hash"], True
        return None, False
    except ShutdownRequested:
        raise
    except Exception as e:
        logger.error(
            "pipeline_frontpage_summary_failed",
            doc_type=doc_type_str,
            form=form,
            error=str(e),
        )
        return None, False


def generate_group_frontpage_summary(
    company_group_id: str,
    analysis_hash: str,
    prompt: Prompt,
    model_config: ModelConfig,
) -> Tuple[Optional[str], bool]:
    """Generate a frontpage summary from a company group analysis.

    Args:
        company_group_id: UUID string of the company group.
        analysis_hash: Content hash of the group analysis.
        prompt: System prompt for group frontpage summaries.
        model_config: Model configuration for group frontpage summaries.

    Returns:
        Tuple of (content_hash_or_None, success).
    """
    from symbology.database.base import get_db_session
    from symbology.database.generated_content import (
        ContentStage,
        compute_generation_depth,
        create_generated_content,
        get_generated_content_by_hash,
    )
    from symbology.llm.client import get_generate_response
    from symbology.llm.prompts import format_user_prompt_content

    try:
        source_content = get_generated_content_by_hash(analysis_hash)
        if not source_content:
            logger.error(
                "group_frontpage_source_not_found", analysis_hash=analysis_hash
            )
            return None, False

        user_prompt_text = format_user_prompt_content(source_content=[source_content])

        # Offload oversized prompts to Anthropic (no-op when under threshold).
        # Lazy import: config_loader imports this module at top level.
        from symbology.worker.config_loader import resolve_generation_model_config
        model_config = resolve_generation_model_config(
            model_config, f"{prompt.content}\n{user_prompt_text}"
        )

        response, warning = get_generate_response(
            model_config, prompt.content, user_prompt_text
        )

        content_data = {
            "content": response.response,
            "summary": None,
            "company_id": None,
            "company_group_id": company_group_id,
            "description": "company_group_frontpage",
            "content_stage": ContentStage.COMPANY_GROUP_FRONTPAGE,
            "generation_depth": compute_generation_depth([source_content]),
            "source_type": "generated_content",
            "model_config_id": model_config.id,
            "system_prompt_id": prompt.id,
            "total_duration": response.total_duration,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "warning": warning,
        }
        generated, was_created = create_generated_content(content_data)

        session = get_db_session()
        generated.source_content = [source_content]
        session.commit()

        logger.info(
            "group_frontpage_summary_generated",
            content_id=str(generated.id),
            company_group_id=company_group_id,
        )
        return generated.content_hash, True
    except ShutdownRequested:
        raise
    except Exception as e:
        logger.error(
            "pipeline_group_frontpage_summary_failed",
            company_group_id=company_group_id,
            error=str(e),
        )
        return None, False


def generate_page_content(
    stage: str,
    source_content_hashes: List[str],
    prompt: Prompt,
    model_config: ModelConfig,
    *,
    ticker: Optional[str] = None,
    company_group_id: Optional[UUID] = None,
    filing_id: Optional[UUID] = None,
    document_id: Optional[UUID] = None,
    document_type: Optional[str] = None,
    form_type: Optional[str] = None,
    description: Optional[str] = None,
    force: bool = False,
) -> Tuple[Optional[str], bool]:
    """Generate one page-content piece for any of the new content stages.

    Uniform write for the new stages: N already-gathered source-content hashes
    -> one LLM call -> one GeneratedContent row tagged with ``stage`` and the
    appropriate subject/scope FK. Source gathering is the caller's (page
    pipeline's) job. ``generation_depth`` is set automatically from the sources.

    Args:
        stage: ContentStage value (e.g. "company_main_content").
        source_content_hashes: Content hashes of the source GeneratedContent.
        prompt: System prompt for this stage.
        model_config: Model configuration for this stage.
        ticker: Company ticker (resolves company_id) for company-scoped stages.
        company_group_id / filing_id / document_id: Subject/scope FK for the
            relevant page type (set exactly one for the new page-content stages).
        document_type / form_type: Optional structured metadata.
        description: Optional description (defaults to the stage name).
        force: If True, skip the dedup check and always regenerate.

    Returns:
        Tuple of (content_hash_or_None, success).
    """
    from symbology.database.generated_content import find_existing_page_content
    from symbology.worker.handlers import handle_content_generation

    if not source_content_hashes:
        return None, False

    # Dedup (skip if force): reuse content already generated for the same stage
    # from the same sources with the same prompt + model config, mirroring the
    # L1 reuse in generate_single_summaries so page intros don't re-call the LLM.
    if not force:
        existing = find_existing_page_content(
            content_stage=stage,
            source_content_hashes=source_content_hashes,
            system_prompt_id=prompt.id,
            model_config_id=model_config.id,
        )
        if existing and existing.content_hash:
            logger.info(
                "pipeline_reuse_existing_page_content",
                stage=stage,
                content_hash=existing.content_hash[:12],
            )
            return existing.content_hash, True

    try:
        result = handle_content_generation(
            {
                "system_prompt_hash": prompt.content_hash,
                "model_config_hash": str(model_config.id),
                "source_content_hashes": source_content_hashes,
                "company_ticker": ticker,
                "company_group_id": company_group_id,
                "filing_id": filing_id,
                "document_id": document_id,
                "document_type": document_type,
                "form_type": form_type,
                "content_stage": stage,
                "description": description or stage,
            }
        )
        if result and result.get("content_hash"):
            return result["content_hash"], True
        return None, False
    except ShutdownRequested:
        raise
    except Exception as e:
        logger.error("pipeline_page_content_failed", stage=stage, error=str(e))
        return None, False
