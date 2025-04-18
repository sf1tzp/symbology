"""Tests for the company API endpoints."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from uuid_extensions import uuid7

from src.api.main import app

client = TestClient(app)

# Sample company data for tests
SAMPLE_COMPANY_ID = uuid7()
SAMPLE_COMPANY_DATA = {
    "id": SAMPLE_COMPANY_ID,
    "name": "Test Company",
    "display_name": "TESTCO",
    "cik": "0001234567",
    "tickers": ["TEST", "TSTC"],
    "exchanges": ["NYSE"],
    "sic": "7370",
    "sic_description": "Services-Computer Programming, Data Processing, Etc.",
    "fiscal_year_end": "2023-12-31",
    "entity_type": "CORP",
    "ein": "12-3456789",
    "is_company": True,
    "former_names": [{"name": "Old Test Inc.", "date": "2020-01-01"}]
}


class TestCompanyApi:
    """Test class for Company API endpoints."""

    @patch("src.api.routes.companies.get_company")
    def test_get_company_by_id_found(self, mock_get_company):
        """Test retrieving a company by ID when it exists."""
        # Setup the mock to return our sample company as a dictionary
        mock_get_company.return_value = SAMPLE_COMPANY_DATA

        # Make the API call
        response = client.get(f"/api/companies/id/{SAMPLE_COMPANY_ID}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(SAMPLE_COMPANY_ID)
        assert data["name"] == "Test Company"
        assert data["cik"] == "0001234567"
        assert "TEST" in data["tickers"]

        # Verify the mock was called with the correct arguments
        mock_get_company.assert_called_once_with(SAMPLE_COMPANY_ID)

    @patch("src.api.routes.companies.get_company")
    def test_get_company_by_id_not_found(self, mock_get_company):
        """Test retrieving a company by ID when it doesn't exist."""
        # Setup the mock to return None (company not found)
        mock_get_company.return_value = None

        # Make the API call
        response = client.get(f"/api/companies/id/{SAMPLE_COMPANY_ID}")

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "Company not found"

        # Verify the mock was called with the correct arguments
        mock_get_company.assert_called_once_with(SAMPLE_COMPANY_ID)

    @patch("src.api.routes.companies.get_company_by_ticker")
    def test_search_companies_by_ticker_found(self, mock_get_company_by_ticker):
        """Test searching for a company by ticker when it exists."""
        # Setup the mock to return our sample company as a dictionary
        mock_get_company_by_ticker.return_value = SAMPLE_COMPANY_DATA

        # Make the API call
        response = client.get("/api/companies/?ticker=TEST")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(SAMPLE_COMPANY_ID)
        assert data["name"] == "Test Company"
        assert "TEST" in data["tickers"]

        # Verify the mock was called with the correct arguments
        mock_get_company_by_ticker.assert_called_once_with("TEST")

    @patch("src.api.routes.companies.get_company_by_ticker")
    def test_search_companies_by_ticker_not_found(self, mock_get_company_by_ticker):
        """Test searching for a company by ticker when it doesn't exist."""
        # Setup the mock to return None (company not found)
        mock_get_company_by_ticker.return_value = None

        # Make the API call
        response = client.get("/api/companies/?ticker=NONEXISTENT")

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "Company with ticker NONEXISTENT not found"

        # Verify the mock was called with the correct arguments
        mock_get_company_by_ticker.assert_called_once_with("NONEXISTENT")

    @patch("src.api.routes.companies.get_company_by_cik")
    def test_search_companies_by_cik_found(self, mock_get_company_by_cik):
        """Test searching for a company by CIK when it exists."""
        # Setup the mock to return our sample company as a dictionary
        mock_get_company_by_cik.return_value = SAMPLE_COMPANY_DATA

        # Make the API call
        response = client.get("/api/companies/?cik=0001234567")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(SAMPLE_COMPANY_ID)
        assert data["name"] == "Test Company"
        assert data["cik"] == "0001234567"

        # Verify the mock was called with the correct arguments
        mock_get_company_by_cik.assert_called_once_with("0001234567")

    @patch("src.api.routes.companies.get_company_by_cik")
    def test_search_companies_by_cik_not_found(self, mock_get_company_by_cik):
        """Test searching for a company by CIK when it doesn't exist."""
        # Setup the mock to return None (company not found)
        mock_get_company_by_cik.return_value = None

        # Make the API call
        response = client.get("/api/companies/?cik=9999999999")

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "Company with CIK 9999999999 not found"

        # Verify the mock was called with the correct arguments
        mock_get_company_by_cik.assert_called_once_with("9999999999")

    def test_search_companies_no_params(self):
        """Test searching for companies without providing required parameters."""
        # Make the API call without query parameters
        response = client.get("/api/companies/")

        # Assertions
        assert response.status_code == 400
        assert response.json()["detail"] == "Either ticker or CIK parameter is required"

    @patch("src.api.routes.companies.get_company_by_ticker")
    @patch("src.api.routes.companies.edgar_login")
    @patch("src.api.routes.companies.ingest_company")
    @patch("src.api.routes.companies.ingest_filing")
    @patch("src.api.routes.companies.ingest_filing_documents")
    @patch("src.api.routes.companies.ingest_financial_data")
    @patch("src.api.routes.companies.get_company")
    def test_search_companies_auto_ingest_success(
        self, mock_get_company, mock_ingest_financial_data, mock_ingest_filing_documents,
        mock_ingest_filing, mock_ingest_company, mock_edgar_login, mock_get_company_by_ticker
    ):
        """Test auto-ingestion works when company is not found by ticker."""
        # Setup initial search to return None (company not found)
        mock_get_company_by_ticker.return_value = None

        # Setup mock for company ingestion
        edgar_company = MagicMock()
        edgar_company.name = "Auto Ingested Company"
        mock_ingest_company.return_value = (edgar_company, SAMPLE_COMPANY_ID)

        # Setup filing ingestion mocks
        filing_mock = MagicMock()
        filing_id = uuid7()
        mock_ingest_filing.return_value = (filing_mock, filing_id)

        # Setup document ingestion mocks
        doc_uuids = [uuid7() for _ in range(3)]
        mock_ingest_filing_documents.return_value = doc_uuids

        # Setup financial data ingestion mocks
        mock_ingest_financial_data.return_value = {"income": 5, "balance": 3, "cash": 2}

        # Setup final company retrieval
        mock_get_company.return_value = SAMPLE_COMPANY_DATA

        # Make the API call with auto_ingest=True
        response = client.get("/api/companies/?ticker=AUTO&auto_ingest=true")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(SAMPLE_COMPANY_ID)
        assert data["name"] == "Test Company"

        # Verify the mocks were called correctly
        mock_get_company_by_ticker.assert_called_once_with("AUTO")
        mock_edgar_login.assert_called_once()
        mock_ingest_company.assert_called_once_with("AUTO")
        # Should try to ingest filings for 5 most recent years
        assert mock_ingest_filing.call_count == 5
        # Final company should be retrieved
        mock_get_company.assert_called_once_with(SAMPLE_COMPANY_ID)

    @patch("src.api.routes.companies.get_company_by_ticker")
    @patch("src.api.routes.companies.edgar_login")
    @patch("src.api.routes.companies.ingest_company")
    def test_search_companies_auto_ingest_failure(
        self, mock_ingest_company, mock_edgar_login, mock_get_company_by_ticker
    ):
        """Test auto-ingestion failure is handled properly."""
        # Setup initial search to return None (company not found)
        mock_get_company_by_ticker.return_value = None

        # Setup mock for company ingestion to fail
        mock_ingest_company.side_effect = Exception("API Error: Unable to find company")

        # Make the API call with auto_ingest=True
        response = client.get("/api/companies/?ticker=FAIL&auto_ingest=true")

        # Assertions
        assert response.status_code == 500
        assert "Failed to automatically ingest company with ticker FAIL" in response.json()["detail"]

        # Verify the mocks were called correctly
        mock_get_company_by_ticker.assert_called_once_with("FAIL")
        mock_edgar_login.assert_called_once()
        mock_ingest_company.assert_called_once_with("FAIL")

    @patch("src.api.routes.companies.get_company_by_cik")
    def test_search_companies_auto_ingest_by_cik_not_implemented(self, mock_get_company_by_cik):
        """Test auto-ingestion by CIK is not yet implemented."""
        # Setup the mock to return None (company not found)
        mock_get_company_by_cik.return_value = None

        # Make the API call with auto_ingest=True
        response = client.get("/api/companies/?cik=9999999999&auto_ingest=true")

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "Company with CIK 9999999999 not found"

        # Verify the mock was called with the correct arguments
        mock_get_company_by_cik.assert_called_once_with("9999999999")

    @patch("src.api.routes.companies.get_company_by_ticker")
    def test_search_companies_auto_ingest_default_false(self, mock_get_company_by_ticker):
        """Test that auto_ingest defaults to False and doesn't trigger ingestion."""
        # Setup the mock to return None (company not found)
        mock_get_company_by_ticker.return_value = None

        # Make the API call without specifying auto_ingest (should default to False)
        response = client.get("/api/companies/?ticker=TEST")

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "Company with ticker TEST not found"

        # Verify only the initial ticker search was performed
        mock_get_company_by_ticker.assert_called_once_with("TEST")