"""Tests for the prompts API endpoints."""
from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient

from src.api.main import app
from src.database.prompts import Prompt
from src.database.prompts import PromptRole as DBPromptRole

client = TestClient(app)

# Sample prompt data for tests
SAMPLE_SYSTEM_PROMPT_ID = UUID("123e4567-e89b-12d3-a456-426614174000")
SAMPLE_USER_PROMPT_ID = UUID("123e4567-e89b-12d3-a456-426614174001")

SAMPLE_SYSTEM_PROMPT = {
    "id": SAMPLE_SYSTEM_PROMPT_ID,
    "name": "Company Analysis",
    "description": "System prompt for analyzing companies",
    "role": DBPromptRole.SYSTEM,
    "content": "You are a financial analyst assistant. Analyze the company."
}

SAMPLE_USER_PROMPT = {
    "id": SAMPLE_USER_PROMPT_ID,
    "name": "Financial Metrics Request",
    "description": "User prompt requesting financial metrics",
    "role": DBPromptRole.USER,
    "content": "Provide key financial metrics for the company in the requested time period."
}


@patch("src.api.routes.prompts.prompts_db.get_db_session")
@patch("src.api.routes.prompts.prompts_db.Prompt")
def test_get_prompts_by_role_system(mock_prompt_model, mock_get_session):
    """Test retrieving system prompts."""
    # Setup mock session and query
    mock_session = mock_get_session.return_value
    mock_query = mock_session.query.return_value
    mock_filter = mock_query.filter.return_value

    # Setup the mock to return our sample system prompts
    sample_system_prompt = Prompt()
    sample_system_prompt.id = SAMPLE_SYSTEM_PROMPT_ID
    sample_system_prompt.name = "Company Analysis"
    sample_system_prompt.description = "System prompt for analyzing companies"
    sample_system_prompt.role = DBPromptRole.SYSTEM
    sample_system_prompt.content = "You are a financial analyst assistant. Analyze the company."

    mock_filter.all.return_value = [sample_system_prompt]

    # Make the API call
    response = client.get("/api/prompts/by-role/system")

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(SAMPLE_SYSTEM_PROMPT_ID)
    assert data[0]["name"] == "Company Analysis"
    assert data[0]["role"] == "system"

    # Verify the mock was called with the correct arguments
    mock_session.query.assert_called_once_with(mock_prompt_model)
    mock_query.filter.assert_called_once()


@patch("src.api.routes.prompts.prompts_db.get_db_session")
@patch("src.api.routes.prompts.prompts_db.Prompt")
def test_get_prompts_by_role_user(mock_prompt_model, mock_get_session):
    """Test retrieving user prompts."""
    # Setup mock session and query
    mock_session = mock_get_session.return_value
    mock_query = mock_session.query.return_value
    mock_filter = mock_query.filter.return_value

    # Setup the mock to return our sample user prompts
    sample_user_prompt = Prompt()
    sample_user_prompt.id = SAMPLE_USER_PROMPT_ID
    sample_user_prompt.name = "Financial Metrics Request"
    sample_user_prompt.description = "User prompt requesting financial metrics"
    sample_user_prompt.role = DBPromptRole.USER
    sample_user_prompt.content = "Provide key financial metrics for the company in the requested time period."

    mock_filter.all.return_value = [sample_user_prompt]

    # Make the API call
    response = client.get("/api/prompts/by-role/user")

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(SAMPLE_USER_PROMPT_ID)
    assert data[0]["name"] == "Financial Metrics Request"
    assert data[0]["role"] == "user"

    # Verify the mock was called with the correct arguments
    mock_session.query.assert_called_once_with(mock_prompt_model)
    mock_query.filter.assert_called_once()


@patch("src.api.routes.prompts.prompts_db.get_db_session")
@patch("src.api.routes.prompts.prompts_db.Prompt")
def test_get_prompts_by_role_empty(mock_prompt_model, mock_get_session):
    """Test retrieving prompts when none exist for the given role."""
    # Setup mock session and query
    mock_session = mock_get_session.return_value
    mock_query = mock_session.query.return_value
    mock_filter = mock_query.filter.return_value

    # Setup the mock to return an empty list
    mock_filter.all.return_value = []

    # Make the API call
    response = client.get("/api/prompts/by-role/assistant")

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0

    # Verify the mock was called with the correct arguments
    mock_session.query.assert_called_once_with(mock_prompt_model)
    mock_query.filter.assert_called_once()


