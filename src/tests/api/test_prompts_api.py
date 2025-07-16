"""Tests for the prompts API endpoints."""
from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

# Sample data for tests
SAMPLE_PROMPT_ID = uuid4()


def create_mock_prompt():
    """Create a mock prompt object for testing."""
    mock_prompt = MagicMock()
    mock_prompt.id = SAMPLE_PROMPT_ID
    mock_prompt.name = "Financial Statement Analysis"
    mock_prompt.description = "Analyzes financial statements from SEC filings"
    mock_prompt.content = "Analyze the financial statements for the company, focusing on key metrics and trends."

    # Mock the role enum
    mock_role = MagicMock()
    mock_role.value = "system"
    mock_prompt.role = mock_role

    return mock_prompt


class TestPromptsApi:
    """Test class for Prompts API endpoints."""

    @patch("src.api.routes.prompts.get_prompt")
    def test_get_prompt_by_id_found(self, mock_get_prompt):
        """Test retrieving a prompt by ID when it exists."""
        # Setup the mock to return our sample prompt
        mock_get_prompt.return_value = create_mock_prompt()

        # Make the API call
        response = client.get(f"/api/prompts/{SAMPLE_PROMPT_ID}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(SAMPLE_PROMPT_ID)
        assert data["name"] == "Financial Statement Analysis"
        assert data["description"] == "Analyzes financial statements from SEC filings"
        assert data["role"] == "system"
        assert data["content"] == "Analyze the financial statements for the company, focusing on key metrics and trends."

        # Verify the mock was called with the correct arguments
        mock_get_prompt.assert_called_once_with(SAMPLE_PROMPT_ID)

    @patch("src.api.routes.prompts.get_prompt")
    def test_get_prompt_by_id_not_found(self, mock_get_prompt):
        """Test retrieving a prompt by ID when it doesn't exist."""
        # Setup the mock to return None (prompt not found)
        mock_get_prompt.return_value = None

        # Make the API call
        response = client.get(f"/api/prompts/{SAMPLE_PROMPT_ID}")

        # Assertions
        assert response.status_code == 404
        assert response.json()["detail"] == f"Prompt with ID {SAMPLE_PROMPT_ID} not found"

        # Verify the mock was called with the correct arguments
        mock_get_prompt.assert_called_once_with(SAMPLE_PROMPT_ID)

    def test_get_prompt_by_id_invalid_uuid(self):
        """Test retrieving a prompt with an invalid UUID format."""
        # Test with an invalid UUID
        invalid_uuid = "not-a-valid-uuid"
        response = client.get(f"/api/prompts/{invalid_uuid}")

        # Assertions
        assert response.status_code == 422
        assert "uuid_parsing" in str(response.json())

    @patch("src.api.routes.prompts.get_prompt")
    def test_get_prompt_by_id_database_error(self, mock_get_prompt):
        """Test error handling when database operation fails."""
        # Setup the mock to raise an exception
        mock_get_prompt.side_effect = Exception("Database connection failed")

        # Make the API call
        response = client.get(f"/api/prompts/{SAMPLE_PROMPT_ID}")

        # Assertions
        assert response.status_code == 500
        assert "Internal server error while retrieving prompt" in response.json()["detail"]

        # Verify the mock was called
        mock_get_prompt.assert_called_once_with(SAMPLE_PROMPT_ID)

    @patch("src.api.routes.prompts.get_prompt")
    def test_get_prompt_by_id_value_error(self, mock_get_prompt):
        """Test error handling when UUID parsing fails."""
        # Setup the mock to raise a ValueError
        mock_get_prompt.side_effect = ValueError("Invalid UUID format")

        # Make the API call
        response = client.get(f"/api/prompts/{SAMPLE_PROMPT_ID}")

        # Assertions
        assert response.status_code == 400
        assert "Invalid UUID format" in response.json()["detail"]

        # Verify the mock was called
        mock_get_prompt.assert_called_once_with(SAMPLE_PROMPT_ID)

    @patch("src.api.routes.prompts.get_prompt")
    def test_get_prompt_by_id_with_minimal_data(self, mock_get_prompt):
        """Test retrieving a prompt with minimal required data."""
        # Setup a mock prompt with minimal data
        mock_prompt = MagicMock()
        mock_prompt.id = SAMPLE_PROMPT_ID
        mock_prompt.name = "Simple Prompt"
        mock_prompt.description = None  # Optional field
        mock_prompt.content = "Simple prompt content"

        # Mock the role enum
        mock_role = MagicMock()
        mock_role.value = "user"
        mock_prompt.role = mock_role

        mock_get_prompt.return_value = mock_prompt

        # Make the API call
        response = client.get(f"/api/prompts/{SAMPLE_PROMPT_ID}")

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(SAMPLE_PROMPT_ID)
        assert data["name"] == "Simple Prompt"
        assert data["description"] is None
        assert data["role"] == "user"
        assert data["content"] == "Simple prompt content"

        # Verify the mock was called with the correct arguments
        mock_get_prompt.assert_called_once_with(SAMPLE_PROMPT_ID)

    @patch("src.api.routes.prompts.get_prompt")
    def test_get_prompt_by_id_different_roles(self, mock_get_prompt):
        """Test retrieving prompts with different role types."""
        # Test with assistant role
        mock_prompt = create_mock_prompt()
        mock_prompt.role.value = "assistant"
        mock_get_prompt.return_value = mock_prompt

        response = client.get(f"/api/prompts/{SAMPLE_PROMPT_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "assistant"

        # Test with user role
        mock_prompt.role.value = "user"
        response = client.get(f"/api/prompts/{SAMPLE_PROMPT_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "user"
