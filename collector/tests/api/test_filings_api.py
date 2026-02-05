"""Tests for the filings API endpoints."""
from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient
from collector.api.main import create_app
from collector.database.companies import Company
from collector.database.filings import Filing
from uuid_extensions import uuid7

client = TestClient(create_app())

# Sample data for tests
SAMPLE_COMPANY_ID = uuid7()
SAMPLE_FILING_ID = uuid7()
SAMPLE_TICKER = "AAPL"

SAMPLE_COMPANY = Company(
    id=SAMPLE_COMPANY_ID,
    name="Apple Inc.",
    display_name="Apple",
    ticker=SAMPLE_TICKER,
    exchanges=["NASDAQ"],
    sic="3571",
    sic_description="Electronic Computers",
    fiscal_year_end="2023-09-30",
    former_names=[]
)

SAMPLE_FILING = Filing(
    id=SAMPLE_FILING_ID,
    company_id=SAMPLE_COMPANY_ID,
    accession_number="0000320193-23-000077",
    form="10-K",
    filing_date=date(2023, 10, 27),
    url="https://www.sec.gov/Archives/edgar/data/320193/000032019323000077/aapl-20230930.htm",
    period_of_report=date(2023, 9, 30)
)

# Attach the company relationship
SAMPLE_FILING.company = SAMPLE_COMPANY


