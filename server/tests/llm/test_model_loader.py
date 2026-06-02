"""Tests for dynamic context-window sizing (LM Studio model instances).

Covers the pure sizing helpers and ``ensure_model_loaded``: disabled-by-default
no-op, reuse of an adequately-sized existing instance, loading a new instance
when none is big enough, the model's own context ceiling, and best-effort
failure handling. The management HTTP calls are monkeypatched — no network.
"""
import symbology.llm.model_loader as ml
from symbology.utils.config import settings


def test_estimate_tokens_scales_with_length():
    assert ml.estimate_tokens("") == 0
    assert ml.estimate_tokens(None) == 0
    assert ml.estimate_tokens("x" * 70) == int(70 / settings.openai.chars_per_token) + 1


def test_required_context_length_buckets_and_clamps(monkeypatch):
    cfg = settings.openai
    monkeypatch.setattr(cfg, "context_min", 4096)
    monkeypatch.setattr(cfg, "context_max", 128000)
    monkeypatch.setattr(cfg, "context_bucket", 4096)
    monkeypatch.setattr(cfg, "context_safety_margin", 1.0)

    assert ml.required_context_length(100, 100) == 4096        # clamps up to floor
    assert ml.required_context_length(5000, 1000) == 8192      # 6000 -> 8192 bucket
    assert ml.required_context_length(1_000_000, 4096) == 128000  # clamps to ceiling


def test_ensure_model_loaded_disabled_is_noop(monkeypatch):
    monkeypatch.setattr(settings.openai, "manage_context", False)
    monkeypatch.setattr(ml, "_list_instances", lambda m: (_ for _ in ()).throw(AssertionError("called")))
    assert ml.ensure_model_loaded("gpt-oss-20b", "hello", 256) is None


def _enable(monkeypatch):
    cfg = settings.openai
    monkeypatch.setattr(cfg, "manage_context", True)
    monkeypatch.setattr(cfg, "context_min", 4096)
    monkeypatch.setattr(cfg, "context_max", 128000)
    monkeypatch.setattr(cfg, "context_bucket", 4096)
    monkeypatch.setattr(cfg, "context_safety_margin", 1.0)


def test_reuses_largest_adequate_instance(monkeypatch):
    _enable(monkeypatch)
    instances = [
        {"id": "m", "context_length": 4096},
        {"id": "m:2", "context_length": 128000},
    ]
    monkeypatch.setattr(ml, "_list_instances", lambda model: (instances, 131072))
    loads = []
    monkeypatch.setattr(ml, "_load_instance", lambda *a: loads.append(a))

    # Small request -> the 128000 instance already covers it, no new load.
    assert ml.ensure_model_loaded("m", "tiny", 256) == "m:2"
    assert loads == []


def test_loads_new_instance_when_none_big_enough(monkeypatch):
    _enable(monkeypatch)
    instances = [{"id": "m", "context_length": 4096}]
    monkeypatch.setattr(ml, "_list_instances", lambda model: (instances, 131072))
    monkeypatch.setattr(ml, "_load_instance", lambda model, ctx: f"{model}:new@{ctx}")

    # ~20k-token prompt + 1024 out -> needs a 24576 window the 4096 instance lacks.
    big = "x" * int(20_000 * settings.openai.chars_per_token)
    assert ml.ensure_model_loaded("m", big, 1024) == "m:new@24576"


def test_target_capped_at_model_max(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(ml, "_list_instances", lambda model: ([], 8192))
    captured = []
    monkeypatch.setattr(ml, "_load_instance", lambda model, ctx: captured.append(ctx) or "m:1")

    # Request would want >8192 but the model maxes at 8192 -> load is capped.
    big = "x" * int(50_000 * settings.openai.chars_per_token)
    assert ml.ensure_model_loaded("m", big, 4096) == "m:1"
    assert captured == [8192]


def test_list_failure_falls_back_to_blind_load(monkeypatch):
    _enable(monkeypatch)

    def _boom(model):
        raise ConnectionError("mgmt API down")

    monkeypatch.setattr(ml, "_list_instances", _boom)
    monkeypatch.setattr(ml, "_load_instance", lambda model, ctx: "m:blind")
    assert ml.ensure_model_loaded("m", "hello", 256) == "m:blind"


def test_load_failure_is_non_fatal(monkeypatch):
    _enable(monkeypatch)
    monkeypatch.setattr(ml, "_list_instances", lambda model: ([], 131072))

    def _boom(model, ctx):
        raise ConnectionError("load failed")

    monkeypatch.setattr(ml, "_load_instance", _boom)
    assert ml.ensure_model_loaded("m", "hello", 256) is None
