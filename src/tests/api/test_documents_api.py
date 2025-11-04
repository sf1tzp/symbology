"""Tests for the document API endpoints."""
from unittest.mock import patch

from fastapi.testclient import TestClient
from src.api.main import create_app
from src.database.companies import Company
from src.database.documents import Document, DocumentType
from uuid_extensions import uuid7

client = TestClient(create_app())

# Sample data for tests
SAMPLE_COMPANY_ID = uuid7()
SAMPLE_FILING_ID = uuid7()
SAMPLE_DOCUMENT_ID = uuid7()

SAMPLE_COMPANY = Company(
    id=SAMPLE_COMPANY_ID,
    name="Apple Inc.",
    display_name="Apple",
    ticker="AAPL",
    exchanges=["NASDAQ"],
    sic="3571",
    sic_description="Electronic Computers",
    fiscal_year_end="2023-09-30",
    former_names=[]
)

SAMPLE_DOCUMENT = Document(
    id=SAMPLE_DOCUMENT_ID,
    filing_id=SAMPLE_FILING_ID,
    company_id=SAMPLE_COMPANY_ID,
    title="Management Discussion and Analysis",
    document_type=DocumentType.MDA,
    content="This is a sample 10-K document content",
    content_hash="a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456"
)

# Attach the company relationship
SAMPLE_DOCUMENT.company = SAMPLE_COMPANY


class TestDocumentApi:
    """Test class for Document API endpoints."""

    @patch("src.api.routes.documents.get_document")
    def test_get_document_by_id_found(self, mock_get_document):
        """Test retrieving a document by ID when it exists."""
        # Setup the mock to return our sample document
        mock_get_document.return_value = SAMPLE_DOCUMENT

        # Make the API call
        response = client.get(f"/documents/{SAMPLE_DOCUMENT_ID}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(SAMPLE_DOCUMENT_ID)
        assert data["filing_id"] == str(SAMPLE_FILING_ID)
        assert data["company_ticker"] == "AAPL"
        assert data["title"] == "Management Discussion and Analysis"
        assert data["document_type"] == "management_discussion"
        assert data["content"] == "This is a sample 10-K document content"
        assert data["content_hash"] == "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456"
        assert data["short_hash"] == "a1b2c3d4e5f6"
        assert data["filing"] is None

        # Verify the mock was called with the correct arguments
        mock_get_document.assert_called_once_with(SAMPLE_DOCUMENT_ID)

    @patch("src.api.routes.documents.get_document")
    def test_get_document_by_id_not_found(self, mock_get_document):
        """Test retrieving a document by ID when it doesn't exist."""
        # Setup the mock to return None (document not found)
        mock_get_document.return_value = None

        # Make the API call
        response = client.get(f"/documents/{SAMPLE_DOCUMENT_ID}")

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "Document not found"

        # Verify the mock was called with the correct arguments
        mock_get_document.assert_called_once_with(SAMPLE_DOCUMENT_ID)

    def test_get_document_by_id_invalid_uuid(self):
        """Test retrieving a document with an invalid UUID format."""
        # Test with an invalid UUID
        invalid_uuid = "not-a-valid-uuid"
        response = client.get(f"/documents/{invalid_uuid}")

        # Assertions
        assert response.status_code == 422
        assert "uuid_parsing" in str(response.json())

    @patch("src.api.routes.documents.get_document")
    def test_get_document_content_found(self, mock_get_document):
        """Test retrieving document content when document exists."""
        # Setup the mock to return our sample document
        mock_get_document.return_value = SAMPLE_DOCUMENT

        # Make the API call
        response = client.get(f"/documents/{SAMPLE_DOCUMENT_ID}/content")

        # Assertions
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert response.text == "This is a sample 10-K document content"

        # Verify the mock was called with the correct arguments
        mock_get_document.assert_called_once_with(SAMPLE_DOCUMENT_ID)

    @patch("src.api.routes.documents.get_document")
    def test_get_document_content_not_found(self, mock_get_document):
        """Test retrieving document content when document doesn't exist."""
        # Setup the mock to return None (document not found)
        mock_get_document.return_value = None

        # Make the API call
        response = client.get(f"/documents/{SAMPLE_DOCUMENT_ID}/content")

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "Document not found"

        # Verify the mock was called with the correct arguments
        mock_get_document.assert_called_once_with(SAMPLE_DOCUMENT_ID)

    @patch("src.api.routes.documents.get_document")
    def test_get_document_content_no_content(self, mock_get_document):
        """Test retrieving document content when document has no content."""
        # Setup document without content
        doc_no_content = Document(
            id=SAMPLE_DOCUMENT_ID,
            filing_id=SAMPLE_FILING_ID,
            company_id=SAMPLE_COMPANY_ID,
            title="Management Discussion and Analysis",
            document_type=DocumentType.MDA,
            content=None,
            content_hash="a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456"
        )
        doc_no_content.company = SAMPLE_COMPANY
        mock_get_document.return_value = doc_no_content

        # Make the API call
        response = client.get(f"/documents/{SAMPLE_DOCUMENT_ID}/content")

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "Document content not available"

        # Verify the mock was called with the correct arguments
        mock_get_document.assert_called_once_with(SAMPLE_DOCUMENT_ID)

    @patch("src.api.routes.documents.get_document")
    def test_get_document_content_empty_string(self, mock_get_document):
        """Test retrieving document content when content is empty string."""
        # Setup document with empty content
        doc_empty = Document(
            id=SAMPLE_DOCUMENT_ID,
            filing_id=SAMPLE_FILING_ID,
            company_id=SAMPLE_COMPANY_ID,
            title="Management Discussion and Analysis",
            document_type=DocumentType.MDA,
            content="",
            content_hash="a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456"
        )
        doc_empty.company = SAMPLE_COMPANY
        mock_get_document.return_value = doc_empty

        # Make the API call
        response = client.get(f"/documents/{SAMPLE_DOCUMENT_ID}/content")

        # Assertions
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert response.text == ""

        # Verify the mock was called with the correct arguments
        mock_get_document.assert_called_once_with(SAMPLE_DOCUMENT_ID)

    def test_get_document_content_invalid_uuid(self):
        """Test retrieving document content with an invalid UUID format."""
        # Test with an invalid UUID
        invalid_uuid = "not-a-valid-uuid"
        response = client.get(f"/documents/{invalid_uuid}/content")

        # Assertions
        assert response.status_code == 422
        assert "uuid_parsing" in str(response.json())

    @patch("src.api.routes.documents.get_document")
    def test_get_document_database_error(self, mock_get_document):
        """Test error handling when database query fails."""
        # Setup the mock to raise a database exception
        mock_get_document.side_effect = Exception("Database connection error")

        # Make the API call
        response = client.get(f"/documents/{SAMPLE_DOCUMENT_ID}")

        # Assertions
        assert response.status_code == 500
        assert "Failed to get document" in response.json()["detail"]

        # Verify the mock was called with the correct arguments
        mock_get_document.assert_called_once_with(SAMPLE_DOCUMENT_ID)

    @patch("src.api.routes.documents.get_document")
    def test_get_document_content_database_error(self, mock_get_document):
        """Test error handling when database query fails for content endpoint."""
        # Setup the mock to raise a database exception
        mock_get_document.side_effect = Exception("Database connection error")

        # Make the API call
        response = client.get(f"/documents/{SAMPLE_DOCUMENT_ID}/content")

        # Assertions
        assert response.status_code == 500
        assert "Failed to get document content" in response.json()["detail"]

        # Verify the mock was called with the correct arguments
        mock_get_document.assert_called_once_with(SAMPLE_DOCUMENT_ID)