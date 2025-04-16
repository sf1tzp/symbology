"""Tests for the company API endpoints."""
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

# Sample company data for tests
SAMPLE_COMPANY_ID = uuid4()
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
        response = client.get(f"/api/companies/{SAMPLE_COMPANY_ID}")

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
        response = client.get(f"/api/companies/{SAMPLE_COMPANY_ID}")

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