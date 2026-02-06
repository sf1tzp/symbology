"""Tests for job handlers with mocked DB/LLM/EDGAR dependencies."""
from unittest.mock import MagicMock, patch

from uuid_extensions import uuid7

from symbology.worker.handlers import (
    handle_full_pipeline,
    handle_ingest_pipeline,
    handle_test,
)


class TestHandleTest:
    def test_echoes_params(self):
        result = handle_test({"foo": "bar"})
        assert result == {"echo": {"foo": "bar"}, "status": "ok"}

    def test_empty_params(self):
        result = handle_test({})
        assert result["status"] == "ok"


class TestHandleCompanyIngestion:
    def test_ingests_company(self):
        company_id = uuid7()
        mock_edgar_company = MagicMock()
        mock_edgar_company.name = "Apple Inc."

        mock_edgar_login = MagicMock()
        mock_ingest = MagicMock(return_value=(mock_edgar_company, company_id))
        mock_settings = MagicMock()
        mock_settings.edgar_api.edgar_contact = "test@test.com"

        with patch.dict("sys.modules", {
            "symbology.ingestion.edgar_db": MagicMock(),
            "symbology.ingestion.edgar_db.accessors": MagicMock(edgar_login=mock_edgar_login),
            "symbology.ingestion.ingestion_helpers": MagicMock(ingest_company=mock_ingest),
        }):
            from symbology.worker.handlers import handle_company_ingestion
            with patch("symbology.utils.config.settings", mock_settings):
                result = handle_company_ingestion({"ticker": "AAPL"})
        assert result["ticker"] == "AAPL"
        assert result["company_id"] == str(company_id)
        assert result["name"] == "Apple Inc."

    def test_raises_on_missing_ticker(self):
        """Missing ticker key should raise KeyError."""
        from symbology.worker.handlers import handle_company_ingestion
        try:
            # Patch the lazy imports so they don't fail, but the KeyError on params should hit first
            with patch.dict("sys.modules", {
                "symbology.ingestion.edgar_db": MagicMock(),
                "symbology.ingestion.edgar_db.accessors": MagicMock(),
                "symbology.ingestion.ingestion_helpers": MagicMock(),
            }):
                handle_company_ingestion({})
                assert False, "Should have raised KeyError"
        except KeyError:
            pass


class TestHandleFilingIngestion:
    def test_ingests_filings(self):
        filing_id = uuid7()
        mock_ingest = MagicMock(return_value=[("AAPL", "10-K", "2023-09-30", filing_id)])
        mock_settings = MagicMock()
        mock_settings.edgar_api.edgar_contact = "test@test.com"

        with patch.dict("sys.modules", {
            "symbology.ingestion.edgar_db": MagicMock(),
            "symbology.ingestion.edgar_db.accessors": MagicMock(),
            "symbology.ingestion.ingestion_helpers": MagicMock(ingest_filings=mock_ingest),
        }):
            with patch("symbology.utils.config.settings", mock_settings):
                from symbology.worker.handlers import handle_filing_ingestion
                result = handle_filing_ingestion({
                    "company_id": str(uuid7()),
                    "ticker": "AAPL",
                    "form": "10-K",
                    "count": 1,
                })
        assert result["ticker"] == "AAPL"
        assert result["form"] == "10-K"
        assert len(result["filing_ids"]) == 1
        assert result["filing_ids"][0] == str(filing_id)

    def test_defaults(self):
        mock_ingest = MagicMock(return_value=[])
        mock_settings = MagicMock()
        mock_settings.edgar_api.edgar_contact = "test@test.com"

        with patch.dict("sys.modules", {
            "symbology.ingestion.edgar_db": MagicMock(),
            "symbology.ingestion.edgar_db.accessors": MagicMock(),
            "symbology.ingestion.ingestion_helpers": MagicMock(ingest_filings=mock_ingest),
        }):
            with patch("symbology.utils.config.settings", mock_settings):
                from symbology.worker.handlers import handle_filing_ingestion
                result = handle_filing_ingestion({
                    "company_id": str(uuid7()),
                    "ticker": "MSFT",
                })
        assert result["form"] == "10-K"
        call_args = mock_ingest.call_args
        assert call_args[0][3] == 5  # count default
        assert call_args[0][4] is True  # include_documents default


