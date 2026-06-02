import json
import re
import time

from typing import Dict, List, Optional

import anthropic
from openai import OpenAI

from symbology.database.model_configs import ModelConfig
from symbology.llm.model_loader import ensure_model_loaded
from symbology.utils.config import settings
from symbology.utils.logging import get_logger

logger = get_logger(__name__)


def _provider_for(model: str) -> str:
    """Route a model name to a provider.

    Anything whose name starts with ``claude`` goes to the Anthropic API;
    everything else (e.g. ``google/gemma-4-e4b``) goes to the internal
    OpenAI-compatible endpoint. The catch-all means a typo'd claude model
    routes to OpenAI, so the resolved provider is logged per request.
    """
    return "anthropic" if model.lower().startswith("claude") else "openai"


class AnthropicResponseAdapter:
    """Adapter that maps Anthropic API responses to the interface callers expect."""

    def __init__(self, message, duration_ns):
        self.response = message.content[0].text
        self.content = self.response
        self.total_duration = duration_ns / 1e9
        self.done = True
        self.done_reason = message.stop_reason
        self.input_tokens = message.usage.input_tokens
        self.output_tokens = message.usage.output_tokens


class OpenAIResponseAdapter:
    """Adapter mapping OpenAI-compatible chat completions to the same interface.

    Exposes the identical attributes as :class:`AnthropicResponseAdapter` so all
    callers work unchanged regardless of provider. Token usage is None-guarded
    because some local servers omit the ``usage`` block.
    """

    def __init__(self, completion, duration_ns):
        choice = completion.choices[0]
        self.response = choice.message.content
        self.content = self.response
        self.total_duration = duration_ns / 1e9
        self.done = True
        self.done_reason = choice.finish_reason
        usage = getattr(completion, "usage", None)
        self.input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        self.output_tokens = getattr(usage, "completion_tokens", None) if usage else None


class ShutdownRequested(Exception):
    """Raised when a shutdown signal is received during a backoff sleep."""


# Global flag set by the worker's signal handler so that retry_backoff
# can break out of long sleeps promptly.
_shutdown_flag = False


def set_shutdown_flag():
    """Signal retry_backoff loops to abort."""
    global _shutdown_flag
    _shutdown_flag = True


def reset_shutdown_flag():
    """Reset the shutdown flag (e.g. at worker start)."""
    global _shutdown_flag
    _shutdown_flag = False


def _is_retryable(e: Exception) -> bool:
    """Whether an exception from the LLM call is worth retrying.

    Retry transient failures (network blips, rate limits, server errors) but fail
    fast on clear programming/config errors (e.g. the SDK's "Could not resolve
    authentication method" TypeError) and other 4xx client errors — retrying those
    just burns the whole timeout without any chance of success.
    """
    # Programming / configuration errors — never transient.
    if isinstance(e, (TypeError, ValueError, KeyError, AttributeError)):
        return False
    # HTTP status, if the SDK exception exposes one (anthropic/openai APIStatusError).
    status = getattr(e, "status_code", None)
    if isinstance(status, int):
        return status == 429 or status >= 500  # rate limit + server errors only
    # Unknown (e.g. connection/timeout errors) — treat as transient.
    return True


def retry_backoff(timeout, func, *args, **kwargs):
    backoff = 1
    logger.debug("retry_backoff", backoff=backoff, timeout=timeout, func=func, args=args, kwargs=kwargs)
    start = time.time()
    while time.time() - start < timeout:
        if _shutdown_flag:
            raise ShutdownRequested("shutdown requested during retry backoff")

        try:
            result = func(*args, **kwargs)
            return result

        except Exception as e:
            if not _is_retryable(e):
                logger.error("retry_backoff_non_retryable", error=e, error_type=type(e).__name__)
                raise
            logger.error("retry_backoff", backoff=backoff, error=e)
            backoff = min(300, backoff * 2)
            # Sleep in 1-second increments so we can respond to shutdown signals
            sleep_until = time.time() + backoff
            while time.time() < sleep_until:
                if _shutdown_flag:
                    raise ShutdownRequested("shutdown requested during retry backoff")
                time.sleep(min(1.0, sleep_until - time.time()))
    else:
        raise TimeoutError


def init_client(api_key: str = None):
    key = api_key or settings.anthropic.api_key
    client = anthropic.Anthropic(api_key=key)
    logger.debug('initialized_anthropic_client')
    return client


