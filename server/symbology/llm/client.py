import json
import re
import time

from typing import Dict, List

import anthropic

from symbology.database.model_configs import ModelConfig
from symbology.utils.config import settings
from symbology.utils.logging import get_logger

logger = get_logger(__name__)


class AnthropicResponseAdapter:
    """Adapter that maps Anthropic API responses to the interface callers expect."""

    def __init__(self, message, duration_ns):
        self.response = message.content[0].text
        self.content = self.response
        self.total_duration = duration_ns
        self.done = True
        self.done_reason = message.stop_reason
        self.input_tokens = message.usage.input_tokens
        self.output_tokens = message.usage.output_tokens


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


def get_chat_response(
        model_config: ModelConfig,
        messages: List[Dict],
        client=None,
    ) -> tuple:

    if not client:
        client = init_client()

    logger.info("sending_chat_request", model=model_config.model)

    options_dict = json.loads(model_config.options_json)
    max_tokens = options_dict.get('max_tokens', 4096)
    temperature = options_dict.get('temperature', 0.8)

    start_ns = time.time_ns()
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

    logger.info("received_chat_response",
        model=model_config.model,
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
    if not client:
        client = init_client()

    logger.info("sending_generate_request", model=model_config.model)

    options_dict = json.loads(model_config.options_json)
    max_tokens = options_dict.get('max_tokens', 4096)
    temperature = options_dict.get('temperature', 0.8)

    start_ns = time.time_ns()
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

    logger.info("received_generate_response",
        model=model_config.model,
        done=adapter.done,
        done_reason=adapter.done_reason,
        duration=f"{duration_ns / 1e9:.2f}s",
        input_tokens=adapter.input_tokens,
        output_tokens=adapter.output_tokens,
    )

    return adapter, None
