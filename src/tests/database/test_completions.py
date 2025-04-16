import uuid
import pytest
from datetime import date
from sqlalchemy.exc import IntegrityError
from typing import Dict, Any, List

# Import the Completion model and functions
from src.ingestion.database.completions import (
    Completion,
    get_completion_ids,
    get_completion,
    create_completion,
    update_completion,
    delete_completion
)
from src.ingestion.database.documents import Document, create_document
from src.ingestion.database.prompts import Prompt, create_prompt
from src.ingestion.database.filings import Filing, create_filing
from src.ingestion.database.companies import Company, create_company
from src.ingestion.database.base import Base

# Sample company data fixture
@pytest.fixture
def sample_company_data() -> Dict[str, Any]:
    """Sample company data for testing."""
    return {
        "name": "Test Company, Inc.",
        "cik": "0000123456",
        "display_name": "Test Co",
        "is_company": True,
        "tickers": ["TEST"],
        "exchanges": ["NYSE"],
        "sic": "7370",
        "sic_description": "Services-Computer Programming, Data Processing, Etc.",
        "fiscal_year_end": date(2023, 12, 31),
        "entity_type": "Corporation",
        "ein": "12-3456789"
    }

@pytest.fixture
def create_test_company(db_session, sample_company_data):
    """Create and return a test company."""
    company = Company(**sample_company_data)
    db_session.add(company)
    db_session.commit()
    return company

# Sample filing data fixture
@pytest.fixture
def sample_filing_data(create_test_company) -> Dict[str, Any]:
    """Sample filing data for testing."""
    return {
        "company_id": create_test_company.id,
        "accession_number": "0000123456-23-000123",
        "filing_type": "10-K",
        "filing_date": date(2023, 12, 31),
        "filing_url": "https://www.sec.gov/Archives/edgar/data/123456/000012345623000123/test-10k.htm",
        "period_of_report": date(2023, 12, 31)
    }

@pytest.fixture
def create_test_filing(db_session, sample_filing_data):
    """Create and return a test filing."""
    filing = Filing(**sample_filing_data)
    db_session.add(filing)
    db_session.commit()
    return filing

# Sample document data fixture
@pytest.fixture
def sample_document_data(create_test_filing) -> Dict[str, Any]:
    """Sample document data for testing."""
    return {
        "filing_id": create_test_filing.id,
        "company_id": create_test_filing.company_id,
        "document_name": "test_10k.htm",
        "content": "This is the text content of the test 10-K document."
    }

@pytest.fixture
def create_test_document(db_session, sample_document_data):
    """Create and return a test document."""
    document = Document(**sample_document_data)
    db_session.add(document)
    db_session.commit()
    return document

@pytest.fixture
def create_multiple_documents(db_session, create_test_filing) -> List[Document]:
    """Create and return multiple test documents for the same filing."""
    documents = []

    # Create 3 test documents
    for i in range(3):
        document_data = {
            "filing_id": create_test_filing.id,
            "company_id": create_test_filing.company_id,
            "document_name": f"exhibit_{i+1}.htm",
            "content": f"This is the text content of exhibit {i+1}."
        }
        document = Document(**document_data)
        db_session.add(document)
        documents.append(document)

    db_session.commit()
    return documents

# Sample prompt data fixtures
@pytest.fixture
def sample_system_prompt_data() -> Dict[str, Any]:
    """Sample system prompt data for testing."""
    return {
        "name": "Financial Assistant System Prompt",
        "role": "system",  # Will be converted to PromptRole enum value
        "description": "Standard system prompt for financial analysis",
        "template": "You are a helpful financial assistant that provides information about companies.",
        "template_vars": [],
        "default_vars": {}
    }

@pytest.fixture
def sample_user_prompt_data() -> Dict[str, Any]:
    """Sample user prompt data for testing."""
    return {
        "name": "Financial Summary User Prompt",
        "role": "user",  # Will be converted to PromptRole enum value
        "description": "Request for financial performance summary",
        "template": "Summarize the financial performance of the company in the provided documents.",
        "template_vars": [],
        "default_vars": {}
    }

@pytest.fixture
def create_test_prompts(db_session, sample_system_prompt_data, sample_user_prompt_data):
    """Create and return system and user test prompts."""
    # Convert string roles to enum values
    from src.ingestion.database.prompts import PromptRole
    system_prompt_data = sample_system_prompt_data.copy()
    system_prompt_data["role"] = PromptRole.SYSTEM

    user_prompt_data = sample_user_prompt_data.copy()
    user_prompt_data["role"] = PromptRole.USER

    system_prompt = Prompt(**system_prompt_data)
    user_prompt = Prompt(**user_prompt_data)
    db_session.add(system_prompt)
    db_session.add(user_prompt)
    db_session.commit()
    return system_prompt, user_prompt

