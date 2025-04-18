"""Tests for the completions API routes."""
from unittest.mock import patch
import uuid

from fastapi.testclient import TestClient

from src.api.main import app
from src.database.completions import Completion
from src.database.documents import Document

client = TestClient(app)


@patch("src.api.routes.completions.get_completion_ids")
def test_get_all_completion_ids(mock_get_completion_ids):
    """Test getting all completion IDs."""
    # Setup the mock to return our sample IDs
    test_uuids = [
        uuid.UUID('06802a9f-9c9b-7bfe-8000-5465af31c25f'),
        uuid.UUID('06802a9f-9c9b-7d10-8000-bcdc085cc4cb'),
        uuid.UUID('06802a9f-9c9b-7d58-8000-b6689fb9ed7e')
    ]
    mock_get_completion_ids.return_value = test_uuids

    response = client.get("/api/completions/")
    assert response.status_code == 200
    assert len(response.json()) == 3

    # Make sure the returned UUIDs match what we set in our mock
    returned_uuids = [uuid.UUID(str(uuid_str)) for uuid_str in response.json()]
    for test_uuid in test_uuids:
        assert test_uuid in returned_uuids


@patch("src.api.routes.completions.get_completions_by_document")
def test_get_completion_by_document_id(mock_get_completions_by_document):
    """Test getting completions filtered by document ID."""
    # Instead of trying to create UUIDs from strings, use proper UUID objects
    test_doc_id_a = uuid.UUID('574441ac-2d04-45b0-bf11-288e9c3db99a')
    test_comp_id_a1 = uuid.UUID('574441ac-2d04-45b0-bf11-288e9c3da99a')
    test_comp_id_a2 = uuid.UUID('574441ac-2d04-45b0-bf11-288e9c3da99b')

    test_doc_id_b = uuid.UUID('574441ac-2d04-45b0-bf11-288e9c3db99b')
    test_comp_id_b = uuid.UUID('574441ac-2d04-45b0-bf11-288e9c3da99c')

    # Set up different return values for different document IDs
    def get_completions_side_effect(doc_id):
        if str(doc_id).endswith("a"):
            return [
                # For document ID ending in a
                Completion(
                    id=test_comp_id_a1,
                    model="gpt-4",
                    context_text=[{"role": "user", "content": "Test"}],
                    source_documents=[Document(id=test_doc_id_a)]
                ),
                # For document ID ending in a, add a second completion
                Completion(
                    id=test_comp_id_a2,
                    model="gpt-4-turbo",
                    context_text=[{"role": "user", "content": "Another test"}],
                    source_documents=[Document(id=test_doc_id_a)]
                )
            ]
        else:
            return [
                # For all other document IDs
                Completion(
                    id=test_comp_id_b,
                    model="gpt-3.5-turbo",
                    context_text=[{"role": "user", "content": "Single result test"}],
                    source_documents=[Document(id=test_doc_id_b)]
                )
            ]

    mock_get_completions_by_document.side_effect = get_completions_side_effect

    # Test with document ID that returns multiple completions
    response = client.get(f"/api/completions/?document_id={test_doc_id_a}")

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert str(test_comp_id_a1) in [str(uuid_str) for uuid_str in response.json()]
    assert str(test_comp_id_a2) in [str(uuid_str) for uuid_str in response.json()]

    # Test with document ID that returns a single completion
    response = client.get(f"/api/completions/?document_id={test_doc_id_b}")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert str(test_comp_id_b) in [str(uuid_str) for uuid_str in response.json()]

    # Verify the database function was called with the correct document ID
    last_call = mock_get_completions_by_document.call_args_list[-1]
    assert last_call[0][0] == test_doc_id_b


