"""Tests for pipeline orchestration helpers."""
import json
from unittest.mock import MagicMock, patch

import pytest

from symbology.worker.pipeline import (
    FORM_DOCUMENT_TYPES,
    PIPELINE_MODEL_CONFIGS,
    PIPELINE_PROMPTS,
    ensure_model_config,
    ensure_prompt,
)


class TestEnsureModelConfig:
    def test_creates_with_defaults(self):
        mock_mc = MagicMock()
        mock_mc.get_short_hash.return_value = "abc123"

        with patch("symbology.worker.pipeline.get_or_create_model_config", return_value=mock_mc) as mock_get_or_create:
            result = ensure_model_config("qwen3:4b")

        assert result is mock_mc
        call_data = mock_get_or_create.call_args[0][0]
        assert call_data["model"] == "qwen3:4b"
        options = json.loads(call_data["options_json"])
        assert options["num_ctx"] == 4096  # default

    def test_overrides_num_ctx(self):
        mock_mc = MagicMock()
        mock_mc.get_short_hash.return_value = "abc123"

        with patch("symbology.worker.pipeline.get_or_create_model_config", return_value=mock_mc) as mock_get_or_create:
            result = ensure_model_config("qwen3:4b", num_ctx=28567)

        call_data = mock_get_or_create.call_args[0][0]
        options = json.loads(call_data["options_json"])
        assert options["num_ctx"] == 28567

    def test_overrides_multiple_options(self):
        mock_mc = MagicMock()
        mock_mc.get_short_hash.return_value = "abc123"

        with patch("symbology.worker.pipeline.get_or_create_model_config", return_value=mock_mc) as mock_get_or_create:
            result = ensure_model_config("qwen3:14b", num_ctx=8000, temperature=0.5)

        call_data = mock_get_or_create.call_args[0][0]
        options = json.loads(call_data["options_json"])
        assert options["num_ctx"] == 8000
        assert options["temperature"] == 0.5

    def test_none_overrides_ignored(self):
        mock_mc = MagicMock()
        mock_mc.get_short_hash.return_value = "abc123"

        with patch("symbology.worker.pipeline.get_or_create_model_config", return_value=mock_mc) as mock_get_or_create:
            result = ensure_model_config("qwen3:4b", num_ctx=None, temperature=None)

        call_data = mock_get_or_create.call_args[0][0]
        options = json.loads(call_data["options_json"])
        # Should keep defaults since overrides are None
        assert options["num_ctx"] == 4096
        assert options["temperature"] == 0.8


class TestEnsurePrompt:
    def test_loads_prompt_from_file(self, tmp_path):
        prompt_dir = tmp_path / "risk_factors"
        prompt_dir.mkdir()
        (prompt_dir / "prompt.md").write_text("Analyze the risk factors.")

        mock_prompt = MagicMock()
        mock_prompt.get_short_hash.return_value = "def456"

        with patch("symbology.worker.pipeline.create_prompt", return_value=(mock_prompt, True)) as mock_create:
            result = ensure_prompt("risk_factors", prompts_dir=tmp_path)

        assert result is mock_prompt
        call_data = mock_create.call_args[0][0]
        assert call_data["name"] == "risk_factors"
        assert call_data["content"] == "Analyze the risk factors."
        assert call_data["role"] == "system"

    def test_appends_examples(self, tmp_path):
        prompt_dir = tmp_path / "general-summary"
        prompt_dir.mkdir()
        (prompt_dir / "prompt.md").write_text("Summarize the content.")

        examples_dir = prompt_dir / "examples"
        examples_dir.mkdir()
        (examples_dir / "01_example.md").write_text("Example A")
        (examples_dir / "02_example.md").write_text("Example B")

        mock_prompt = MagicMock()
        mock_prompt.get_short_hash.return_value = "ghi789"

        with patch("symbology.worker.pipeline.create_prompt", return_value=(mock_prompt, False)) as mock_create:
            result = ensure_prompt("general-summary", prompts_dir=tmp_path)

        call_data = mock_create.call_args[0][0]
        assert "Summarize the content." in call_data["content"]
        assert "Example A" in call_data["content"]
        assert "Example B" in call_data["content"]

    def test_raises_on_missing_prompt_file(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Prompt file not found"):
            ensure_prompt("nonexistent", prompts_dir=tmp_path)

    def test_custom_role(self, tmp_path):
        prompt_dir = tmp_path / "test_prompt"
        prompt_dir.mkdir()
        (prompt_dir / "prompt.md").write_text("Test content.")

        mock_prompt = MagicMock()
        mock_prompt.get_short_hash.return_value = "xyz000"

        with patch("symbology.worker.pipeline.create_prompt", return_value=(mock_prompt, True)) as mock_create:
            ensure_prompt("test_prompt", prompts_dir=tmp_path, role="user")

        call_data = mock_create.call_args[0][0]
        assert call_data["role"] == "user"

    def test_no_examples_dir(self, tmp_path):
        """Prompt without examples directory works fine."""
        prompt_dir = tmp_path / "simple"
        prompt_dir.mkdir()
        (prompt_dir / "prompt.md").write_text("Just a prompt.")

        mock_prompt = MagicMock()
        mock_prompt.get_short_hash.return_value = "aaa111"

        with patch("symbology.worker.pipeline.create_prompt", return_value=(mock_prompt, True)) as mock_create:
            ensure_prompt("simple", prompts_dir=tmp_path)

        call_data = mock_create.call_args[0][0]
        assert call_data["content"] == "Just a prompt."


class TestPipelineConstants:
    def test_model_configs_have_required_keys(self):
        for stage, config in PIPELINE_MODEL_CONFIGS.items():
            assert "model" in config, f"{stage} missing 'model'"
            assert "num_ctx" in config, f"{stage} missing 'num_ctx'"

    def test_form_document_types_coverage(self):
        assert "10-K" in FORM_DOCUMENT_TYPES
        assert "10-Q" in FORM_DOCUMENT_TYPES
        assert len(FORM_DOCUMENT_TYPES["10-K"]) == 4
        assert len(FORM_DOCUMENT_TYPES["10-Q"]) == 4

    def test_pipeline_prompts_stages(self):
        assert "aggregate_summary" in PIPELINE_PROMPTS
        assert "frontpage_summary" in PIPELINE_PROMPTS
