"""Tests for pipeline orchestration helpers."""
import json
from unittest.mock import MagicMock, patch

import pytest
from uuid_extensions import uuid7

from symbology.database.documents import DocumentType
from symbology.worker.pipeline import (
    FORM_DOCUMENT_TYPES,
    PIPELINE_MODEL_CONFIGS,
    PIPELINE_PROMPTS,
    ensure_model_config,
    ensure_prompt,
    generate_aggregate_summary,
    generate_frontpage_summary,
    generate_single_summaries,
)


class TestEnsureModelConfig:
    def test_creates_with_defaults(self):
        mock_mc = MagicMock()
        mock_mc.get_short_hash.return_value = "abc123"

        with patch("symbology.worker.pipeline.get_or_create_model_config", return_value=mock_mc) as mock_get_or_create:
            result = ensure_model_config("claude-haiku-4-5-20251001")

        assert result is mock_mc
        call_data = mock_get_or_create.call_args[0][0]
        assert call_data["model"] == "claude-haiku-4-5-20251001"
        options = json.loads(call_data["options_json"])
        assert options["max_tokens"] == 4096  # default

    def test_overrides_max_tokens(self):
        mock_mc = MagicMock()
        mock_mc.get_short_hash.return_value = "abc123"

        with patch("symbology.worker.pipeline.get_or_create_model_config", return_value=mock_mc) as mock_get_or_create:
            result = ensure_model_config("claude-haiku-4-5-20251001", max_tokens=8192)

        call_data = mock_get_or_create.call_args[0][0]
        options = json.loads(call_data["options_json"])
        assert options["max_tokens"] == 8192

    def test_overrides_multiple_options(self):
        mock_mc = MagicMock()
        mock_mc.get_short_hash.return_value = "abc123"

        with patch("symbology.worker.pipeline.get_or_create_model_config", return_value=mock_mc) as mock_get_or_create:
            result = ensure_model_config("claude-sonnet-4-5-20250929", max_tokens=8192, temperature=0.5)

        call_data = mock_get_or_create.call_args[0][0]
        options = json.loads(call_data["options_json"])
        assert options["max_tokens"] == 8192
        assert options["temperature"] == 0.5

    def test_none_overrides_ignored(self):
        mock_mc = MagicMock()
        mock_mc.get_short_hash.return_value = "abc123"

        with patch("symbology.worker.pipeline.get_or_create_model_config", return_value=mock_mc) as mock_get_or_create:
            result = ensure_model_config("claude-haiku-4-5-20251001", max_tokens=None, temperature=None)

        call_data = mock_get_or_create.call_args[0][0]
        options = json.loads(call_data["options_json"])
        # Should keep defaults since overrides are None
        assert options["max_tokens"] == 4096
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
            assert "model_name" in config, f"{stage} missing 'model_name'"
            assert "max_tokens" in config, f"{stage} missing 'max_tokens'"

    def test_form_document_types_coverage(self):
        assert "10-K" in FORM_DOCUMENT_TYPES
        assert "10-Q" in FORM_DOCUMENT_TYPES
        assert len(FORM_DOCUMENT_TYPES["10-K"]) == 4
        assert len(FORM_DOCUMENT_TYPES["10-Q"]) == 4

    def test_pipeline_prompts_stages(self):
        assert "aggregate_summary" in PIPELINE_PROMPTS
        assert "frontpage_summary" in PIPELINE_PROMPTS


# ---------------------------------------------------------------------------
# Tests for composable pipeline functions
# ---------------------------------------------------------------------------


def _make_mock_filing(doc_type=DocumentType.RISK_FACTORS, content_hash="doc_hash"):
    """Create a mock filing with a single document."""
    mock_doc = MagicMock()
    mock_doc.document_type = doc_type
    mock_doc.content_hash = content_hash
    mock_doc.id = uuid7()

    mock_filing = MagicMock()
    mock_filing.id = uuid7()
    mock_filing.documents = [mock_doc]
    return mock_filing, mock_doc


def _make_mock_prompt():
    mock_prompt = MagicMock()
    mock_prompt.id = uuid7()
    mock_prompt.content_hash = "prompt_hash_001"
    return mock_prompt


def _make_mock_mc():
    mock_mc = MagicMock()
    mock_mc.id = uuid7()
    return mock_mc


