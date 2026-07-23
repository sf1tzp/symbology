"""Routing + adapter tests for the dual-provider LLM client.

Verifies that ``model`` selects the provider (``claude*`` -> Anthropic, else ->
the OpenAI-compatible endpoint), that both response adapters expose the same
interface, and that OpenAI token usage is None-guarded. No network or DB: fake
clients are passed in via the ``client=`` argument.
"""
import json
import types

import pytest

from symbology.database.model_configs import ModelConfig
from symbology.llm.client import (
    _is_retryable,
    _provider_for,
    get_chat_response,
    get_generate_response,
    retry_backoff,
    sampling_params_removed,
)

ADAPTER_ATTRS = (
    "response",
    "content",
    "total_duration",
    "done",
    "done_reason",
    "input_tokens",
    "output_tokens",
)


def _model_config(model: str) -> ModelConfig:
    """An unsaved ModelConfig carrying only the canonical options."""
    return ModelConfig(
        model=model,
        options_json=json.dumps({"max_tokens": 256, "temperature": 0.3}),
    )


class _FakeAnthropicClient:
    def __init__(self):
        self.calls = []
        self.messages = types.SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(text="hello from claude")],
            stop_reason="end_turn",
            usage=types.SimpleNamespace(input_tokens=10, output_tokens=5),
        )


class _FakeOpenAIClient:
    def __init__(self, with_usage: bool = True):
        self.calls = []
        self._with_usage = with_usage
        self.chat = types.SimpleNamespace(
            completions=types.SimpleNamespace(create=self._create)
        )

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        usage = (
            types.SimpleNamespace(prompt_tokens=7, completion_tokens=3)
            if self._with_usage
            else None
        )
        return types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    message=types.SimpleNamespace(content="hello from gemma"),
                    finish_reason="stop",
                )
            ],
            usage=usage,
        )


def test_provider_for_routing():
    assert _provider_for("claude-haiku-4-5-20251001") == "anthropic"
    assert _provider_for("claude-sonnet-4-5-20250929") == "anthropic"
    assert _provider_for("Claude-Opus") == "anthropic"  # case-insensitive
    assert _provider_for("google/gemma-4-e4b") == "openai"
    assert _provider_for("gpt-oss-120b") == "openai"


def test_generate_routes_to_anthropic():
    client = _FakeAnthropicClient()
    adapter, _ = get_generate_response(
        _model_config("claude-haiku-4-5-20251001"), "sys", "usr", client=client
    )

    assert adapter.response == "hello from claude"
    assert adapter.content == "hello from claude"
    assert adapter.done is True
    assert adapter.done_reason == "end_turn"
    assert adapter.input_tokens == 10
    assert adapter.output_tokens == 5
    # Anthropic call shape: system kwarg + single user message.
    sent = client.calls[0]
    assert sent["system"] == "sys"
    assert sent["messages"] == [{"role": "user", "content": "usr"}]
    assert sent["max_tokens"] == 256 and sent["temperature"] == 0.3


def test_sampling_params_removed_classification():
    # Sonnet 5+ / Opus 4.7+ / Claude 5 tier reject temperature (400).
    assert sampling_params_removed("claude-sonnet-5") is True
    assert sampling_params_removed("claude-opus-4-7") is True
    assert sampling_params_removed("claude-opus-4-8") is True
    assert sampling_params_removed("claude-fable-5") is True
    # Older families still accept the configured temperature.
    assert sampling_params_removed("claude-sonnet-4-6") is False
    assert sampling_params_removed("claude-sonnet-4-5-20250929") is False
    assert sampling_params_removed("claude-haiku-4-5-20251001") is False


def test_generate_sonnet_5_omits_sampling_and_disables_thinking():
    """Sonnet 5 rejects temperature with a 400 and runs adaptive thinking by
    default; the client must send neither temperature nor an implicit-thinking
    request (max_tokens is sized for text output only)."""
    client = _FakeAnthropicClient()
    adapter, _ = get_generate_response(
        _model_config("claude-sonnet-5"), "sys", "usr", client=client
    )

    assert adapter.response == "hello from claude"
    sent = client.calls[0]
    assert "temperature" not in sent
    assert sent["thinking"] == {"type": "disabled"}
    assert sent["max_tokens"] == 256


