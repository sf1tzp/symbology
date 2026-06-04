"""Tests for the explicit-pair / company diff pipeline wrappers."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from uuid_extensions import uuid7


def _filing(period_year):
    cid = uuid7()
    return SimpleNamespace(
        id=uuid7(),
        company_id=cid,
        company=SimpleNamespace(id=cid),
        period_of_report=SimpleNamespace(year=period_year),
    )


class TestFilingDiffPipeline:
    def test_loops_document_types_and_drops_none(self):
        from symbology.worker import diff_pipeline

        left, right = _filing(2023), _filing(2024)
        cfg = SimpleNamespace(form_document_types={"10-K": ["risk_factors", "management_discussion"]})
        seen = []

        def fake_one(company, document_type, lf, rf, form):
            seen.append(document_type.value)
            # Only the first doc type yields a diff set; the second is absent.
            return SimpleNamespace(document_type=document_type) if document_type.value == "risk_factors" else None

        with patch("symbology.worker.config_loader.load_pipeline_config", return_value=cfg), \
             patch.object(diff_pipeline, "_diff_one_doctype", side_effect=fake_one):
            out = diff_pipeline.filing_diff_pipeline(left, right, "10-K")

        assert seen == ["risk_factors", "management_discussion"]
        assert len(out) == 1

    def test_passes_pair_in_given_order(self):
        from symbology.worker import diff_pipeline

        left, right = _filing(2023), _filing(2024)
        cfg = SimpleNamespace(form_document_types={"10-K": ["risk_factors"]})
        captured = {}

        def fake_one(company, document_type, lf, rf, form):
            captured["lf"], captured["rf"] = lf, rf
            return None

        with patch("symbology.worker.config_loader.load_pipeline_config", return_value=cfg), \
             patch.object(diff_pipeline, "_diff_one_doctype", side_effect=fake_one):
            diff_pipeline.filing_diff_pipeline(left, right, "10-K")

        assert captured["lf"] is left and captured["rf"] is right


class TestCompanyDiffPipeline:
    def test_insufficient_filings_returns_empty(self):
        from symbology.worker import diff_pipeline

        company = SimpleNamespace(id=uuid7())
        session = SimpleNamespace()
        q = SimpleNamespace()
        q.filter = lambda *a, **k: q
        q.order_by = lambda *a, **k: q
        q.limit = lambda *a, **k: q
        q.all = lambda: [_filing(2024)]  # only one
        session.query = lambda *a, **k: q

        with patch("symbology.worker.diff_pipeline.get_db_session", return_value=session):
            out = diff_pipeline.company_diff_pipeline(company, form="10-K")
        assert out == []

    def test_delegates_latest_two_in_order(self):
        from symbology.worker import diff_pipeline

        company = SimpleNamespace(id=uuid7())
        newer, older = _filing(2024), _filing(2023)
        q = SimpleNamespace()
        q.filter = lambda *a, **k: q
        q.order_by = lambda *a, **k: q
        q.limit = lambda *a, **k: q
        q.all = lambda: [newer, older]  # ordered desc → newest first
        session = SimpleNamespace(query=lambda *a, **k: q)
        captured = {}

        def fake_pipeline(left, right, form, prompts_dir, generate_summaries, max_summaries):
            captured["left"], captured["right"] = left, right
            return ["ds"]

        with patch("symbology.worker.diff_pipeline.get_db_session", return_value=session), \
             patch("symbology.worker.diff_pipeline.filing_diff_pipeline", side_effect=fake_pipeline):
            out = diff_pipeline.company_diff_pipeline(company, form="10-K")

        assert captured["left"] is older and captured["right"] is newer
        assert out == ["ds"]


def _sd(kind, added=0, removed=0, ldelta=0):
    return SimpleNamespace(
        id=uuid7(), change_kind=kind, tokens_added=added, tokens_removed=removed,
        length_delta=ldelta, left_chunk_id=None, right_chunk_id=uuid7(),
        heading="h", section_path="1A.1", summary_content_id=None,
    )


class TestNoiseLabel:
    @pytest.mark.parametrize(
        "label, expected",
        [
            ("__________", True),   # underline rule mistaken for a heading
            ("____ ____", True),    # spaced separators
            ("...", True),          # punctuation-only
            ("— — —", True),        # em-dash rule
            ("Risk Factors", False),
            ("Item 1A.", False),
            ("____2024", False),    # has an alphanumeric → real-ish label
            (None, False),          # absent label is not noise (falls back to path)
            ("", False),
            ("   ", False),         # blank is absent, not garbage
        ],
    )
    def test_is_noise_label(self, label, expected):
        from symbology.database.chunk_topics import is_noise_label
        assert is_noise_label(label) is expected


class TestTopicSummaryCap:
    def test_significance_kind_breaks_ties_at_equal_volume(self):
        # Additive heuristic: at equal edit volume, structural kinds rank higher.
        from symbology.worker.diff_pipeline import _significance
        from symbology.utils import text_diff
        new = _sd(text_diff.NEW, added=10, removed=10, ldelta=10)
        reworded = _sd(text_diff.REWORDED, added=10, removed=10, ldelta=10)
        unchanged = _sd(text_diff.UNCHANGED, added=10, removed=10, ldelta=10)
        assert _significance(new) > _significance(reworded) > _significance(unchanged)

    def test_summarises_only_top_max_summaries(self):
        from symbology.worker import diff_pipeline
        from symbology.utils import text_diff

        high1 = _sd(text_diff.NEW, added=100, ldelta=100)
        high2 = _sd(text_diff.REMOVED, removed=90, ldelta=-90)
        low1 = _sd(text_diff.REWORDED, added=1, removed=1, ldelta=1)
        low2 = _sd(text_diff.REWORDED, added=2, removed=2, ldelta=2)
        ds = SimpleNamespace(
            section_diffs=[low1, high1, low2, high2],
            right_filing_id=uuid7(),
            document_type=SimpleNamespace(value="risk_factors"),
        )
        company = SimpleNamespace(id=uuid7())

        session = MagicMock()
        session.get.return_value = SimpleNamespace(content="chunk text")
        resp = SimpleNamespace(response="summary", total_duration=1, input_tokens=1, output_tokens=1)
        gen = MagicMock(return_value=(resp, None))
        cfg = SimpleNamespace(prompt_path=lambda k: "p")

        with patch("symbology.worker.diff_pipeline.get_db_session", return_value=session), \
             patch("symbology.worker.config_loader.load_pipeline_config", return_value=cfg), \
             patch("symbology.worker.config_loader.ensure_stage_model_config", return_value=SimpleNamespace(id=uuid7())), \
             patch("symbology.worker.config_loader.resolve_generation_model_config", return_value=SimpleNamespace(id=uuid7())), \
             patch("symbology.worker.pipeline.ensure_prompt", return_value=SimpleNamespace(content="sys", id=uuid7())), \
             patch("symbology.llm.client.get_generate_response", gen), \
             patch("symbology.database.generated_content.create_generated_content",
                   return_value=(SimpleNamespace(id=uuid7()), True)):
            diff_pipeline._generate_topic_summaries(company, [ds], "10-K", None, max_summaries=2)

        # Only the two most significant topics hit the LLM and got summaries.
        assert gen.call_count == 2
        assert high1.summary_content_id is not None
        assert high2.summary_content_id is not None
        assert low1.summary_content_id is None
        assert low2.summary_content_id is None