class TestGenerateSingleSummaries:
    @patch("symbology.worker.handlers.handle_content_generation")
    @patch("symbology.database.generated_content.find_existing_content_for_document", return_value=None)
    def test_generates_for_each_filing(self, mock_find, mock_gen):
        """Generates single summaries for each filing with matching documents."""
        mock_gen.return_value = {"content_hash": "hash_001", "content_id": str(uuid7()), "was_created": True}
        filing, doc = _make_mock_filing()

        hashes, new, reused, failed = generate_single_summaries(
            str(uuid7()), "AAPL", "10-K", "risk_factors",
            [filing], _make_mock_prompt(), _make_mock_mc(),
        )

        assert hashes == ["hash_001"]
        assert new == 1
        assert reused == 0
        assert failed == 0
        # Verify structured fields
        call_params = mock_gen.call_args[0][0]
        assert call_params["document_type"] == "risk_factors"
        assert call_params["form_type"] == "10-K"
        assert call_params["content_stage"] == "single_summary"

    @patch("symbology.worker.handlers.handle_content_generation")
    @patch("symbology.database.generated_content.find_existing_content_for_document")
    def test_reuses_existing_content(self, mock_find, mock_gen):
        """Skips LLM call when content already exists."""
        existing = MagicMock()
        existing.content_hash = "existing_hash"
        mock_find.return_value = existing

        filing, doc = _make_mock_filing()

        hashes, new, reused, failed = generate_single_summaries(
            str(uuid7()), "AAPL", "10-K", "risk_factors",
            [filing], _make_mock_prompt(), _make_mock_mc(),
        )

        assert hashes == ["existing_hash"]
        assert new == 0
        assert reused == 1
        assert failed == 0
        mock_gen.assert_not_called()

    @patch("symbology.worker.handlers.handle_content_generation")
    @patch("symbology.database.generated_content.find_existing_content_for_document")
    def test_force_bypasses_dedup(self, mock_find, mock_gen):
        """Force=True skips dedup check."""
        existing = MagicMock()
        existing.content_hash = "existing_hash"
        mock_find.return_value = existing

        mock_gen.return_value = {"content_hash": "new_hash", "content_id": str(uuid7()), "was_created": True}
        filing, doc = _make_mock_filing()

        hashes, new, reused, failed = generate_single_summaries(
            str(uuid7()), "AAPL", "10-K", "risk_factors",
            [filing], _make_mock_prompt(), _make_mock_mc(),
            force=True,
        )

        assert hashes == ["new_hash"]
        assert new == 1
        assert reused == 0
        mock_find.assert_not_called()

    def test_no_matching_documents(self):
        """Returns empty when no documents match the doc type."""
        filing, _ = _make_mock_filing(doc_type=DocumentType.DESCRIPTION)

        hashes, new, reused, failed = generate_single_summaries(
            str(uuid7()), "AAPL", "10-K", "risk_factors",
            [filing], _make_mock_prompt(), _make_mock_mc(),
        )

        assert hashes == []
        assert new == 0
        assert reused == 0
        assert failed == 0

    @patch("symbology.worker.handlers.handle_content_generation")
    @patch("symbology.database.generated_content.find_existing_content_for_document", return_value=None)
    def test_partial_failure(self, mock_find, mock_gen):
        """Counts failures when content generation raises."""
        mock_gen.side_effect = RuntimeError("LLM error")
        filing, _ = _make_mock_filing()

        hashes, new, reused, failed = generate_single_summaries(
            str(uuid7()), "AAPL", "10-K", "risk_factors",
            [filing], _make_mock_prompt(), _make_mock_mc(),
        )

        assert hashes == []
        assert new == 0
        assert failed == 1


class TestGenerateAggregateSummary:
    @patch("symbology.worker.handlers.handle_content_generation")
    def test_generates_aggregate(self, mock_gen):
        """Generates aggregate summary from single hashes."""
        mock_gen.return_value = {"content_hash": "agg_hash", "content_id": str(uuid7()), "was_created": True}

        hash_result, success = generate_aggregate_summary(
            str(uuid7()), "AAPL", "10-K", "risk_factors",
            ["hash_001", "hash_002"], _make_mock_prompt(), _make_mock_mc(),
        )

        assert hash_result == "agg_hash"
        assert success is True
        call_params = mock_gen.call_args[0][0]
        assert call_params["content_stage"] == "aggregate_summary"
        assert call_params["document_type"] == "risk_factors"
        assert call_params["form_type"] == "10-K"
        assert call_params["source_content_hashes"] == ["hash_001", "hash_002"]

    @patch("symbology.worker.handlers.handle_content_generation")
    def test_failure_returns_none(self, mock_gen):
        """Returns (None, False) on failure."""
        mock_gen.side_effect = RuntimeError("LLM error")

        hash_result, success = generate_aggregate_summary(
            str(uuid7()), "AAPL", "10-K", "risk_factors",
            ["hash_001"], _make_mock_prompt(), _make_mock_mc(),
        )

        assert hash_result is None
        assert success is False

    def test_empty_hashes(self):
        """Returns (None, False) with empty hashes."""
        hash_result, success = generate_aggregate_summary(
            str(uuid7()), "AAPL", "10-K", "risk_factors",
            [], _make_mock_prompt(), _make_mock_mc(),
        )

        assert hash_result is None
        assert success is False


class TestGenerateFrontpageSummary:
    @patch("symbology.worker.handlers.handle_content_generation")
    def test_generates_frontpage(self, mock_gen):
        """Generates frontpage summary from aggregate hash."""
        mock_gen.return_value = {"content_hash": "fp_hash", "content_id": str(uuid7()), "was_created": True}

        hash_result, success = generate_frontpage_summary(
            str(uuid7()), "AAPL", "10-K", "risk_factors",
            "agg_hash", _make_mock_prompt(), _make_mock_mc(),
        )

        assert hash_result == "fp_hash"
        assert success is True
        call_params = mock_gen.call_args[0][0]
        assert call_params["content_stage"] == "frontpage_summary"
        assert call_params["document_type"] == "risk_factors"
        assert call_params["form_type"] == "10-K"
        assert call_params["source_content_hashes"] == ["agg_hash"]

    @patch("symbology.worker.handlers.handle_content_generation")
    def test_failure_returns_none(self, mock_gen):
        """Returns (None, False) on failure."""
        mock_gen.side_effect = RuntimeError("LLM error")

        hash_result, success = generate_frontpage_summary(
            str(uuid7()), "AAPL", "10-K", "risk_factors",
            "agg_hash", _make_mock_prompt(), _make_mock_mc(),
        )

        assert hash_result is None
        assert success is False