# Sample completion data fixtures
@pytest.fixture
def sample_completion_data(create_test_prompts) -> Dict[str, Any]:
    """Sample completion data for testing."""
    system_prompt, user_prompt = create_test_prompts
    return {
        "system_prompt_id": system_prompt.id,
        "user_prompt_id": user_prompt.id,
        "model": "gpt-4",
        "temperature": 0.7,
        "top_p": 1.0,
        "context_text": [
            {"role": "system", "content": system_prompt.template},
            {"role": "user", "content": user_prompt.template}
        ]
    }

@pytest.fixture
def sample_minimal_completion_data() -> Dict[str, Any]:
    """Sample minimal completion data with only required fields."""
    return {
        "model": "gpt-3.5-turbo",
        "context_text": [
            {"role": "user", "content": "Tell me about this company."}
        ]
    }

@pytest.fixture
def multiple_completion_data() -> List[Dict[str, Any]]:
    """Generate data for multiple completions with different models."""
    return [
        {
            "model": "gpt-4",
            "temperature": 0.8,
            "context_text": [
                {"role": "user", "content": "Analyze financial performance."}
            ]
        },
        {
            "model": "gpt-3.5-turbo",
            "temperature": 0.5,
            "context_text": [
                {"role": "user", "content": "Summarize key points."}
            ]
        },
        {
            "model": "text-davinci-003",
            "temperature": 0.3,
            "context_text": [
                {"role": "user", "content": "Extract financial metrics."}
            ]
        }
    ]

# Test cases for Completion CRUD operations
def test_create_completion(db_session, sample_completion_data):
    """Test creating a completion."""
    # Create completion
    completion = Completion(**sample_completion_data)
    db_session.add(completion)
    db_session.commit()

    # Verify it was created
    assert completion.id is not None
    assert completion.model == "gpt-4"
    assert len(completion.context_text) == 2

    # Verify it can be retrieved from the database
    retrieved = db_session.query(Completion).filter_by(id=completion.id).first()
    assert retrieved is not None
    assert retrieved.model == completion.model
    assert retrieved.temperature == 0.7
    assert len(retrieved.context_text) == 2

def test_create_minimal_completion(db_session, sample_minimal_completion_data):
    """Test creating a completion with only required fields."""
    completion = Completion(**sample_minimal_completion_data)
    db_session.add(completion)
    db_session.commit()

    # Verify it was created with defaults
    assert completion.id is not None
    assert completion.model == "gpt-3.5-turbo"
    assert completion.temperature == 0.7  # Default from model
    assert completion.top_p == 1.0  # Default from model
    assert completion.system_prompt_id is None
    assert completion.user_prompt_id is None

def test_completion_document_relationship(db_session, sample_minimal_completion_data, create_multiple_documents):
    """Test the relationship between completions and documents."""
    # Create a completion
    completion = Completion(**sample_minimal_completion_data)

    # Associate documents with the completion
    completion.source_documents.extend(create_multiple_documents)

    db_session.add(completion)
    db_session.commit()

    # Verify the document relationships
    assert len(completion.source_documents) == 3

    # Check from the document side
    document = db_session.query(Document).filter_by(id=create_multiple_documents[0].id).first()
    assert len(document.completions) > 0
    assert document.completions[0].id == completion.id

def test_completion_prompt_relationship(db_session, sample_completion_data, create_test_prompts):
    """Test the relationship between completions and prompts."""
    system_prompt, user_prompt = create_test_prompts

    # Create a completion
    completion = Completion(**sample_completion_data)
    db_session.add(completion)
    db_session.commit()

    # Verify the prompt relationships
    assert completion.system_prompt_id == system_prompt.id
    assert completion.system_prompt.template == system_prompt.template
    assert completion.user_prompt_id == user_prompt.id
    assert completion.user_prompt.template == user_prompt.template

    # Check from the prompt side
    system = db_session.query(Prompt).filter_by(id=system_prompt.id).first()
    user = db_session.query(Prompt).filter_by(id=user_prompt.id).first()

    assert len(system.system_completions) > 0
    assert system.system_completions[0].id == completion.id

    assert len(user.user_completions) > 0
    assert user.user_completions[0].id == completion.id

def test_get_completion_by_id(db_session, sample_completion_data):
    """Test retrieving a completion by ID using the get_completion function."""
    # First create a completion
    completion = Completion(**sample_completion_data)
    db_session.add(completion)
    db_session.commit()

    # Mock the db_session global with our test session
    import src.ingestion.database.completions as completions_module
    original_get_db_session = completions_module.get_db_session
    completions_module.get_db_session = lambda: db_session

    try:
        # Test the get_completion function
        retrieved = get_completion(completion.id)
        assert retrieved is not None
        assert retrieved.id == completion.id
        assert retrieved.model == "gpt-4"

        # Test with non-existent ID
        non_existent = get_completion(uuid.uuid4())
        assert non_existent is None
    finally:
        # Restore the original function
        completions_module.get_db_session = original_get_db_session