class TestHandleIngestPipeline:
    @patch("symbology.worker.handlers.handle_filing_ingestion")
    @patch("symbology.worker.handlers.handle_company_ingestion")
    def test_pipeline_calls_both(self, mock_company, mock_filing):
        company_id = str(uuid7())
        filing_id = str(uuid7())
        mock_company.return_value = {"ticker": "AAPL", "company_id": company_id, "name": "Apple"}
        mock_filing.return_value = {"ticker": "AAPL", "form": "10-K", "filing_ids": [filing_id]}

        result = handle_ingest_pipeline({"ticker": "AAPL"})
        assert result["ticker"] == "AAPL"
        assert result["company_id"] == company_id
        assert result["filings"] == [filing_id]

        mock_company.assert_called_once_with({"ticker": "AAPL"})
        filing_params = mock_filing.call_args[0][0]
        assert filing_params["company_id"] == company_id
        assert filing_params["ticker"] == "AAPL"


def _mock_pipeline_run():
    """Return a MagicMock that behaves like a PipelineRun."""
    run = MagicMock()
    run.id = uuid7()
    return run


class TestHandleFullPipeline:
    @patch("symbology.database.pipeline_runs.get_db_session")
    @patch("symbology.worker.handlers.handle_content_generation")
    @patch("symbology.worker.handlers.handle_filing_ingestion")
    @patch("symbology.worker.handlers.handle_company_ingestion")
    def test_full_pipeline_orchestrates_all_stages(
        self, mock_company, mock_filing, mock_content_gen, mock_pr_session, tmp_path
    ):
        """Full pipeline calls company, filing, and content generation handlers."""
        company_id = str(uuid7())
        filing_id = uuid7()
        mock_company.return_value = {
            "ticker": "AAPL",
            "company_id": company_id,
            "name": "Apple",
        }
        mock_filing.return_value = {
            "ticker": "AAPL",
            "form": "10-K",
            "filing_ids": [str(filing_id)],
        }

        # Mock content generation to return a hash each time
        call_count = {"n": 0}

        def fake_content_gen(params):
            call_count["n"] += 1
            return {
                "content_id": str(uuid7()),
                "content_hash": f"hash_{call_count['n']:03d}",
                "was_created": True,
            }

        mock_content_gen.side_effect = fake_content_gen

        # Set up a mock filing with one document
        mock_doc = MagicMock()
        mock_doc.document_type = MagicMock()
        mock_doc.document_type.value = "risk_factors"
        # Make the enum comparison work: DocumentType("risk_factors") == mock_doc.document_type
        from symbology.database.documents import DocumentType

        mock_doc.document_type = DocumentType.RISK_FACTORS
        mock_doc.content_hash = "doc_hash_001"

        mock_filing_obj = MagicMock()
        mock_filing_obj.id = filing_id
        mock_filing_obj.documents = [mock_doc]

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [
            mock_filing_obj
        ]

        # Create prompt files
        for name in ["risk_factors", "aggregate-summary", "general-summary"]:
            d = tmp_path / name
            d.mkdir()
            (d / "prompt.md").write_text(f"Prompt for {name}")

        mock_prompt = MagicMock()
        mock_prompt.content_hash = "prompt_hash_001"
        mock_prompt.get_short_hash.return_value = "prompt_hash_0"

        mock_mc = MagicMock()
        mock_mc.id = uuid7()
        mock_mc.get_short_hash.return_value = "mc_hash_0001"

        with (
            patch(
                "symbology.database.base.get_db_session",
                return_value=mock_session,
            ),
            patch(
                "symbology.worker.pipeline.ensure_model_config",
                return_value=mock_mc,
            ),
            patch(
                "symbology.worker.pipeline.ensure_prompt",
                return_value=mock_prompt,
            ),
        ):
            result = handle_full_pipeline({
                "ticker": "AAPL",
                "forms": ["10-K"],
                "counts": {"10-K": 1},
                "document_types": {"10-K": ["risk_factors"]},
                "prompts_dir": str(tmp_path),
            })

        assert result["ticker"] == "AAPL"
        assert result["company_id"] == company_id
        assert result["forms"] == ["10-K"]
        # 1 single + 1 aggregate + 1 frontpage = 3
        assert result["content_generated"] == 3
        assert mock_content_gen.call_count == 3
        assert result["pipeline_run_id"] is not None

        # Verify the three stages were called with correct descriptions
        descriptions = [
            call[0][0]["description"] for call in mock_content_gen.call_args_list
        ]
        assert descriptions[0] == "risk_factors_single_summary"
        assert descriptions[1] == "risk_factors_aggregate_summary"
        assert descriptions[2] == "risk_factors_frontpage_summary"

    @patch("symbology.database.pipeline_runs.get_db_session")
    @patch("symbology.worker.handlers.handle_content_generation")
    @patch("symbology.worker.handlers.handle_filing_ingestion")
    @patch("symbology.worker.handlers.handle_company_ingestion")
    def test_skips_when_no_documents(
        self, mock_company, mock_filing, mock_content_gen, mock_pr_session, tmp_path
    ):
        """Pipeline skips content gen when filings have no matching documents."""
        company_id = str(uuid7())
        mock_company.return_value = {
            "ticker": "MSFT",
            "company_id": company_id,
            "name": "Microsoft",
        }
        mock_filing.return_value = {
            "ticker": "MSFT",
            "form": "10-K",
            "filing_ids": [],
        }

        # Filing with no documents
        mock_filing_obj = MagicMock()
        mock_filing_obj.documents = []

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = [
            mock_filing_obj
        ]

        for name in ["risk_factors", "aggregate-summary", "general-summary"]:
            d = tmp_path / name
            d.mkdir()
            (d / "prompt.md").write_text(f"Prompt for {name}")

        mock_prompt = MagicMock()
        mock_prompt.content_hash = "prompt_hash"
        mock_prompt.get_short_hash.return_value = "prompt_ha"
        mock_mc = MagicMock()
        mock_mc.id = uuid7()
        mock_mc.get_short_hash.return_value = "mc_hash"

        with (
            patch(
                "symbology.database.base.get_db_session",
                return_value=mock_session,
            ),
            patch(
                "symbology.worker.pipeline.ensure_model_config",
                return_value=mock_mc,
            ),
            patch(
                "symbology.worker.pipeline.ensure_prompt",
                return_value=mock_prompt,
            ),
        ):
            result = handle_full_pipeline({
                "ticker": "MSFT",
                "forms": ["10-K"],
                "document_types": {"10-K": ["risk_factors"]},
                "prompts_dir": str(tmp_path),
            })

        assert result["content_generated"] == 0
        mock_content_gen.assert_not_called()

    @patch("symbology.database.pipeline_runs.get_db_session")
    @patch("symbology.worker.handlers.handle_filing_ingestion")
    @patch("symbology.worker.handlers.handle_company_ingestion")
    def test_defaults_to_both_forms(self, mock_company, mock_filing, mock_pr_session):
        """Without explicit forms, processes both 10-K and 10-Q."""
        company_id = str(uuid7())
        mock_company.return_value = {
            "ticker": "GOOG",
            "company_id": company_id,
            "name": "Alphabet",
        }
        mock_filing.return_value = {
            "ticker": "GOOG",
            "form": "10-K",
            "filing_ids": [],
        }

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.all.return_value = []

        mock_prompt = MagicMock()
        mock_prompt.content_hash = "ph"
        mock_prompt.get_short_hash.return_value = "ph"
        mock_mc = MagicMock()
        mock_mc.id = uuid7()
        mock_mc.get_short_hash.return_value = "mc"

        with (
            patch(
                "symbology.database.base.get_db_session",
                return_value=mock_session,
            ),
            patch(
                "symbology.worker.pipeline.ensure_model_config",
                return_value=mock_mc,
            ),
            patch(
                "symbology.worker.pipeline.ensure_prompt",
                return_value=mock_prompt,
            ),
        ):
            result = handle_full_pipeline({"ticker": "GOOG"})

        assert result["forms"] == ["10-K", "10-Q"]
        # Should have called filing ingestion twice (once per form)
        assert mock_filing.call_count == 2
        forms_called = [call[0][0]["form"] for call in mock_filing.call_args_list]
        assert "10-K" in forms_called
        assert "10-Q" in forms_called