class TestFilingsApi:
    """Test class for Filings API endpoints."""

    @patch("src.api.routes.filings.get_filings_by_company")
    def test_get_company_filings_found(self, mock_get_filings):
        """Test retrieving filings by company ID when filings exist."""
        # Setup the mock to return our sample filings
        mock_get_filings.return_value = [SAMPLE_FILING]

        # Make the API call
        response = client.get(f"/filings/by-company/{SAMPLE_COMPANY_ID}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(SAMPLE_FILING_ID)
        assert data[0]["company_id"] == str(SAMPLE_COMPANY_ID)
        assert data[0]["accession_number"] == "0000320193-23-000077"
        assert data[0]["form"] == "10-K"
        assert data[0]["filing_date"] == "2023-10-27"
        assert data[0]["url"] == "https://www.sec.gov/Archives/edgar/data/320193/000032019323000077/aapl-20230930.htm"
        assert data[0]["period_of_report"] == "2023-09-30"

        # Verify the mock was called with the correct arguments
        mock_get_filings.assert_called_once_with(SAMPLE_COMPANY_ID)

    @patch("src.api.routes.filings.get_filings_by_company")
    def test_get_company_filings_empty_list(self, mock_get_filings):
        """Test retrieving filings by company ID when no filings exist."""
        # Setup the mock to return empty list
        mock_get_filings.return_value = []

        # Make the API call
        response = client.get(f"/filings/by-company/{SAMPLE_COMPANY_ID}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

        # Verify the mock was called with the correct arguments
        mock_get_filings.assert_called_once_with(SAMPLE_COMPANY_ID)

    @patch("src.api.routes.filings.get_filings_by_company")
    def test_get_company_filings_multiple_filings(self, mock_get_filings):
        """Test retrieving multiple filings by company ID."""
        # Setup the mock to return multiple filings
        filing2_id = uuid7()
        filing2 = Filing(
            id=filing2_id,
            company_id=SAMPLE_COMPANY_ID,
            accession_number="0000320193-23-000078",
            form="10-Q",
            filing_date=date(2023, 7, 28),
            url="https://www.sec.gov/Archives/edgar/data/320193/000032019323000078/aapl-20230630.htm",
            period_of_report=date(2023, 6, 30)
        )
        filing2.company = SAMPLE_COMPANY
        mock_get_filings.return_value = [SAMPLE_FILING, filing2]

        # Make the API call
        response = client.get(f"/filings/by-company/{SAMPLE_COMPANY_ID}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["form"] == "10-K"
        assert data[1]["form"] == "10-Q"

        # Verify the mock was called with the correct arguments
        mock_get_filings.assert_called_once_with(SAMPLE_COMPANY_ID)

    def test_get_company_filings_invalid_uuid(self):
        """Test retrieving filings with an invalid UUID format."""
        # Test with an invalid UUID
        invalid_uuid = "not-a-valid-uuid"
        response = client.get(f"/filings/by-company/{invalid_uuid}")

        # Assertions
        assert response.status_code == 422
        assert "uuid_parsing" in str(response.json())

    @patch("src.api.routes.filings.get_filings_by_company")
    def test_get_company_filings_database_error(self, mock_get_filings):
        """Test error handling when database operation fails."""
        # Setup the mock to raise an exception
        mock_get_filings.side_effect = Exception("Database connection failed")

        # Make the API call
        response = client.get(f"/filings/by-company/{SAMPLE_COMPANY_ID}")

        # Assertions
        assert response.status_code == 500
        assert "Failed to retrieve filings" in response.json()["detail"]

    @patch("src.database.companies.get_company_by_ticker")
    @patch("src.api.routes.filings.get_filings_by_company")
    def test_get_filings_by_ticker_found(self, mock_get_filings, mock_get_company):
        """Test retrieving filings by ticker when company and filings exist."""
        # Setup the mocks
        mock_get_company.return_value = SAMPLE_COMPANY
        mock_get_filings.return_value = [SAMPLE_FILING]

        # Make the API call
        response = client.get(f"/filings/by-ticker/{SAMPLE_TICKER}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(SAMPLE_FILING_ID)
        assert data[0]["company_id"] == str(SAMPLE_COMPANY_ID)
        assert data[0]["form"] == "10-K"

        # Verify the mocks were called correctly
        mock_get_company.assert_called_once_with(SAMPLE_TICKER)
        mock_get_filings.assert_called_once_with(SAMPLE_COMPANY_ID)

    @patch("src.database.companies.get_company_by_ticker")
    def test_get_filings_by_ticker_company_not_found(self, mock_get_company):
        """Test retrieving filings by ticker when company doesn't exist."""
        # Setup the mock to return None (company not found)
        mock_get_company.return_value = None

        # Make the API call
        response = client.get(f"/filings/by-ticker/{SAMPLE_TICKER}")

        # Assertions
        assert response.status_code == 404
        assert f"Company with ticker '{SAMPLE_TICKER}' not found" in response.json()["detail"]

        # Verify the mock was called
        mock_get_company.assert_called_once_with(SAMPLE_TICKER)

    @patch("src.database.companies.get_company_by_ticker")
    @patch("src.api.routes.filings.get_filings_by_company")
    def test_get_filings_by_ticker_empty_list(self, mock_get_filings, mock_get_company):
        """Test retrieving filings by ticker when company exists but has no filings."""
        # Setup the mocks
        mock_get_company.return_value = SAMPLE_COMPANY
        mock_get_filings.return_value = []

        # Make the API call
        response = client.get(f"/filings/by-ticker/{SAMPLE_TICKER}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

        # Verify the mocks were called correctly
        mock_get_company.assert_called_once_with(SAMPLE_TICKER)
        mock_get_filings.assert_called_once_with(SAMPLE_COMPANY_ID)

    @patch("src.database.companies.get_company_by_ticker")
    def test_get_filings_by_ticker_database_error(self, mock_get_company):
        """Test error handling when database operation fails for ticker lookup."""
        # Setup the mock to raise an exception
        mock_get_company.side_effect = Exception("Database connection failed")

        # Make the API call
        response = client.get(f"/filings/by-ticker/{SAMPLE_TICKER}")

        # Assertions
        assert response.status_code == 500
        assert "Failed to retrieve filings" in response.json()["detail"]

    @patch("src.database.companies.get_company_by_ticker")
    @patch("src.api.routes.filings.get_filings_by_company")
    def test_get_filings_by_ticker_filings_error(self, mock_get_filings, mock_get_company):
        """Test error handling when filings retrieval fails."""
        # Setup the mocks
        mock_get_company.return_value = SAMPLE_COMPANY
        mock_get_filings.side_effect = Exception("Failed to get filings")

        # Make the API call
        response = client.get(f"/filings/by-ticker/{SAMPLE_TICKER}")

        # Assertions
        assert response.status_code == 500
        assert "Failed to retrieve filings" in response.json()["detail"]