def init_openai_chat_client(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: Optional[float] = None,
) -> OpenAI:
    """Create an OpenAI client pointed at the shared OpenAI-compatible endpoint.

    Reuses ``settings.openai`` — the same ``OPENAI_*`` host/port used for
    embeddings. Mirrors :func:`symbology.llm.embeddings.init_embedding_client`.
    """
    cfg = settings.openai
    client = OpenAI(
        base_url=base_url or cfg.base_url,
        api_key=api_key or cfg.api_key,
        # Long per-request timeout: local generation can take minutes.
        timeout=timeout if timeout is not None else cfg.chat_request_timeout,
        # Let retry_backoff own retries (with its retryable/non-retryable
        # classification) — disable the SDK's separate internal retry layer.
        max_retries=0,
    )
    logger.debug("initialized_openai_chat_client", base_url=base_url or cfg.base_url)
    return client


def get_chat_response(
        model_config: ModelConfig,
        messages: List[Dict],
        client=None,
    ) -> tuple:

    provider = _provider_for(model_config.model)

    options_dict = json.loads(model_config.options_json)
    max_tokens = options_dict.get('max_tokens', 4096)
    temperature = options_dict.get('temperature', 0.8)

    logger.info("sending_chat_request", model=model_config.model, provider=provider)

    start_ns = time.time_ns()
    if provider == "anthropic":
        if not client:
            client = init_client()
        message = retry_backoff(
            3600,
            client.messages.create,
            model=model_config.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
        )
        duration_ns = time.time_ns() - start_ns
        adapter = AnthropicResponseAdapter(message, duration_ns)
    else:
        if not client:
            client = init_openai_chat_client()
        # Size the served model's context window to this request and route to a
        # large-enough instance (no-op unless OPENAI_MANAGE_CONTEXT is enabled;
        # falls back to the bare model name). Estimate from the message text.
        prompt_text = "\n".join(str(m.get("content", "")) for m in messages)
        instance_id = ensure_model_loaded(model_config.model, prompt_text, max_tokens)
        completion = retry_backoff(
            settings.openai.retry_timeout,
            client.chat.completions.create,
            model=instance_id or model_config.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
        )
        duration_ns = time.time_ns() - start_ns
        adapter = OpenAIResponseAdapter(completion, duration_ns)

    logger.info("received_chat_response",
        model=model_config.model,
        provider=provider,
        done=adapter.done,
        done_reason=adapter.done_reason,
        duration=f"{duration_ns / 1e9:.2f}s",
        input_tokens=adapter.input_tokens,
        output_tokens=adapter.output_tokens,
    )

    return adapter, None


def remove_thinking_tags(content: str):
    if not content:
        return None

    # Remove <think>...</think> blocks and any content before them
    cleaned = re.sub(r'<think>[\s\S]*?</think>\s*', '', content, flags=re.IGNORECASE)

    # Trim any remaining whitespace
    cleaned = cleaned.strip()

    return cleaned or None


def get_generate_response(model_config: ModelConfig, system_prompt: str, user_prompt: str, client=None) -> tuple:
    provider = _provider_for(model_config.model)

    options_dict = json.loads(model_config.options_json)
    max_tokens = options_dict.get('max_tokens', 4096)
    temperature = options_dict.get('temperature', 0.8)

    logger.info("sending_generate_request", model=model_config.model, provider=provider)

    start_ns = time.time_ns()
    if provider == "anthropic":
        if not client:
            client = init_client()
        message = retry_backoff(
            timeout=3600,
            func=client.messages.create,
            model=model_config.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        duration_ns = time.time_ns() - start_ns
        adapter = AnthropicResponseAdapter(message, duration_ns)
    else:
        if not client:
            client = init_openai_chat_client()
        # Size the served model's context window to this request and route to a
        # large-enough instance (no-op unless OPENAI_MANAGE_CONTEXT is enabled;
        # falls back to the bare model name).
        instance_id = ensure_model_loaded(
            model_config.model, f"{system_prompt}\n{user_prompt}", max_tokens
        )
        completion = retry_backoff(
            settings.openai.retry_timeout,
            client.chat.completions.create,
            model=instance_id or model_config.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        duration_ns = time.time_ns() - start_ns
        adapter = OpenAIResponseAdapter(completion, duration_ns)

    logger.info("received_generate_response",
        model=model_config.model,
        provider=provider,
        done=adapter.done,
        done_reason=adapter.done_reason,
        duration=f"{duration_ns / 1e9:.2f}s",
        input_tokens=adapter.input_tokens,
        output_tokens=adapter.output_tokens,
    )

    return adapter, None
