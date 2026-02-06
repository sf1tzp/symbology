"""Tests for scheduler polling logic."""
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID

from uuid_extensions import uuid7
import pytest

from symbology.scheduler.polling import (
    _known_accession_numbers,
    check_company_for_new_filings,
    poll_all_companies,
)


class TestKnownAccessionNumbers:
    """Test the DB lookup for existing accession numbers."""

    pytestmark = pytest.mark.integration

    def test_returns_known_accessions(self, db_session):
        from symbology.database.companies import Company
        from symbology.database.filings import Filing

        company = Company(name="Acme", ticker="ACME")
        db_session.add(company)
        db_session.commit()

        f1 = Filing(
            company_id=company.id,
            accession_number="0001-24-000001",
            form="10-K",
            filing_date=date.today(),
        )
        f2 = Filing(
            company_id=company.id,
            accession_number="0001-24-000002",
            form="10-Q",
            filing_date=date.today(),
        )
        db_session.add_all([f1, f2])
        db_session.commit()

        with patch("symbology.scheduler.polling.get_db_session", return_value=db_session):
            known = _known_accession_numbers(company.id, ["10-K", "10-Q"])

        assert known == {"0001-24-000001", "0001-24-000002"}

    def test_filters_by_form(self, db_session):
        from symbology.database.companies import Company
        from symbology.database.filings import Filing

        company = Company(name="Acme", ticker="ACME")
        db_session.add(company)
        db_session.commit()

        f1 = Filing(
            company_id=company.id,
            accession_number="0001-24-000001",
            form="10-K",
            filing_date=date.today(),
        )
        db_session.add(f1)
        db_session.commit()

        with patch("symbology.scheduler.polling.get_db_session", return_value=db_session):
            known = _known_accession_numbers(company.id, ["10-Q"])

        assert known == set()


class TestCheckCompanyForNewFilings:
    """Test EDGAR polling for a single company."""

    def test_detects_new_filing(self):
        mock_session = MagicMock()
        mock_company = MagicMock()
        mock_company.id = uuid7()
        mock_company.ticker = "AAPL"
        mock_session.query.return_value.filter.return_value.first.return_value = mock_company
        mock_session.query.return_value.filter.return_value.all.return_value = []

        mock_filing = MagicMock()
        mock_filing.accession_number = "0001-24-999999"
        mock_filing.filing_date = date.today()

        with (
            patch("symbology.scheduler.polling.get_db_session", return_value=mock_session),
            patch("symbology.scheduler.polling._fetch_recent_edgar_filings", return_value=[mock_filing]),
        ):
            new = check_company_for_new_filings("AAPL", ["10-K"], lookback_days=30)

        assert new == ["0001-24-999999"]

    def test_skips_known_filing(self):
        mock_session = MagicMock()
        mock_company = MagicMock()
        mock_company.id = uuid7()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_company
        mock_session.query.return_value.filter.return_value.all.return_value = [
            ("0001-24-000001",)
        ]

        mock_filing = MagicMock()
        mock_filing.accession_number = "0001-24-000001"
        mock_filing.filing_date = date.today()

        with (
            patch("symbology.scheduler.polling.get_db_session", return_value=mock_session),
            patch("symbology.scheduler.polling._fetch_recent_edgar_filings", return_value=[mock_filing]),
        ):
            new = check_company_for_new_filings("AAPL", ["10-K"], lookback_days=30)

        assert new == []

    def test_skips_old_filings(self):
        mock_session = MagicMock()
        mock_company = MagicMock()
        mock_company.id = uuid7()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_company
        mock_session.query.return_value.filter.return_value.all.return_value = []

        mock_filing = MagicMock()
        mock_filing.accession_number = "0001-24-000099"
        mock_filing.filing_date = date.today() - timedelta(days=60)

        with (
            patch("symbology.scheduler.polling.get_db_session", return_value=mock_session),
            patch("symbology.scheduler.polling._fetch_recent_edgar_filings", return_value=[mock_filing]),
        ):
            new = check_company_for_new_filings("AAPL", ["10-K"], lookback_days=30)

        assert new == []

    def test_company_not_in_db(self):
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None

        with patch("symbology.scheduler.polling.get_db_session", return_value=mock_session):
            new = check_company_for_new_filings("ZZZZZ", ["10-K"])

        assert new == []

    def test_edgar_error_caught(self):
        mock_session = MagicMock()
        mock_company = MagicMock()
        mock_company.id = uuid7()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_company
        mock_session.query.return_value.filter.return_value.all.return_value = []

        with (
            patch("symbology.scheduler.polling.get_db_session", return_value=mock_session),
            patch("symbology.scheduler.polling._fetch_recent_edgar_filings", side_effect=RuntimeError("EDGAR down")),
        ):
            new = check_company_for_new_filings("AAPL", ["10-K"])

        assert new == []


class TestPollAllCompanies:
    """Test the full poll cycle."""

    def test_enqueues_jobs_for_companies_with_new_filings(self):
        with (
            patch("symbology.scheduler.polling._init_edgar"),
            patch("symbology.scheduler.polling.get_all_company_tickers", return_value=["AAPL", "MSFT"]),
            patch("symbology.scheduler.polling.check_company_for_new_filings") as mock_check,
            patch("symbology.scheduler.polling.create_job") as mock_create_job,
        ):
            mock_check.side_effect = [["new-acc-1"], []]  # AAPL has new, MSFT doesn't
            count = poll_all_companies(forms=["10-K"], lookback_days=30)

        assert count == 1
        mock_create_job.assert_called_once()
        call_kwargs = mock_create_job.call_args
        assert call_kwargs[1]["params"]["ticker"] == "AAPL"
        assert call_kwargs[1]["params"]["trigger"] == "scheduled"

    def test_no_companies_returns_zero(self):
        with (
            patch("symbology.scheduler.polling._init_edgar"),
            patch("symbology.scheduler.polling.get_all_company_tickers", return_value=[]),
        ):
            count = poll_all_companies(forms=["10-K"])

        assert count == 0

    def test_continues_on_per_company_error(self):
        with (
            patch("symbology.scheduler.polling._init_edgar"),
            patch("symbology.scheduler.polling.get_all_company_tickers", return_value=["AAPL", "MSFT"]),
            patch("symbology.scheduler.polling.check_company_for_new_filings") as mock_check,
            patch("symbology.scheduler.polling.create_job") as mock_create_job,
        ):
            mock_check.side_effect = [RuntimeError("EDGAR down"), ["new-acc-2"]]
            count = poll_all_companies(forms=["10-K"], lookback_days=30)

        assert count == 1  # MSFT still got enqueued