def test_chat_sonnet_5_omits_sampling_and_disables_thinking():
    client = _FakeAnthropicClient()
    get_chat_response(
        _model_config("claude-sonnet-5"),
        [{"role": "user", "content": "hi"}],
        client=client,
    )
    sent = client.calls[0]
    assert "temperature" not in sent
    assert sent["thinking"] == {"type": "disabled"}


def test_generate_older_claude_keeps_temperature():
    client = _FakeAnthropicClient()
    get_generate_response(
        _model_config("claude-haiku-4-5-20251001"), "sys", "usr", client=client
    )
    sent = client.calls[0]
    assert sent["temperature"] == 0.3
    assert "thinking" not in sent


def test_generate_routes_to_openai():
    client = _FakeOpenAIClient()
    adapter, _ = get_generate_response(
        _model_config("google/gemma-4-e4b"), "sys", "usr", client=client
    )

    assert adapter.response == "hello from gemma"
    assert adapter.done_reason == "stop"
    assert adapter.input_tokens == 7
    assert adapter.output_tokens == 3
    # OpenAI call shape: system + user folded into the messages list.
    sent = client.calls[0]
    assert sent["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "usr"},
    ]
    assert sent["max_tokens"] == 256 and sent["temperature"] == 0.3


def test_openai_usage_none_guard():
    client = _FakeOpenAIClient(with_usage=False)
    adapter, _ = get_generate_response(
        _model_config("google/gemma-4-e4b"), "sys", "usr", client=client
    )
    assert adapter.input_tokens is None
    assert adapter.output_tokens is None


def test_chat_routes_both_providers():
    messages = [{"role": "user", "content": "hi"}]

    anthropic_client = _FakeAnthropicClient()
    a_adapter, _ = get_chat_response(
        _model_config("claude-haiku-4-5-20251001"), messages, client=anthropic_client
    )
    assert a_adapter.response == "hello from claude"
    assert anthropic_client.calls[0]["messages"] == messages

    openai_client = _FakeOpenAIClient()
    o_adapter, _ = get_chat_response(
        _model_config("google/gemma-4-e4b"), messages, client=openai_client
    )
    assert o_adapter.response == "hello from gemma"
    assert openai_client.calls[0]["messages"] == messages


def test_both_adapters_expose_full_interface():
    a_adapter, _ = get_generate_response(
        _model_config("claude-haiku-4-5-20251001"), "s", "u", client=_FakeAnthropicClient()
    )
    o_adapter, _ = get_generate_response(
        _model_config("google/gemma-4-e4b"), "s", "u", client=_FakeOpenAIClient()
    )
    for attr in ADAPTER_ATTRS:
        assert hasattr(a_adapter, attr), f"anthropic adapter missing {attr}"
        assert hasattr(o_adapter, attr), f"openai adapter missing {attr}"


def test_is_retryable_classification():
    # Programming/config errors — never retry.
    assert _is_retryable(TypeError("auth")) is False
    assert _is_retryable(ValueError()) is False
    # Connection-style errors — retry.
    assert _is_retryable(ConnectionError()) is True

    class _Status(Exception):
        def __init__(self, code):
            self.status_code = code

    assert _is_retryable(_Status(400)) is False   # bad request
    assert _is_retryable(_Status(401)) is False   # auth
    assert _is_retryable(_Status(429)) is True    # rate limit
    assert _is_retryable(_Status(503)) is True    # server error


def test_retry_backoff_fails_fast_on_non_retryable():
    calls = []

    def _boom():
        calls.append(1)
        raise TypeError("Could not resolve authentication method")

    with pytest.raises(TypeError):
        retry_backoff(3600, _boom)
    assert len(calls) == 1  # no retry loop — failed immediately
