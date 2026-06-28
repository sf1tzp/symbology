"""Tests for offloading oversized prompts from the local endpoint to Anthropic.

Exercises ``resolve_generation_model_config``: the no-op cases (disabled, under
threshold, already-Anthropic, missing key) and the swap case. ``get_or_create_model_config``
is monkeypatched in the swap case so no DB is touched.
"""
import json

import symbology.worker.config_loader as cl
from symbology.database.model_configs import ModelConfig
from symbology.utils.config import settings


def _mc(model: str, max_tokens: int = 4096, temperature: float = 0.3) -> ModelConfig:
    return ModelConfig(
        model=model,
        options_json=json.dumps(
            {"max_tokens": max_tokens, "temperature": temperature}, sort_keys=True
        ),
    )


def _huge_prompt(tokens: int) -> str:
    return "x" * int(tokens * settings.openai.chars_per_token)


def test_no_offload_when_disabled(monkeypatch):
    monkeypatch.setattr(settings.openai, "overflow_threshold_tokens", 0)
    mc = _mc("google/gemma-4-e4b")
    assert cl.resolve_generation_model_config(mc, _huge_prompt(100_000)) is mc


def test_no_offload_under_threshold(monkeypatch):
    monkeypatch.setattr(settings.openai, "overflow_threshold_tokens", 45000)
    mc = _mc("google/gemma-4-e4b")
    assert cl.resolve_generation_model_config(mc, "a short prompt") is mc


def test_offload_counts_output_tokens(monkeypatch):
    """Regression: a prompt that fits on its own can still overflow once its
    reserved output is counted. Reproduces the production failure (prompt ~23k,
    output 8192, 32k local ceiling) that the prompt-only check let through."""
    monkeypatch.setattr(settings.openai, "overflow_threshold_tokens", 32000)
    monkeypatch.setattr(settings.openai, "overflow_model", "claude-sonnet-4-6")
    monkeypatch.setattr(settings.anthropic, "api_key", "sk-test")
    monkeypatch.setattr(
        "symbology.database.model_configs.get_or_create_model_config",
        lambda data: _mc(data["model"]),
    )

    # 22959 prompt tokens alone is well under the 32000 ceiling, but
    # (22959 + 8192) * 1.15 ≈ 35723 > 32000, so it must offload.
    mc = _mc("google/gemma-4-e4b", max_tokens=8192)
    out = cl.resolve_generation_model_config(mc, _huge_prompt(22959))
    assert out.model == "claude-sonnet-4-6"


def test_no_offload_for_large_prompt_with_small_output(monkeypatch):
    """Budget guard: the shared math means a large prompt with a small output
    stays local instead of needlessly rerouting (the failing of a lowered
    prompt-only threshold)."""
    monkeypatch.setattr(settings.openai, "overflow_threshold_tokens", 32000)
    monkeypatch.setattr(settings.anthropic, "api_key", "sk-test")
    # (25000 + 1000) * 1.15 = 29900 <= 32000 -> stays local.
    mc = _mc("google/gemma-4-e4b", max_tokens=1000)
    assert cl.resolve_generation_model_config(mc, _huge_prompt(25000)) is mc


def test_no_offload_for_anthropic_model(monkeypatch):
    monkeypatch.setattr(settings.openai, "overflow_threshold_tokens", 1)
    mc = _mc("claude-haiku-4-5-20251001")
    # Already Anthropic -> returned unchanged even though it's over threshold.
    assert cl.resolve_generation_model_config(mc, _huge_prompt(1000)) is mc


def test_offload_skipped_without_anthropic_key(monkeypatch):
    monkeypatch.setattr(settings.openai, "overflow_threshold_tokens", 1)
    monkeypatch.setattr(settings.openai, "overflow_model", "claude-haiku-4-5-20251001")
    monkeypatch.setattr(settings.anthropic, "api_key", "")
    mc = _mc("google/gemma-4-e4b")
    assert cl.resolve_generation_model_config(mc, _huge_prompt(1000)) is mc


def test_offload_swaps_to_anthropic_and_mirrors_options(monkeypatch):
    monkeypatch.setattr(settings.openai, "overflow_threshold_tokens", 45000)
    monkeypatch.setattr(settings.openai, "overflow_model", "claude-sonnet-4-5-20250929")
    monkeypatch.setattr(settings.anthropic, "api_key", "sk-test")

    captured = {}

    def _fake_goc(data):
        captured.update(data)
        return _mc(data["model"])

    monkeypatch.setattr(
        "symbology.database.model_configs.get_or_create_model_config", _fake_goc
    )

    mc = _mc("google/gemma-4-e4b", max_tokens=8192, temperature=0.2)
    out = cl.resolve_generation_model_config(mc, _huge_prompt(46000))

    assert out.model == "claude-sonnet-4-5-20250929"
    assert captured["model"] == "claude-sonnet-4-5-20250929"
    # Options mirror the local config (max_tokens/temperature), no top_k/top_p.
    assert json.loads(captured["options_json"]) == {"max_tokens": 8192, "temperature": 0.2}


