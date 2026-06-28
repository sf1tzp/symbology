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
