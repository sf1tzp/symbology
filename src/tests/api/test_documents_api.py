"""Tests for the document API endpoints."""
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

# Sample data for tests
SAMPLE_COMPANY_ID = uuid4()
SAMPLE_FILING_ID = uuid4()
SAMPLE_DOCUMENT_ID = uuid4()


def create_mock_document():
    """Create a mock document object for testing."""
    mock_document = MagicMock()
    mock_document.id = SAMPLE_DOCUMENT_ID
    mock_document.filing_id = SAMPLE_FILING_ID
    mock_document.company_id = SAMPLE_COMPANY_ID
    mock_document.document_name = "test_10k.htm"
    mock_document.content = "This is a sample 10-K document content"
    mock_document.filing = None  # No filing relationship for basic test
    return mock_document


class TestDocumentApi:
    """Test class for Document API endpoints."""

    @patch("src.api.routes.documents.get_document")
    def test_get_document_by_id_found(self, mock_get_document):
        """Test retrieving a document by ID when it exists."""
        # Setup the mock to return our sample document
        mock_get_document.return_value = create_mock_document()

        # Make the API call
        response = client.get(f"/api/documents/{SAMPLE_DOCUMENT_ID}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(SAMPLE_DOCUMENT_ID)
        assert data["document_name"] == "test_10k.htm"
        assert data["content"] == "This is a sample 10-K document content"

        # Verify the mock was called with the correct arguments
        mock_get_document.assert_called_once_with(SAMPLE_DOCUMENT_ID)

    @patch("src.api.routes.documents.get_document")
    def test_get_document_by_id_not_found(self, mock_get_document):
        """Test retrieving a document by ID when it doesn't exist."""
        # Setup the mock to return None (document not found)
        mock_get_document.return_value = None

        # Make the API call
        response = client.get(f"/api/documents/{SAMPLE_DOCUMENT_ID}")

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "Document not found"

        # Verify the mock was called with the correct arguments
        mock_get_document.assert_called_once_with(SAMPLE_DOCUMENT_ID)

    def test_get_document_by_id_invalid_uuid(self):
        """Test retrieving a document with an invalid UUID format."""
        # Test with an invalid UUID
        invalid_uuid = "not-a-valid-uuid"
        response = client.get(f"/api/documents/{invalid_uuid}")

        # Assertions
        assert response.status_code == 422
        assert "uuid_parsing" in str(response.json())

    @patch("src.api.routes.documents.get_document")
    def test_get_document_content_found(self, mock_get_document):
        """Test retrieving document content when document exists."""
        # Setup the mock to return our sample document
        mock_get_document.return_value = create_mock_document()

        # Make the API call
        response = client.get(f"/api/documents/{SAMPLE_DOCUMENT_ID}/content")

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
        response = client.get(f"/api/documents/{SAMPLE_DOCUMENT_ID}/content")

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "Document not found"

        # Verify the mock was called with the correct arguments
        mock_get_document.assert_called_once_with(SAMPLE_DOCUMENT_ID)

    @patch("src.api.routes.documents.get_document")
    def test_get_document_content_no_content(self, mock_get_document):
        """Test retrieving document content when document has no content."""
        # Setup document mock without content
        mock_document = create_mock_document()
        mock_document.content = None
        mock_get_document.return_value = mock_document

        # Make the API call
        response = client.get(f"/api/documents/{SAMPLE_DOCUMENT_ID}/content")

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == "Document content not available"

        # Verify the mock was called with the correct arguments
        mock_get_document.assert_called_once_with(SAMPLE_DOCUMENT_ID)

    @patch("src.api.routes.documents.get_document")
    def test_get_document_content_empty_string(self, mock_get_document):
        """Test retrieving document content when content is empty string."""
        # Setup document mock with empty content
        mock_document = create_mock_document()
        mock_document.content = ""
        mock_get_document.return_value = mock_document

        # Make the API call
        response = client.get(f"/api/documents/{SAMPLE_DOCUMENT_ID}/content")

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
        response = client.get(f"/api/documents/{invalid_uuid}/content")

        # Assertions
        assert response.status_code == 422
        assert "uuid_parsing" in str(response.json())

    @patch("src.api.routes.documents.get_document")
    def test_get_document_database_error(self, mock_get_document):
        """Test error handling when database query fails."""
        # Setup the mock to raise a database exception
        mock_get_document.side_effect = Exception("Database connection error")

        # Make the API call
        response = client.get(f"/api/documents/{SAMPLE_DOCUMENT_ID}")

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
        response = client.get(f"/api/documents/{SAMPLE_DOCUMENT_ID}/content")

        # Assertions
        assert response.status_code == 500
        assert "Failed to get document content" in response.json()["detail"]

        # Verify the mock was called with the correct arguments
        mock_get_document.assert_called_once_with(SAMPLE_DOCUMENT_ID)