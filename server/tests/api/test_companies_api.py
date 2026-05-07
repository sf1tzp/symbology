"""Tests for the company API endpoints."""
from unittest.mock import patch

from fastapi.testclient import TestClient
from symbology.api.main import create_app
from symbology.database.companies import Company
from uuid_extensions import uuid7

client = TestClient(create_app())

# Sample company data for tests
SAMPLE_COMPANY_ID = uuid7()
SAMPLE_COMPANY_DATA = Company(
    id=SAMPLE_COMPANY_ID,
    name="Test Company",
    display_name="TESTCO",
    ticker="TEST",
    exchanges=["NYSE"],
    sic="7370",
    sic_description="Services-Computer Programming, Data Processing, Etc.",
    fiscal_year_end="2023-12-31",
    former_names=[{"name": "Old Test Inc.", "date": "2020-01-01"}]
)

SAMPLE_SEARCH_RESULTS = [
    Company(
        id=SAMPLE_COMPANY_ID,
        name="Test Company",
        display_name="TESTCO",
        ticker="TEST",
        exchanges=["NYSE"],
        sic="7370",
        sic_description="Services-Computer Programming, Data Processing, Etc.",
        fiscal_year_end="2023-12-31",
        former_names=[{"name": "Old Test Inc.", "date": "2020-01-01"}]
    ),
    Company(
        id=uuid7(),
        name="Another Test Corp",
        display_name="ANTEST",
        ticker="ANTEST",
        exchanges=["NASDAQ"],
        sic="7371",
        sic_description="Services-Computer Programming Services",
        fiscal_year_end="2023-12-31",
        former_names=[]
    )
]


class TestCompanyApi:
    """Test class for Company API endpoints."""

    @patch("symbology.api.routes.companies.search_companies_by_query")
    def test_search_companies_partial_found(self, mock_search_companies):
        """Test searching companies with partial query returns results."""
        # Setup the mock to return our sample search results
        mock_search_companies.return_value = SAMPLE_SEARCH_RESULTS

        # Make the API call
        response = client.get("/companies/search?query=test&limit=10")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Test Company"
        assert data[1]["name"] == "Another Test Corp"

        # Verify the mock was called with the correct arguments
        mock_search_companies.assert_called_once_with("test", 10)

    @patch("symbology.api.routes.companies.search_companies_by_query")
    def test_search_companies_partial_empty_results(self, mock_search_companies):
        """Test searching companies with query that returns no results."""
        # Setup the mock to return empty list
        mock_search_companies.return_value = []

        # Make the API call
        response = client.get("/companies/search?query=nonexistent&limit=10")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

        # Verify the mock was called with the correct arguments
        mock_search_companies.assert_called_once_with("nonexistent", 10)

    def test_search_companies_partial_empty_query(self):
        """Test searching companies with empty query returns 400."""
        # Make the API call with empty query
        response = client.get("/companies/search?query=&limit=10")

        # Assertions
        assert response.status_code == 400
        assert response.json()["detail"] == "Search query must not be empty"

    def test_search_companies_partial_no_query(self):
        """Test searching companies without query parameter returns 422."""
        # Make the API call without query parameter
        response = client.get("/companies/search?limit=10")

        # Assertions
        assert response.status_code == 422

    @patch("symbology.api.routes.companies.search_companies_by_query")
    def test_search_companies_partial_limit_bounds(self, mock_search_companies):
        """Test search with limit parameter validation."""
        # Setup the mock to return empty list for valid requests
        mock_search_companies.return_value = []

        # Test with limit too high
        response = client.get("/companies/search?query=test&limit=100")
        assert response.status_code == 422

        # Test with limit too low
        response = client.get("/companies/search?query=test&limit=0")
        assert response.status_code == 422

        # Test with valid limit
        response = client.get("/companies/search?query=test&limit=25")
        assert response.status_code == 200

        # Verify the mock was called for the valid request
        mock_search_companies.assert_called_once_with("test", 25)

    @patch("symbology.api.routes.companies.get_company")
    def test_get_company_by_id_found(self, mock_get_company):
        """Test retrieving a company by ID when it exists."""
        # Setup the mock to return our sample company as a dictionary
        mock_get_company.return_value = SAMPLE_COMPANY_DATA

        # Make the API call
        response = client.get(f"/companies/id/{SAMPLE_COMPANY_ID}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(SAMPLE_COMPANY_ID)
        assert data["name"] == "Test Company"
        assert data["ticker"] == "TEST"

        # Verify the mock was called with the correct arguments
        mock_get_company.assert_called_once_with(SAMPLE_COMPANY_ID)

    @patch("symbology.api.routes.companies.get_company")
    def test_get_company_by_id_not_found(self, mock_get_company):
        """Test retrieving a company by ID when it doesn't exist."""
        # Setup the mock to return None (company not found)
        mock_get_company.return_value = None

        # Make the API call
        response = client.get(f"/companies/id/{SAMPLE_COMPANY_ID}")

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "Company not found"

        # Verify the mock was called with the correct arguments
        mock_get_company.assert_called_once_with(SAMPLE_COMPANY_ID)

    def test_get_company_by_id_invalid_uuid(self):
        """Test retrieving a company with an invalid UUID format."""
        # Test with an invalid UUID
        invalid_uuid = "not-a-valid-uuid"
        response = client.get(f"/companies/id/{invalid_uuid}")

        # Assertions
        assert response.status_code == 422
        assert "uuid_parsing" in str(response.json())

    @patch("symbology.api.routes.companies.get_frontpage_summary_by_ticker")
    @patch("symbology.api.routes.companies.get_company_by_ticker")
    def test_search_companies_by_ticker_found(self, mock_get_company_by_ticker, mock_get_frontpage_summary):
        """Test searching for a company by ticker when it exists."""
        # Setup the mock to return our sample company as a dictionary
        mock_get_company_by_ticker.return_value = SAMPLE_COMPANY_DATA
        # Mock the frontpage summary retrieval
        mock_get_frontpage_summary.return_value = "Test company frontpage summary"

        # Make the API call
        response = client.get("/companies/?ticker=TEST")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        # API now returns a list when searching by ticker
        assert isinstance(data, list)
        assert len(data) == 1
        company = data[0]
        assert company["id"] == str(SAMPLE_COMPANY_ID)
        assert company["name"] == "Test Company"
        assert company["ticker"] == "TEST"

        # Verify the mock was called with the correct arguments
        mock_get_company_by_ticker.assert_called_once_with("TEST")

    @patch("symbology.api.routes.companies.get_frontpage_summary_by_ticker")
    @patch("symbology.api.routes.companies.get_company_by_ticker")
    def test_search_companies_by_ticker_not_found(self, mock_get_company_by_ticker, mock_get_frontpage_summary):
        """Test searching for a company by ticker when it doesn't exist."""
        # Setup the mock to return None (company not found)
        mock_get_company_by_ticker.return_value = None
        mock_get_frontpage_summary.return_value = None

        # Make the API call
        response = client.get("/companies/?ticker=NONEXISTENT")

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "Company with ticker NONEXISTENT not found"

        # Verify the mock was called with the correct arguments
        mock_get_company_by_ticker.assert_called_once_with("NONEXISTENT")