def test_offload_falls_back_to_anthropic_default_model(monkeypatch):
    monkeypatch.setattr(settings.openai, "overflow_threshold_tokens", 45000)
    monkeypatch.setattr(settings.openai, "overflow_model", "")  # -> use default_model
    monkeypatch.setattr(settings.anthropic, "api_key", "sk-test")
    monkeypatch.setattr(settings.anthropic, "default_model", "claude-haiku-4-5-20251001")

    monkeypatch.setattr(
        "symbology.database.model_configs.get_or_create_model_config",
        lambda data: _mc(data["model"]),
    )

    mc = _mc("google/gemma-4-e4b")
    out = cl.resolve_generation_model_config(mc, _huge_prompt(46000))
    assert out.model == "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# Reactive overflow fallback: the local endpoint returns a context-overflow
# error at request time (the preemptive estimate undershot), so the request is
# retried against Anthropic.
# ---------------------------------------------------------------------------


from symbology.llm.client import is_context_overflow_error


class _BadRequest(Exception):
    """Stand-in for openai.BadRequestError: exposes status_code + message."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def test_is_context_overflow_error_matches_local_message():
    assert is_context_overflow_error(
        _BadRequest("Error code: 400 - {'error': 'Context size has been exceeded.'}")
    )


def test_is_context_overflow_error_matches_openai_message():
    assert is_context_overflow_error(
        _BadRequest("This model's maximum context length is 8192 tokens")
    )


def test_is_context_overflow_error_ignores_other_400s():
    assert not is_context_overflow_error(_BadRequest("invalid 'temperature'"))


def test_is_context_overflow_error_ignores_non_400():
    assert not is_context_overflow_error(_BadRequest("server error", status_code=500))
    assert not is_context_overflow_error(ValueError("boom"))


def _stub_resp():
    class _R:
        response = "ok"
        total_duration = 0.1
        input_tokens = 1
        output_tokens = 1

    return _R(), None


def test_generate_with_overflow_reactively_falls_back(monkeypatch):
    """Local request overflows at call time -> retried on Anthropic, and the
    returned config is the Anthropic one (so the caller records it)."""
    # Disable preemptive offload so the request actually reaches the local model.
    monkeypatch.setattr(settings.openai, "overflow_threshold_tokens", 0)
    monkeypatch.setattr(settings.openai, "overflow_model", "claude-sonnet-4-6")
    monkeypatch.setattr(settings.anthropic, "api_key", "sk-test")
    monkeypatch.setattr(
        "symbology.database.model_configs.get_or_create_model_config",
        lambda data: _mc(data["model"]),
    )

    calls = []

    def _fake_generate(model_config, system_prompt, user_prompt):
        calls.append(model_config.model)
        if model_config.model == "google/gemma-4-e4b":
            raise _BadRequest("Error code: 400 - {'error': 'Context size has been exceeded.'}")
        return _stub_resp()

    monkeypatch.setattr("symbology.llm.client.get_generate_response", _fake_generate)

    mc = _mc("google/gemma-4-e4b", max_tokens=2048, temperature=0.2)
    response, warning, used = cl.generate_with_overflow(mc, "sys", "user")

    assert response.response == "ok"
    assert used.model == "claude-sonnet-4-6"
    assert calls == ["google/gemma-4-e4b", "claude-sonnet-4-6"]


def test_generate_with_overflow_reraises_when_no_fallback(monkeypatch):
    """Overflow with no Anthropic key configured -> nothing to fall back to, so
    the original error propagates (the job fails as before, not silently)."""
    monkeypatch.setattr(settings.openai, "overflow_threshold_tokens", 0)
    monkeypatch.setattr(settings.anthropic, "api_key", "")

    def _fake_generate(model_config, system_prompt, user_prompt):
        raise _BadRequest("Error code: 400 - {'error': 'Context size has been exceeded.'}")

    monkeypatch.setattr("symbology.llm.client.get_generate_response", _fake_generate)

    mc = _mc("google/gemma-4-e4b")
    try:
        cl.generate_with_overflow(mc, "sys", "user")
        assert False, "expected the overflow error to propagate"
    except _BadRequest:
        pass


def test_generate_with_overflow_propagates_non_overflow_errors(monkeypatch):
    """A non-overflow error is not a fallback trigger -> propagates unchanged
    without a wasted Anthropic retry."""
    monkeypatch.setattr(settings.openai, "overflow_threshold_tokens", 0)
    monkeypatch.setattr(settings.openai, "overflow_model", "claude-sonnet-4-6")
    monkeypatch.setattr(settings.anthropic, "api_key", "sk-test")

    calls = []

    def _fake_generate(model_config, system_prompt, user_prompt):
        calls.append(model_config.model)
        raise _BadRequest("invalid 'temperature'")

    monkeypatch.setattr("symbology.llm.client.get_generate_response", _fake_generate)

    mc = _mc("google/gemma-4-e4b")
    try:
        cl.generate_with_overflow(mc, "sys", "user")
        assert False, "expected the bad-request error to propagate"
    except _BadRequest:
        pass
    assert calls == ["google/gemma-4-e4b"]  # no retry
