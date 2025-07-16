"""Tests for the completions API routes."""
from datetime import datetime
from unittest.mock import patch
import uuid

from fastapi.testclient import TestClient
from src.api.main import app
from src.database.completions import Completion
from src.database.documents import Document

client = TestClient(app)


class TestCompletionsApi:
    """Test class for Completions API endpoints."""

    @patch("src.api.routes.completions.get_completion")
    def test_get_completion_by_id_found(self, mock_get_completion):
        """Test getting a completion by ID when it exists."""
        # Use proper UUID objects
        test_completion_id = uuid.UUID('123e4567-e89b-12d3-a456-426614174000')
        test_prompt_id = uuid.UUID('123e4567-e89b-12d3-a456-426614174003')
        test_doc_id = uuid.UUID('123e4567-e89b-12d3-a456-426614174005')

        # Mock the completion with source documents
        mock_completion = Completion(
            id=test_completion_id,
            system_prompt_id=test_prompt_id,
            model="gpt-4",
            temperature=0.7,
            top_p=1.0,
            num_ctx=4096,
            created_at=datetime(2023, 12, 25, 12, 30, 45),
            total_duration=2.5,
            source_documents=[Document(id=test_doc_id)]
        )
        mock_get_completion.return_value = mock_completion

        # Make the API call
        response = client.get(f"/api/completions/{test_completion_id}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_completion_id)
        assert data["system_prompt_id"] == str(test_prompt_id)
        assert data["model"] == "gpt-4"
        assert data["temperature"] == 0.7
        assert data["top_p"] == 1.0
        assert data["num_ctx"] == 4096
        assert data["total_duration"] == 2.5
        assert len(data["source_documents"]) == 1
        assert data["source_documents"][0] == str(test_doc_id)

        # Verify the mock was called with the correct arguments
        mock_get_completion.assert_called_once_with(test_completion_id)

    @patch("src.api.routes.completions.get_completion")
    def test_get_completion_by_id_not_found(self, mock_get_completion):
        """Test getting a completion by ID when it doesn't exist."""
        test_completion_id = uuid.UUID('123e4567-e89b-12d3-a456-426614174999')

        # Setup the mock to return None (completion not found)
        mock_get_completion.return_value = None

        # Make the API call
        response = client.get(f"/api/completions/{test_completion_id}")

        # Assertions
        assert response.status_code == 404
        assert f"Completion with ID {test_completion_id} not found" in response.json()["detail"]

        # Verify the mock was called with the correct arguments
        mock_get_completion.assert_called_once_with(test_completion_id)

    @patch("src.api.routes.completions.get_completion")
    def test_get_completion_by_id_no_source_documents(self, mock_get_completion):
        """Test getting a completion that has no source documents."""
        test_completion_id = uuid.UUID('123e4567-e89b-12d3-a456-426614174001')

        # Mock the completion with no source documents
        mock_completion = Completion(
            id=test_completion_id,
            model="gpt-3.5-turbo",
            temperature=0.5,
            created_at=datetime(2023, 12, 25, 12, 30, 45),
            total_duration=1.8,
            source_documents=[]  # No source documents
        )
        mock_get_completion.return_value = mock_completion

        # Make the API call
        response = client.get(f"/api/completions/{test_completion_id}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_completion_id)
        assert data["model"] == "gpt-3.5-turbo"
        assert data["source_documents"] == []

        # Verify the mock was called with the correct arguments
        mock_get_completion.assert_called_once_with(test_completion_id)

    def test_get_completion_invalid_uuid_format(self):
        """Test getting a completion with an invalid UUID format."""
        invalid_uuid = "not-a-valid-uuid"

        # Make the API call
        response = client.get(f"/api/completions/{invalid_uuid}")

        # Assertions
        assert response.status_code == 422
        assert "uuid_parsing" in str(response.json())

    @patch("src.api.routes.completions.get_completion")
    def test_get_completion_internal_error(self, mock_get_completion):
        """Test handling of internal server errors."""
        test_completion_id = uuid.UUID('123e4567-e89b-12d3-a456-426614174000')

        # Setup the mock to raise an exception
        mock_get_completion.side_effect = Exception("Database connection error")

        # Make the API call
        response = client.get(f"/api/completions/{test_completion_id}")

        # Assertions
        assert response.status_code == 500
        assert "Failed to get completion" in response.json()["detail"]

        # Verify the mock was called with the correct arguments
        mock_get_completion.assert_called_once_with(test_completion_id)