def test_create_completion_function(db_session, sample_completion_data, create_multiple_documents):
    """Test the create_completion helper function."""
    # Mock the db_session global
    import src.ingestion.database.completions as completions_module
    original_get_db_session = completions_module.get_db_session
    completions_module.get_db_session = lambda: db_session

    try:
        # Add document IDs to the completion data
        completion_data = sample_completion_data.copy()
        completion_data['document_ids'] = [doc.id for doc in create_multiple_documents]

        # Create a completion using the helper function
        completion = create_completion(completion_data)

        # Verify it was created correctly
        assert completion.id is not None
        assert completion.model == "gpt-4"
        assert len(completion.source_documents) == 3

        # Verify it exists in the database
        retrieved = db_session.query(Completion).filter_by(id=completion.id).first()
        assert retrieved is not None
        assert retrieved.model == completion.model
        assert len(retrieved.source_documents) == 3
    finally:
        # Restore the original function
        completions_module.get_db_session = original_get_db_session

def test_update_completion(db_session, sample_completion_data):
    """Test updating a completion using the update_completion function."""
    # First create a completion
    completion = Completion(**sample_completion_data)
    db_session.add(completion)
    db_session.commit()

    # Mock the db_session global
    import src.ingestion.database.completions as completions_module
    original_get_db_session = completions_module.get_db_session
    completions_module.get_db_session = lambda: db_session

    try:
        # Update the completion
        updates = {
            "model": "gpt-4-turbo",
            "temperature": 0.5
        }

        updated = update_completion(completion.id, updates)

        # Verify updates were applied
        assert updated is not None
        assert updated.model == "gpt-4-turbo"
        assert updated.temperature == 0.5

        # Check that other fields weren't changed
        assert updated.top_p == 1.0
        assert len(updated.context_text) == 2

        # Test updating non-existent completion
        non_existent = update_completion(uuid.uuid4(), {"model": "test-model"})
        assert non_existent is None
    finally:
        # Restore the original function
        completions_module.get_db_session = original_get_db_session

def test_update_completion_documents(db_session, sample_completion_data, create_multiple_documents):
    """Test updating a completion's associated documents."""
    # First create a completion without documents
    completion = Completion(**sample_completion_data)
    db_session.add(completion)
    db_session.commit()

    # Mock the db_session global
    import src.ingestion.database.completions as completions_module
    original_get_db_session = completions_module.get_db_session
    completions_module.get_db_session = lambda: db_session

    try:
        # Update the completion with document associations
        updates = {
            "document_ids": [doc.id for doc in create_multiple_documents[:2]]  # Only associate first two documents
        }

        updated = update_completion(completion.id, updates)

        # Verify document associations were updated
        assert updated is not None
        assert len(updated.source_documents) == 2

        # Update again with different documents
        updates = {
            "document_ids": [create_multiple_documents[2].id]  # Only associate the third document
        }

        updated = update_completion(completion.id, updates)

        # Verify document associations were updated again
        assert len(updated.source_documents) == 1
        assert updated.source_documents[0].id == create_multiple_documents[2].id
    finally:
        # Restore the original function
        completions_module.get_db_session = original_get_db_session

def test_delete_completion(db_session, sample_completion_data):
    """Test deleting a completion using the delete_completion function."""
    # First create a completion
    completion = Completion(**sample_completion_data)
    db_session.add(completion)
    db_session.commit()
    completion_id = completion.id

    # Mock the db_session global
    import src.ingestion.database.completions as completions_module
    original_get_db_session = completions_module.get_db_session
    completions_module.get_db_session = lambda: db_session

    try:
        # Delete the completion
        result = delete_completion(completion_id)
        assert result is True

        # Verify it was deleted
        assert db_session.query(Completion).filter_by(id=completion_id).first() is None

        # Test deleting non-existent completion
        result = delete_completion(uuid.uuid4())
        assert result is False
    finally:
        # Restore the original function
        completions_module.get_db_session = original_get_db_session

