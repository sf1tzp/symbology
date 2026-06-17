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


def _pf(form, period):
    """A filing stub with a comparable (date) period for pairing tests."""
    return SimpleNamespace(id=uuid7(), form=form, period_of_report=period, filing_date=period)


class TestQuarterlyDiffPair:
    """A 10-Q page pairs the latest quarter with the immediately preceding 10-K /
    10-Q, never straddling the annual to a quarter of the prior cycle."""

    def _run(self, filings):
        from symbology.worker import diff_pipeline

        q = SimpleNamespace()
        q.filter = lambda *a, **k: q
        q.order_by = lambda *a, **k: q
        q.limit = lambda *a, **k: q
        q.all = lambda: filings
        session = SimpleNamespace(query=lambda *a, **k: q)
        captured = {}

        def fake_pipeline(left, right, form, prompts_dir, generate_summaries, max_summaries):
            captured["left"], captured["right"], captured["form"] = left, right, form
            return ["ds"]

        with patch("symbology.worker.diff_pipeline.get_db_session", return_value=session), \
             patch("symbology.worker.diff_pipeline.filing_diff_pipeline", side_effect=fake_pipeline):
            out = diff_pipeline.company_diff_pipeline(SimpleNamespace(id=uuid7()), form="10-Q")
        return captured, out

    def test_first_quarter_pairs_with_anchor_10k(self):
        from datetime import date

        # Newest-first, as the desc-ordered query returns. The latest 10-Q (Q1-26)
        # follows the FY25 10-K; it must pair with that annual, not the prior Q3-25.
        filings = [
            _pf("10-Q", date(2026, 3, 31)),
            _pf("10-K", date(2025, 12, 31)),
            _pf("10-Q", date(2025, 9, 30)),
        ]
        captured, out = self._run(filings)
        assert captured["right"] is filings[0]
        assert captured["left"] is filings[1]  # the anchor 10-K
        assert captured["form"] == "10-Q"
        assert out == ["ds"]

    def test_mid_cycle_pairs_with_prior_quarter(self):
        from datetime import date

        filings = [
            _pf("10-Q", date(2025, 6, 30)),
            _pf("10-Q", date(2025, 3, 31)),
            _pf("10-K", date(2024, 12, 31)),
        ]
        captured, _ = self._run(filings)
        assert captured["right"] is filings[0]
        assert captured["left"] is filings[1]  # prior quarter of the same cycle

    def test_no_quarter_returns_empty(self):
        from datetime import date

        _, out = self._run([_pf("10-K", date(2025, 12, 31))])
        assert out == []


