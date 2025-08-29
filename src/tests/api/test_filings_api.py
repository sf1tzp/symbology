"""Tests for the filings API endpoints."""
from datetime import date
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from src.api.main import create_app

client = TestClient(create_app())

# Sample data for tests
SAMPLE_COMPANY_ID = uuid4()
SAMPLE_FILING_ID = uuid4()
SAMPLE_TICKER = "AAPL"


def create_mock_filing():
    """Create a mock filing object for testing."""
    mock_filing = MagicMock()
    mock_filing.id = SAMPLE_FILING_ID
    mock_filing.company_id = SAMPLE_COMPANY_ID
    mock_filing.accession_number = "0000320193-23-000077"
    mock_filing.filing_type = "10-K"
    mock_filing.filing_date = date(2023, 10, 27)
    mock_filing.filing_url = "https://www.sec.gov/Archives/edgar/data/320193/000032019323000077/aapl-20230930.htm"
    mock_filing.period_of_report = date(2023, 9, 30)
    return mock_filing


def create_mock_company():
    """Create a mock company object for testing."""
    mock_company = MagicMock()
    mock_company.id = SAMPLE_COMPANY_ID
    mock_company.ticker = SAMPLE_TICKER
    mock_company.name = "Apple Inc."
    return mock_company


class TestFilingsApi:
    """Test class for Filings API endpoints."""

    @patch("src.api.routes.filings.get_filings_by_company")
    def test_get_company_filings_found(self, mock_get_filings):
        """Test retrieving filings by company ID when filings exist."""
        # Setup the mock to return our sample filings
        mock_filing = create_mock_filing()
        mock_get_filings.return_value = [mock_filing]

        # Make the API call
        response = client.get(f"/filings/by-company/{SAMPLE_COMPANY_ID}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(SAMPLE_FILING_ID)
        assert data[0]["company_id"] == str(SAMPLE_COMPANY_ID)
        assert data[0]["accession_number"] == "0000320193-23-000077"
        assert data[0]["filing_type"] == "10-K"
        assert data[0]["filing_date"] == "2023-10-27"
        assert data[0]["filing_url"] == "https://www.sec.gov/Archives/edgar/data/320193/000032019323000077/aapl-20230930.htm"
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
        mock_filing1 = create_mock_filing()
        mock_filing2 = create_mock_filing()
        mock_filing2.id = uuid4()
        mock_filing2.filing_type = "10-Q"
        mock_filing2.accession_number = "0000320193-23-000078"
        mock_get_filings.return_value = [mock_filing1, mock_filing2]

        # Make the API call
        response = client.get(f"/filings/by-company/{SAMPLE_COMPANY_ID}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["filing_type"] == "10-K"
        assert data[1]["filing_type"] == "10-Q"

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
        mock_company = create_mock_company()
        mock_get_company.return_value = mock_company
        mock_filing = create_mock_filing()
        mock_get_filings.return_value = [mock_filing]

        # Make the API call
        response = client.get(f"/filings/by-ticker/{SAMPLE_TICKER}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(SAMPLE_FILING_ID)
        assert data[0]["company_id"] == str(SAMPLE_COMPANY_ID)
        assert data[0]["filing_type"] == "10-K"

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
        mock_company = create_mock_company()
        mock_get_company.return_value = mock_company
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
        mock_company = create_mock_company()
        mock_get_company.return_value = mock_company
        mock_get_filings.side_effect = Exception("Failed to get filings")

        # Make the API call
        response = client.get(f"/filings/by-ticker/{SAMPLE_TICKER}")

        # Assertions
        assert response.status_code == 500
        assert "Failed to retrieve filings" in response.json()["detail"]