def test_get_completion_ids(db_session, multiple_completion_data):
    """Test retrieving all completion IDs."""
    # Create multiple completions
    completion_ids = []
    for data in multiple_completion_data:
        completion = Completion(**data)
        db_session.add(completion)
        db_session.commit()
        completion_ids.append(completion.id)

    # Mock the db_session global
    import src.ingestion.database.completions as completions_module
    original_get_db_session = completions_module.get_db_session
    completions_module.get_db_session = lambda: db_session

    try:
        # Get all completion IDs
        ids = get_completion_ids()

        # Verify all created completions are included
        for completion_id in completion_ids:
            assert completion_id in ids

        # Verify count matches or exceeds (in case of existing data)
        assert len(ids) >= len(completion_ids)
    finally:
        # Restore the original function
        completions_module.get_db_session = original_get_db_session

def test_update_with_invalid_attributes(db_session, sample_completion_data):
    """Test updating a completion with invalid attributes."""
    # First create a completion
    completion = Completion(**sample_completion_data)
    db_session.add(completion)
    db_session.commit()

    # Mock the db_session global
    import src.ingestion.database.completions as completions_module
    original_get_db_session = completions_module.get_db_session
    completions_module.get_db_session = lambda: db_session

    try:
        # Update with invalid attribute
        updates = {
            "model": "gpt-4-32k",
            "invalid_field": "This field doesn't exist"
        }

        # Should still update valid fields but ignore invalid ones
        updated = update_completion(completion.id, updates)
        assert updated is not None
        assert updated.model == "gpt-4-32k"

        # The invalid field should not be added to the object
        assert not hasattr(updated, "invalid_field")
    finally:
        # Restore the original function
        completions_module.get_db_session = original_get_db_session

def test_get_completion_with_string_uuid(db_session, sample_completion_data):
    """Test retrieving a completion using string representation of UUID."""
    # First create a completion
    completion = Completion(**sample_completion_data)
    db_session.add(completion)
    db_session.commit()

    # Mock the db_session global
    import src.ingestion.database.completions as completions_module
    original_get_db_session = completions_module.get_db_session
    completions_module.get_db_session = lambda: db_session

    try:
        # Test get_completion with string UUID
        retrieved = get_completion(str(completion.id))
        assert retrieved is not None
        assert retrieved.id == completion.id
        assert retrieved.model == "gpt-4"
    finally:
        # Restore the original function
        completions_module.get_db_session = original_get_db_session

def test_delete_document_doesnt_delete_completion(db_session, sample_minimal_completion_data, create_test_document):
    """Test that deleting a document doesn't delete associated completions."""
    # Create a completion with an associated document
    completion = Completion(**sample_minimal_completion_data)
    completion.source_documents.append(create_test_document)
    db_session.add(completion)
    db_session.commit()
    completion_id = completion.id

    # Now delete the document
    db_session.delete(create_test_document)
    db_session.commit()

    # Verify that the completion still exists (just without the document)
    completion = db_session.query(Completion).filter_by(id=completion_id).first()
    assert completion is not None
    assert len(completion.source_documents) == 0

def test_delete_prompt_doesnt_delete_completion(db_session, sample_completion_data, create_test_prompts):
    """Test that deleting a prompt doesn't delete associated completions."""
    system_prompt, user_prompt = create_test_prompts

    # Create a completion
    completion = Completion(**sample_completion_data)
    db_session.add(completion)
    db_session.commit()
    completion_id = completion.id

    # Now delete both prompts
    db_session.delete(system_prompt)
    db_session.delete(user_prompt)
    db_session.commit()

    # Verify that the completion still exists (just without the prompt references)
    completion = db_session.query(Completion).filter_by(id=completion_id).first()
    assert completion is not None
    assert completion.system_prompt_id is None
    assert completion.user_prompt_id is None

def test_context_text_json_operations(db_session, sample_minimal_completion_data):
    """Test that the context_text JSON field works correctly."""
    # Create a completion
    completion = Completion(**sample_minimal_completion_data)
    db_session.add(completion)
    db_session.commit()

    # Add an item to the context_text list and flag the attribute as modified
    completion.context_text.append({"role": "assistant", "content": "I'll analyze the company for you."})
    # Use the SQLAlchemy flag_modified function to mark the JSON field as changed
    from sqlalchemy.orm import attributes
    attributes.flag_modified(completion, "context_text")
    db_session.commit()

    # Verify the item was added correctly
    retrieved = db_session.query(Completion).filter_by(id=completion.id).first()
    assert len(retrieved.context_text) == 2
    assert retrieved.context_text[1]["role"] == "assistant"
    assert retrieved.context_text[1]["content"] == "I'll analyze the company for you."

    # Update an existing item in the context_text list
    retrieved.context_text[0]["content"] = "Updated content"
    attributes.flag_modified(retrieved, "context_text")
    db_session.commit()

    # Verify the update was persisted
    updated = db_session.query(Completion).filter_by(id=completion.id).first()
    assert updated.context_text[0]["content"] == "Updated content"