@patch("src.api.routes.prompts.prompts_db.get_db_session")
@patch("src.api.routes.prompts.prompts_db.Prompt")
def test_get_prompts_by_role_exception(mock_prompt_model, mock_get_session):
    """Test error handling when database query fails."""
    # Setup mock session to raise an exception
    mock_session = mock_get_session.return_value
    mock_query = mock_session.query.return_value
    mock_query.filter.side_effect = Exception("Database connection error")

    # Make the API call
    response = client.get("/api/prompts/by-role/system")

    # Assertions
    assert response.status_code == 500
    assert "Failed to retrieve prompts" in response.json()["detail"]

    # Verify the mock was called with the correct arguments
    mock_session.query.assert_called_once_with(mock_prompt_model)


@patch("src.api.routes.prompts.prompts_db.create_prompt")
def test_create_prompt_success(mock_create_prompt):
    """Test successfully creating a new prompt."""
    # Setup the mock to return a new prompt
    new_prompt = Prompt()
    new_prompt.id = UUID("123e4567-e89b-12d3-a456-426614174002")
    new_prompt.name = "New Test Prompt"
    new_prompt.description = "A test prompt for testing"
    new_prompt.role = DBPromptRole.SYSTEM
    new_prompt.content = "Test content for the new prompt"

    mock_create_prompt.return_value = new_prompt

    # Create prompt request body
    request_data = {
        "name": "New Test Prompt",
        "description": "A test prompt for testing",
        "role": "system",
        "content": "Test content for the new prompt"
    }

    # Make the API call
    response = client.post("/api/prompts/", json=request_data)

    # Assertions
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == str(new_prompt.id)
    assert data["name"] == "New Test Prompt"
    assert data["role"] == "system"

    # Verify create_prompt was called with the correct data
    mock_create_prompt.assert_called_once()
    call_arg = mock_create_prompt.call_args[0][0]
    assert call_arg["name"] == "New Test Prompt"
    assert call_arg["content"] == "Test content for the new prompt"


@patch("src.api.routes.prompts.prompts_db.create_prompt")
def test_create_prompt_value_error(mock_create_prompt):
    """Test error handling for validation errors when creating a prompt."""
    # Setup the mock to raise a ValueError
    mock_create_prompt.side_effect = ValueError("Invalid prompt data")

    # Create prompt request body with invalid data
    request_data = {
        "name": "Invalid Prompt",
        "description": "A prompt with invalid data",
        "role": "system",
        "content": "Content with {variable1}"
    }

    # Make the API call
    response = client.post("/api/prompts/", json=request_data)

    # Assertions
    assert response.status_code == 400
    assert "Invalid prompt data" in response.json()["detail"]


@patch("src.api.routes.prompts.prompts_db.create_prompt")
def test_create_prompt_integrity_error(mock_create_prompt):
    """Test error handling for integrity errors when creating a prompt."""
    # Import IntegrityError here to avoid circular import in the main file
    from sqlalchemy.exc import IntegrityError

    # Setup the mock to raise an IntegrityError
    mock_create_prompt.side_effect = IntegrityError("statement", {}, "duplicate key value")

    # Create prompt request body
    request_data = {
        "name": "Duplicate Prompt",
        "description": "A prompt that already exists",
        "role": "system",
        "content": "Duplicate content"
    }

    # Make the API call
    response = client.post("/api/prompts/", json=request_data)

    # Assertions
    assert response.status_code == 409
    assert "Prompt already exists" in response.json()["detail"]


@patch("src.api.routes.prompts.prompts_db.create_prompt")
def test_create_prompt_exception(mock_create_prompt):
    """Test error handling for general exceptions when creating a prompt."""
    # Setup the mock to raise a general exception
    mock_create_prompt.side_effect = Exception("Unexpected database error")

    # Create prompt request body
    request_data = {
        "name": "Error Prompt",
        "description": "A prompt that causes an error",
        "role": "system",
        "content": "Error content"
    }

    # Make the API call
    response = client.post("/api/prompts/", json=request_data)

    # Assertions
    assert response.status_code == 500
    assert "Failed to create prompt" in response.json()["detail"]