def _sd(kind, added=0, removed=0, ldelta=0, ops=None):
    return SimpleNamespace(
        id=uuid7(), change_kind=kind, tokens_added=added, tokens_removed=removed,
        length_delta=ldelta, topic_id=uuid7(), left_chunk_id=None, right_chunk_id=uuid7(),
        heading="h", section_path="1A.1", ops=ops or [], summary_content_id=None,
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
            # Run-on table headers: column labels concatenated without spaces.
            ("CareBenefitsHealthServicesPharmacy &ConsumerWellnessCorporate/OtherConsolidatedTotals", True),
            ("Health Care Benefits Segment", False),  # spaced phrase stays readable
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

    def test_is_displayed_change_matches_the_ui_gate(self):
        from symbology.worker.diff_pipeline import is_displayed_change
        from symbology.utils import text_diff

        assert is_displayed_change(_sd(text_diff.ESCALATED)) is True
        assert is_displayed_change(_sd(text_diff.REWORDED)) is True
        # Never shown in the UI → not summarised.
        assert is_displayed_change(_sd(text_diff.NEW)) is False
        assert is_displayed_change(_sd(text_diff.REMOVED)) is False
        assert is_displayed_change(_sd(text_diff.UNCHANGED)) is False
        # A figures-only "reworded" edit is hidden on-page → excluded too.
        noise = _sd(text_diff.REWORDED, ops=[{"op": "delete", "text": "$112,718"},
                                             {"op": "insert", "text": "$91,650"}])
        assert is_displayed_change(noise) is False

    def test_summarises_only_top_displayed_topics(self):
        from symbology.worker import diff_pipeline
        from symbology.utils import text_diff

        esc = _sd(text_diff.ESCALATED, added=100, ldelta=100)   # displayed, highest
        rew_mid = _sd(text_diff.REWORDED, added=50, removed=50)  # displayed, mid
        rew_low = _sd(text_diff.REWORDED, added=1, removed=1)    # displayed, lowest
        new = _sd(text_diff.NEW, added=200, ldelta=200)          # excluded (not shown)
        noise = _sd(text_diff.REWORDED,                          # excluded (figures only)
                    ops=[{"op": "delete", "text": "$112,718"}, {"op": "insert", "text": "$91,650"}])
        ds = SimpleNamespace(
            id=uuid7(),
            section_diffs=[rew_low, new, esc, noise, rew_mid],
            left_filing_id=uuid7(),
            right_filing_id=uuid7(),
            document_type=SimpleNamespace(value="risk_factors"),
        )
        company = SimpleNamespace(id=uuid7())

        resp = SimpleNamespace(response="summary", total_duration=1, input_tokens=1, output_tokens=1)
        gen = MagicMock(return_value=(resp, None))
        cfg = SimpleNamespace(prompt_path=lambda k: "p")

        with patch("symbology.worker.diff_pipeline.get_db_session", return_value=MagicMock()), \
             patch("symbology.worker.diff_pipeline._topic_text", return_value="full topic text"), \
             patch("symbology.worker.config_loader.load_pipeline_config", return_value=cfg), \
             patch("symbology.worker.config_loader.ensure_stage_model_config", return_value=SimpleNamespace(id=uuid7())), \
             patch("symbology.worker.config_loader.resolve_generation_model_config", return_value=SimpleNamespace(id=uuid7())), \
             patch("symbology.worker.pipeline.ensure_prompt", return_value=SimpleNamespace(content="sys", id=uuid7())), \
             patch("symbology.llm.client.get_generate_response", gen), \
             patch("symbology.database.generated_content.create_generated_content",
                   return_value=(SimpleNamespace(id=uuid7()), True)):
            diff_pipeline._generate_topic_summaries(company, [ds], "10-K", None, max_summaries=2)

        # Only the two most significant *displayed* topics hit the LLM; new/removed
        # and figures-only rows are never summarised regardless of significance.
        assert gen.call_count == 2
        assert esc.summary_content_id is not None
        assert rew_mid.summary_content_id is not None
        assert rew_low.summary_content_id is None   # displayed but below the cap
        assert new.summary_content_id is None        # excluded kind
        assert noise.summary_content_id is None      # numeric noise

    def test_skips_empty_summary_so_it_can_retry(self):
        # A reasoning model that runs out of tokens mid-think returns empty content;
        # we must not store a blank row or mark the topic summarised.
        from symbology.worker import diff_pipeline
        from symbology.utils import text_diff

        sd = _sd(text_diff.ESCALATED, added=10, ldelta=10)
        ds = SimpleNamespace(
            id=uuid7(), section_diffs=[sd], left_filing_id=uuid7(),
            right_filing_id=uuid7(), document_type=SimpleNamespace(value="risk_factors"),
        )
        company = SimpleNamespace(id=uuid7())
        resp = SimpleNamespace(response="", total_duration=1, input_tokens=1, output_tokens=512)
        created = MagicMock()

        with patch("symbology.worker.diff_pipeline.get_db_session", return_value=MagicMock()), \
             patch("symbology.worker.diff_pipeline._topic_text", return_value="full topic text"), \
             patch("symbology.worker.config_loader.load_pipeline_config",
                   return_value=SimpleNamespace(prompt_path=lambda k: "p")), \
             patch("symbology.worker.config_loader.ensure_stage_model_config", return_value=SimpleNamespace(id=uuid7())), \
             patch("symbology.worker.config_loader.resolve_generation_model_config", return_value=SimpleNamespace(id=uuid7())), \
             patch("symbology.worker.pipeline.ensure_prompt", return_value=SimpleNamespace(content="sys", id=uuid7())), \
             patch("symbology.llm.client.get_generate_response", return_value=(resp, None)), \
             patch("symbology.database.generated_content.create_generated_content", new=created):
            n = diff_pipeline.summarize_diff_set(ds, company, "10-K", max_summaries=6)

        assert n == 0
        assert sd.summary_content_id is None      # not marked → a later run retries it
        created.assert_not_called()                # no blank row stored

    def test_force_resummarises_already_summarised_topics(self):
        # `jobs retry --force` path: re-summarise a displayed topic that already has a
        # summary (e.g. to backfill blanks), replacing summary_content_id.
        from symbology.worker import diff_pipeline
        from symbology.utils import text_diff

        sd = _sd(text_diff.ESCALATED, added=10, ldelta=10)
        sd.summary_content_id = uuid7()           # already "summarised"
        ds = SimpleNamespace(
            id=uuid7(), section_diffs=[sd], left_filing_id=uuid7(),
            right_filing_id=uuid7(), document_type=SimpleNamespace(value="risk_factors"),
        )
        company = SimpleNamespace(id=uuid7())
        resp = SimpleNamespace(response="fresh summary", total_duration=1, input_tokens=1, output_tokens=10)
        new_id = uuid7()

        with patch("symbology.worker.diff_pipeline.get_db_session", return_value=MagicMock()), \
             patch("symbology.worker.diff_pipeline._topic_text", return_value="full topic text"), \
             patch("symbology.worker.config_loader.load_pipeline_config",
                   return_value=SimpleNamespace(prompt_path=lambda k: "p")), \
             patch("symbology.worker.config_loader.ensure_stage_model_config", return_value=SimpleNamespace(id=uuid7())), \
             patch("symbology.worker.config_loader.resolve_generation_model_config", return_value=SimpleNamespace(id=uuid7())), \
             patch("symbology.worker.pipeline.ensure_prompt", return_value=SimpleNamespace(content="sys", id=uuid7())), \
             patch("symbology.llm.client.get_generate_response", return_value=(resp, None)), \
             patch("symbology.database.generated_content.create_generated_content",
                   return_value=(SimpleNamespace(id=new_id), True)):
            # Without force the topic is skipped (already summarised); with force it's redone.
            n_skip = diff_pipeline.summarize_diff_set(ds, company, "10-K", max_summaries=6)
            n_force = diff_pipeline.summarize_diff_set(ds, company, "10-K", max_summaries=6, force=True)

        assert n_skip == 0
        assert n_force == 1
        assert sd.summary_content_id == new_id    # replaced with the fresh summary