@patch("src.api.routes.completions.get_completion")
def test_get_completion_by_id(mock_get_completion):
    """Test getting a completion by ID."""
    # Use proper UUID objects
    test_id_1 = uuid.UUID('123e4567-e89b-12d3-a456-426614174000')
    test_id_2 = uuid.UUID('123e4567-e89b-12d3-a456-426614174001')
    test_id_3 = uuid.UUID('123e4567-e89b-12d3-a456-426614174003')
    test_id_4 = uuid.UUID('123e4567-e89b-12d3-a456-426614174004')
    test_id_5 = uuid.UUID('123e4567-e89b-12d3-a456-426614174005')

    # Define a side effect to support different completion IDs
    def get_completion_side_effect(completion_id):
        if completion_id == test_id_1:
            return Completion(
                id=test_id_1,
                system_prompt_id=test_id_3,
                user_prompt_id=test_id_4,
                model="gpt-4",
                temperature=0.7,
                top_p=1.0,
                context_text=[{"role": "user", "content": "Test completion"}],
                source_documents=[Document(id=test_id_5)]
            )
        elif completion_id == test_id_2:
            return Completion(
                id=test_id_2,
                model="gpt-3.5-turbo",
                context_text=[{"role": "user", "content": "Another test"}],
                source_documents=[]  # No source documents
            )
        return None  # Not found

    mock_get_completion.side_effect = get_completion_side_effect

    # Test with valid ID
    response = client.get(f"/api/completions/{test_id_1}")

    assert response.status_code == 200
    assert response.json()["id"] == str(test_id_1)
    assert response.json()["model"] == "gpt-4"
    assert len(response.json()["source_documents"]) == 1

    # Test with ID that has no source documents
    response = client.get(f"/api/completions/{test_id_2}")

    assert response.status_code == 200
    assert response.json()["id"] == str(test_id_2)
    assert response.json()["model"] == "gpt-3.5-turbo"
    assert response.json()["source_documents"] == []

    # Test with non-existent ID
    non_existent_id = uuid.UUID('123e4567-e89b-12d3-a456-426614174999')
    response = client.get(f"/api/completions/{non_existent_id}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@patch("src.api.routes.completions.create_completion")
def test_create_completion(mock_create_completion):
    """Test creating a new completion."""
    test_id_3 = uuid.UUID('123e4567-e89b-12d3-a456-426614174003')
    test_id_4 = uuid.UUID('123e4567-e89b-12d3-a456-426614174004')
    test_id_5 = uuid.UUID('123e4567-e89b-12d3-a456-426614174005')
    test_id_6 = uuid.UUID('123e4567-e89b-12d3-a456-426614174006')

    mock_create_completion.return_value = Completion(
        id=test_id_6,
        system_prompt_id=test_id_3,
        user_prompt_id=test_id_4,
        model="gpt-4",
        temperature=0.8,
        top_p=1.0,
        context_text=[{"role": "user", "content": "New test completion"}],
        source_documents=[Document(id=test_id_5)]
    )

    request_data = {
        "system_prompt_id": str(test_id_3),
        "user_prompt_id": str(test_id_4),
        "document_ids": [str(test_id_5)],
        "context_text": [{"role": "user", "content": "New test completion"}],
        "model": "gpt-4",
        "temperature": 0.8
    }

    response = client.post("/api/completions/", json=request_data)

    assert response.status_code == 201
    assert response.json()["id"] == str(test_id_6)
    assert response.json()["model"] == "gpt-4"
    assert response.json()["temperature"] == 0.8
    assert len(response.json()["source_documents"]) == 1

    # Verify create_completion was called with the correct data
    mock_create_completion.assert_called_once()
    call_arg = mock_create_completion.call_args[0][0]
    assert call_arg["model"] == "gpt-4"
    assert call_arg["temperature"] == 0.8
    # The document_ids should be converted to UUID objects
    assert call_arg["document_ids"][0] == test_id_5


def test_invalid_uuid_format():
    """Test providing invalid UUID formats returns a 400 Bad Request."""
    # Test with an invalid completion_id in the URL path
    invalid_uuid = "not-a-valid-uuid"
    response = client.get(f"/api/completions/{invalid_uuid}")

    assert response.status_code == 422
    assert "uuid_parsing" in str(response.json())

    # Test with an invalid document_id in the query parameter
    response = client.get(f"/api/completions/?document_id={invalid_uuid}")

    assert response.status_code == 422
    assert "uuid_parsing" in str(response.json())

    # Test with invalid UUIDs in the request body
    invalid_request_data = {
        "system_prompt_id": "not-a-valid-uuid",
        "user_prompt_id": "another-invalid-uuid",
        "document_ids": ["not-a-valid-doc-uuid"],
        "context_text": [{"role": "user", "content": "Test with invalid UUIDs"}],
        "model": "gpt-4",
        "temperature": 0.7
    }

    response = client.post("/api/completions/", json=invalid_request_data)

    assert response.status_code == 422
    assert "uuid_parsing" in str(response.json())