"""Tests for the filing API endpoints."""
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

# Sample data for tests
SAMPLE_COMPANY_ID = uuid4()
SAMPLE_FILING_ID = uuid4()
SAMPLE_DOCUMENT_ID = uuid4()

# Sample filing data
SAMPLE_FILING_DATA = {
    "id": SAMPLE_FILING_ID,
    "company_id": SAMPLE_COMPANY_ID,
    "accession_number": "0001234567-23-000123",
    "filing_type": "10-K",
    "filing_date": "2023-02-15",
    "filing_url": "https://www.sec.gov/Archives/edgar/data/1234567/000123456723000123/0001234567-23-000123-index.htm",
    "period_of_report": "2022-12-31"
}

# Sample list of filings for a company
SAMPLE_COMPANY_FILINGS = [
    SAMPLE_FILING_DATA,
    {
        "id": uuid4(),
        "company_id": SAMPLE_COMPANY_ID,
        "accession_number": "0001234567-23-000456",
        "filing_type": "10-Q",
        "filing_date": "2023-05-10",
        "filing_url": "https://www.sec.gov/Archives/edgar/data/1234567/000123456723000456/0001234567-23-000456-index.htm",
        "period_of_report": "2023-03-31"
    }
]

# Sample list of documents for a filing
SAMPLE_FILING_DOCUMENTS = [
    {
        "id": SAMPLE_DOCUMENT_ID,
        "filing_id": SAMPLE_FILING_ID,
        "company_id": SAMPLE_COMPANY_ID,
        "document_type": "10-K",
        "document_name": "Annual Report 10-K",
        "filename": "test_10k.htm",
        "description": "Annual Report",
        "sequence": 1,
        "url": "https://www.sec.gov/Archives/edgar/data/1234567/000123456723000123/test_10k.htm",
        "content": "This is a sample 10-K document content"
    },
    {
        "id": uuid4(),
        "filing_id": SAMPLE_FILING_ID,
        "company_id": SAMPLE_COMPANY_ID,
        "document_type": "EX-101",
        "document_name": "Exhibit 101",
        "filename": "test_ex101.htm",
        "description": "Exhibit 101",
        "sequence": 2,
        "url": "https://www.sec.gov/Archives/edgar/data/1234567/000123456723000123/test_ex101.htm",
        "content": "This is a sample exhibit document content"
    }
]


class TestFilingApi:
    """Test class for Filing API endpoints."""

    @patch("src.api.routes.filings.get_filing")
    def test_get_filing_by_id_found(self, mock_get_filing):
        """Test retrieving a filing by ID when it exists."""
        # Setup the mock to return our sample filing
        mock_get_filing.return_value = SAMPLE_FILING_DATA

        # Make the API call
        response = client.get(f"/api/filings/{SAMPLE_FILING_ID}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(SAMPLE_FILING_ID)
        assert data["accession_number"] == "0001234567-23-000123"
        assert data["filing_type"] == "10-K"

        # Verify the mock was called with the correct arguments
        mock_get_filing.assert_called_once_with(SAMPLE_FILING_ID)

    @patch("src.api.routes.filings.get_filing")
    def test_get_filing_by_id_not_found(self, mock_get_filing):
        """Test retrieving a filing by ID when it doesn't exist."""
        # Setup the mock to return None (filing not found)
        mock_get_filing.return_value = None

        # Make the API call
        response = client.get(f"/api/filings/{SAMPLE_FILING_ID}")

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "Filing not found"

        # Verify the mock was called with the correct arguments
        mock_get_filing.assert_called_once_with(SAMPLE_FILING_ID)

    @patch("src.api.routes.filings.get_filings_by_company")
    def test_get_company_filings_found(self, mock_get_filings_by_company):
        """Test retrieving all filings for a company when they exist."""
        # Setup the mock to return our sample filings
        mock_get_filings_by_company.return_value = SAMPLE_COMPANY_FILINGS

        # Make the API call
        response = client.get(f"/api/filings/by-company/{SAMPLE_COMPANY_ID}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == str(SAMPLE_FILING_ID)
        assert data[0]["filing_type"] == "10-K"
        assert data[1]["filing_type"] == "10-Q"

        # Verify the mock was called with the correct arguments
        mock_get_filings_by_company.assert_called_once_with(SAMPLE_COMPANY_ID)

    @patch("src.api.routes.filings.get_filings_by_company")
    def test_get_company_filings_empty(self, mock_get_filings_by_company):
        """Test retrieving all filings for a company when none exist."""
        # Setup the mock to return an empty list
        mock_get_filings_by_company.return_value = []

        # Make the API call
        response = client.get(f"/api/filings/by-company/{SAMPLE_COMPANY_ID}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

        # Verify the mock was called with the correct arguments
        mock_get_filings_by_company.assert_called_once_with(SAMPLE_COMPANY_ID)

    @patch("src.api.routes.filings.get_filing")
    @patch("src.api.routes.filings.get_documents_by_filing")
    def test_get_filing_documents_found(self, mock_get_documents_by_filing, mock_get_filing):
        """Test retrieving all documents for a filing when they exist."""
        # Setup the mocks
        mock_get_filing.return_value = SAMPLE_FILING_DATA
        mock_get_documents_by_filing.return_value = SAMPLE_FILING_DOCUMENTS

        # Make the API call
        response = client.get(f"/api/filings/{SAMPLE_FILING_ID}/documents")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == str(SAMPLE_DOCUMENT_ID)
        assert data[0]["document_name"] == "Annual Report 10-K"
        assert data[1]["document_name"] == "Exhibit 101"

        # Verify the mocks were called with the correct arguments
        mock_get_filing.assert_called_once_with(SAMPLE_FILING_ID)
        mock_get_documents_by_filing.assert_called_once_with(SAMPLE_FILING_ID)

    @patch("src.api.routes.filings.get_filing")
    def test_get_filing_documents_filing_not_found(self, mock_get_filing):
        """Test retrieving documents when the filing doesn't exist."""
        # Setup the mock to return None (filing not found)
        mock_get_filing.return_value = None

        # Make the API call
        response = client.get(f"/api/filings/{SAMPLE_FILING_ID}/documents")

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "Filing not found"

        # Verify the mock was called with the correct arguments
        mock_get_filing.assert_called_once_with(SAMPLE_FILING_ID)

    @patch("src.api.routes.filings.get_filing")
    @patch("src.api.routes.filings.get_documents_by_filing")
    def test_get_filing_documents_empty(self, mock_get_documents_by_filing, mock_get_filing):
        """Test retrieving all documents for a filing when none exist."""
        # Setup the mocks
        mock_get_filing.return_value = SAMPLE_FILING_DATA
        mock_get_documents_by_filing.return_value = []

        # Make the API call
        response = client.get(f"/api/filings/{SAMPLE_FILING_ID}/documents")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

        # Verify the mocks were called with the correct arguments
        mock_get_filing.assert_called_once_with(SAMPLE_FILING_ID)
        mock_get_documents_by_filing.assert_called_once_with(SAMPLE_FILING_ID)