"""Tests for the document API endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from uuid import UUID, uuid4

from src.api.main import app

client = TestClient(app)

# Sample data for tests
SAMPLE_COMPANY_ID = uuid4()
SAMPLE_FILING_ID = uuid4()
SAMPLE_DOCUMENT_ID = uuid4()

# Sample document data
SAMPLE_DOCUMENT_DATA = {
    "id": SAMPLE_DOCUMENT_ID,
    "filing_id": SAMPLE_FILING_ID,
    "company_id": SAMPLE_COMPANY_ID,
    "document_name": "test_10k.htm",
    "content": "This is a sample 10-K document content"
}


class TestDocumentApi:
    """Test class for Document API endpoints."""

    @patch("src.api.routes.documents.get_document")
    def test_get_document_by_id_found(self, mock_get_document):
        """Test retrieving a document by ID when it exists."""
        # Setup the mock to return our sample document
        mock_get_document.return_value = SAMPLE_DOCUMENT_DATA

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