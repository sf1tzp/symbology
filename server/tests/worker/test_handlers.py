"""Tests for job handlers with mocked DB/LLM/EDGAR dependencies."""
import sys
from unittest.mock import MagicMock, patch

from uuid_extensions import uuid7

from symbology.database.jobs import JobType
from symbology.worker.handlers import (
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
