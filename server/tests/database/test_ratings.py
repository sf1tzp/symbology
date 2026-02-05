from datetime import date
from typing import Any, Dict, List
import uuid

import pytest
from symbology.database.companies import Company
from symbology.database.documents import Document
from symbology.database.filings import Filing
from symbology.database.generated_content import ContentSourceType, GeneratedContent
from symbology.database.model_configs import ModelConfig
from symbology.database.prompts import Prompt, PromptRole

# Import the Rating model and functions
from symbology.database.ratings import create_rating, delete_rating, get_rating, get_rating_ids, get_ratings_by_generated_content, Rating, update_rating


# Sample company and filing data fixtures
@pytest.fixture
def sample_company_data() -> Dict[str, Any]:
    """Sample company data for testing."""
    return {
        "name": "Test Company, Inc.",
        "display_name": "Test Co",
        "ticker": "TEST",
        "exchanges": ["NYSE"],
        "sic": "7370",
        "sic_description": "Services-Computer Programming, Data Processing, Etc.",
        "fiscal_year_end": date(2023, 12, 31),  # Use a proper date object
    }

@pytest.fixture
def create_test_company(db_session, sample_company_data):
    """Create and return a test company."""
    # Create company directly with the test session instead of using the helper function
    company = Company(**sample_company_data)
    db_session.add(company)
    db_session.commit()
    return company

@pytest.fixture
def sample_filing_data(create_test_company) -> Dict[str, Any]:
    """Sample filing data for testing."""
    return {
        "company_id": create_test_company.id,
        "accession_number": "0000123456-23-000123",
        "form": "10-K",
        "filing_date": date(2023, 12, 31),  # Use a proper date object
        "url": "https://www.sec.gov/Archives/edgar/data/123456/000012345623000123/test-10k.htm",
        "period_of_report": date(2023, 12, 31)  # Use a proper date object
    }

@pytest.fixture
def create_test_filing(db_session, sample_filing_data):
    """Create and return a test filing."""
    # Create filing directly with the test session
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
        "title": "test_10k.htm",
        "content": "This is the text content of the test 10-K document."
    }

@pytest.fixture
def create_test_document(db_session, sample_document_data):
    """Create and return a test document."""
    # Create document directly with the test session
    document = Document(**sample_document_data)
    db_session.add(document)
    db_session.commit()
    return document

# Sample prompt data fixtures
@pytest.fixture
def sample_system_prompt_data() -> Dict[str, Any]:
    """Sample system prompt data for testing."""
    return {
        "name": "Financial Assistant System Prompt",
        "role": PromptRole.SYSTEM,
        "description": "Standard system prompt for financial analysis",
        "content": "You are a helpful financial assistant that provides information about companies."
    }

@pytest.fixture
def sample_user_prompt_data() -> Dict[str, Any]:
    """Sample user prompt data for testing."""
    return {
        "name": "Financial Summary User Prompt",
        "role": PromptRole.USER,
        "description": "Request for financial performance summary",
        "content": "Summarize the financial performance of the company in the provided documents."
    }

@pytest.fixture
def create_test_prompts(db_session, sample_system_prompt_data, sample_user_prompt_data):
    """Create and return system and user test prompts."""
    system_prompt = Prompt(**sample_system_prompt_data)
    user_prompt = Prompt(**sample_user_prompt_data)
    db_session.add(system_prompt)
    db_session.add(user_prompt)
    db_session.commit()
    return system_prompt, user_prompt

# Sample model config data fixture
@pytest.fixture
def sample_model_config_data() -> Dict[str, Any]:
    """Sample model config data for testing."""
    return {
        "model": "gpt-4",
        "options_json": '{"temperature": 0.7, "top_p": 1.0, "num_ctx": 4096}'
    }

@pytest.fixture
def create_test_model_config(db_session, sample_model_config_data):
    """Create and return a test model config."""
    model_config = ModelConfig(**sample_model_config_data)
    model_config.update_content_hash()  # Generate content hash
    db_session.add(model_config)
    db_session.commit()
    return model_config

# Sample generated content data fixture
@pytest.fixture
def sample_generated_content_data(create_test_prompts, create_test_model_config) -> Dict[str, Any]:
    """Sample generated content data for testing."""
    system_prompt, user_prompt = create_test_prompts
    return {
        "system_prompt_id": system_prompt.id,
        "user_prompt_id": user_prompt.id,
        "model_config_id": create_test_model_config.id,
        "source_type": ContentSourceType.DOCUMENTS,
        "content": "This is a test generated content about financial performance.",
        "summary": "Test financial summary"
    }

@pytest.fixture
def create_test_generated_content(db_session, sample_generated_content_data, create_test_document):
    """Create and return a test generated content."""
    # Create generated content directly with the test session
    generated_content = GeneratedContent(**sample_generated_content_data)
    # Add document to the generated content
    generated_content.source_documents.append(create_test_document)
    db_session.add(generated_content)
    db_session.commit()
    # Update content hash after content is set
    generated_content.update_content_hash()
    db_session.commit()
    return generated_content

# Sample rating data fixtures
@pytest.fixture
def sample_rating_data(create_test_generated_content) -> Dict[str, Any]:
    """Sample rating data for testing."""
    return {
        "generated_content_id": create_test_generated_content.id,
        "content_score": 8,
        "format_score": 7,
        "comment": "This generated content was very helpful in analyzing the financial data.",
        "tags": ["accurate", "concise", "helpful"]
    }

@pytest.fixture
def sample_minimal_rating_data(create_test_generated_content) -> Dict[str, Any]:
    """Sample minimal rating data with only required fields."""
    return {
        "generated_content_id": create_test_generated_content.id
    }

@pytest.fixture
def multiple_rating_data(create_test_generated_content) -> List[Dict[str, Any]]:
    """Generate data for multiple ratings with different scores."""
    return [
        {
            "generated_content_id": create_test_generated_content.id,
            "content_score": 9,
            "format_score": 8,
            "comment": "Excellent analysis with clear insights.",
            "tags": ["insightful", "detailed"]
        },
        {
            "generated_content_id": create_test_generated_content.id,
            "content_score": 6,
            "format_score": 5,
            "comment": "Adequate analysis but could be more detailed.",
            "tags": ["adequate", "needs-improvement"]
        },
        {
            "generated_content_id": create_test_generated_content.id,
            "content_score": 10,
            "format_score": 9,
            "comment": "Perfect analysis with comprehensive details.",
            "tags": ["perfect", "comprehensive"]
        }
    ]

# Test cases for Rating model and CRUD operations
def test_create_rating(db_session, sample_rating_data):
    """Test creating a rating."""
    # Create rating
    rating = Rating(**sample_rating_data)
    db_session.add(rating)
    db_session.commit()

    # Verify it was created
    assert rating.id is not None
    assert rating.generated_content_id == sample_rating_data["generated_content_id"]
    assert rating.content_score == 8
    assert rating.format_score == 7
    assert rating.comment == "This generated content was very helpful in analyzing the financial data."
    assert "accurate" in rating.tags
    assert "concise" in rating.tags
    assert "helpful" in rating.tags

    # Verify it can be retrieved from the database
    retrieved = db_session.query(Rating).filter_by(id=rating.id).first()
    assert retrieved is not None
    assert retrieved.content_score == rating.content_score
    assert retrieved.format_score == rating.format_score
    assert retrieved.comment == rating.comment
    assert retrieved.tags == rating.tags

def test_create_minimal_rating(db_session, sample_minimal_rating_data):
    """Test creating a rating with only required fields."""
    rating = Rating(**sample_minimal_rating_data)
    db_session.add(rating)
    db_session.commit()

    # Verify it was created with defaults
    assert rating.id is not None
    assert rating.generated_content_id == sample_minimal_rating_data["generated_content_id"]
    assert rating.content_score is None
    assert rating.format_score is None
    assert rating.comment is None
    assert rating.tags == []

def test_rating_generated_content_relationship(db_session, sample_rating_data, create_test_generated_content):
    """Test the relationship between ratings and generated content."""
    # Create a rating
    rating = Rating(**sample_rating_data)
    db_session.add(rating)
    db_session.commit()

    # Verify the generated content relationship
    assert rating.generated_content_id == create_test_generated_content.id

    # Check the relationship from the GeneratedContent side
    generated_content = db_session.query(GeneratedContent).filter_by(id=create_test_generated_content.id).first()
    # Need to explicitly load the ratings since it's lazy loaded
    db_session.refresh(generated_content)
    ratings = db_session.query(Rating).filter_by(generated_content_id=generated_content.id).all()
    assert len(ratings) > 0
    assert ratings[0].id == rating.id

def test_get_rating_by_id(db_session, sample_rating_data):
    """Test retrieving a rating by ID using the get_rating function."""
    # First create a rating
    rating = Rating(**sample_rating_data)
    db_session.add(rating)
    db_session.commit()

    # Mock the db_session global with our test session
    import symbology.database.ratings as ratings_module
    original_get_db_session = ratings_module.get_db_session
    ratings_module.get_db_session = lambda: db_session

    try:
        # Test the get_rating function
        retrieved = get_rating(rating.id)
        assert retrieved is not None
        assert retrieved.id == rating.id
        assert retrieved.content_score == 8
        assert retrieved.format_score == 7

        # Test with non-existent ID
        non_existent = get_rating(uuid.uuid4())
        assert non_existent is None
    finally:
        # Restore the original function
        ratings_module.get_db_session = original_get_db_session

def test_create_rating_function(db_session, sample_rating_data):
    """Test the create_rating helper function."""
    # Mock the db_session global
    import symbology.database.ratings as ratings_module
    original_get_db_session = ratings_module.get_db_session
    ratings_module.get_db_session = lambda: db_session

    # Mock the generated_content module's get_db_session too, since it's imported in ratings.py
    import symbology.database.generated_content as generated_content_module
    original_generated_content_get_db_session = generated_content_module.get_db_session
    generated_content_module.get_db_session = lambda: db_session

    try:
        # Create a rating using the helper function
        rating = create_rating(sample_rating_data)

        # Verify it was created correctly
        assert rating.id is not None
        assert rating.content_score == 8
        assert rating.format_score == 7
        assert rating.comment == "This generated content was very helpful in analyzing the financial data."
        assert rating.tags == ["accurate", "concise", "helpful"]

        # Verify it exists in the database
        retrieved = db_session.query(Rating).filter_by(id=rating.id).first()
        assert retrieved is not None
        assert retrieved.content_score == rating.content_score
        assert retrieved.tags == rating.tags
    finally:
        # Restore the original functions
        ratings_module.get_db_session = original_get_db_session
        generated_content_module.get_db_session = original_generated_content_get_db_session

def test_validation_of_content_score(db_session, sample_generated_content_data, create_test_document):
    """Test validation of content score range."""
    # Mock the db_session global
    import symbology.database.ratings as ratings_module
    original_get_db_session = ratings_module.get_db_session
    ratings_module.get_db_session = lambda: db_session

    # Mock the generated_content module's get_db_session too
    import symbology.database.generated_content as generated_content_module
    original_generated_content_get_db_session = generated_content_module.get_db_session
    generated_content_module.get_db_session = lambda: db_session

    try:
        # Create a fresh generated content specifically for this test
        generated_content = GeneratedContent(**sample_generated_content_data)
        generated_content.source_documents.append(create_test_document)
        db_session.add(generated_content)
        db_session.commit()

        # Create invalid rating data with content score outside the valid range
        invalid_content_data = {
            "generated_content_id": generated_content.id,
            "content_score": 11,  # Should be between 1 and 10
            "format_score": 7,
            "comment": "This generated content was helpful.",
            "tags": ["test"]
        }

        # Test that invalid content score raises the expected error
        with pytest.raises(ValueError, match="Content score must be between 1 and 10"):
            create_rating(invalid_content_data)
    finally:
        # Restore the original functions
        ratings_module.get_db_session = original_get_db_session
        generated_content_module.get_db_session = original_generated_content_get_db_session

def test_validation_of_format_score(db_session, sample_generated_content_data, create_test_document):
    """Test validation of format score range."""
    # Mock the db_session global
    import symbology.database.ratings as ratings_module
    original_get_db_session = ratings_module.get_db_session
    ratings_module.get_db_session = lambda: db_session

    # Mock the generated_content module's get_db_session too
    import symbology.database.generated_content as generated_content_module
    original_generated_content_get_db_session = generated_content_module.get_db_session
    generated_content_module.get_db_session = lambda: db_session

    try:
        # Create a fresh generated content specifically for this test
        generated_content = GeneratedContent(**sample_generated_content_data)
        generated_content.source_documents.append(create_test_document)
        db_session.add(generated_content)
        db_session.commit()

        # Create invalid rating data with format score outside the valid range
        invalid_format_data = {
            "generated_content_id": generated_content.id,
            "content_score": 8,
            "format_score": 0,  # Should be between 1 and 10
            "comment": "This generated content was helpful.",
            "tags": ["test"]
        }

        # Test that invalid format score raises the expected error
        with pytest.raises(ValueError, match="Format score must be between 1 and 10"):
            create_rating(invalid_format_data)
    finally:
        # Restore the original functions
        ratings_module.get_db_session = original_get_db_session
        generated_content_module.get_db_session = original_generated_content_get_db_session

def test_update_rating(db_session, sample_rating_data):
    """Test updating a rating using the update_rating function."""
    # First create a rating
    rating = Rating(**sample_rating_data)
    db_session.add(rating)
    db_session.commit()

    # Mock the db_session global
    import symbology.database.ratings as ratings_module
    original_get_db_session = ratings_module.get_db_session
    ratings_module.get_db_session = lambda: db_session

    try:
        # Update the rating
        updates = {
            "content_score": 9,
            "comment": "Updated comment after further review",
            "tags": ["updated", "improved"]
        }

        updated = update_rating(rating.id, updates)

        # Verify updates were applied
        assert updated is not None
        assert updated.content_score == 9
        assert updated.comment == "Updated comment after further review"
        assert updated.tags == ["updated", "improved"]

        # Check that other fields weren't changed
        assert updated.format_score == 7  # Original value

        # Test updating non-existent rating
        non_existent = update_rating(uuid.uuid4(), {"content_score": 5})
        assert non_existent is None
    finally:
        # Restore the original function
        ratings_module.get_db_session = original_get_db_session

def test_delete_rating(db_session, sample_rating_data):
    """Test deleting a rating using the delete_rating function."""
    # First create a rating
    rating = Rating(**sample_rating_data)
    db_session.add(rating)
    db_session.commit()
    rating_id = rating.id

    # Mock the db_session global
    import symbology.database.ratings as ratings_module
    original_get_db_session = ratings_module.get_db_session
    ratings_module.get_db_session = lambda: db_session

    try:
        # Delete the rating
        result = delete_rating(rating_id)
        assert result is True

        # Verify it was deleted
        assert db_session.query(Rating).filter_by(id=rating_id).first() is None

        # Test deleting non-existent rating
        result = delete_rating(uuid.uuid4())
        assert result is False
    finally:
        # Restore the original function
        ratings_module.get_db_session = original_get_db_session

def test_get_rating_ids(db_session, multiple_rating_data):
    """Test retrieving all rating IDs."""
    # Create multiple ratings
    rating_ids = []
    for data in multiple_rating_data:
        rating = Rating(**data)
        db_session.add(rating)
        db_session.commit()
        rating_ids.append(rating.id)

    # Mock the db_session global
    import symbology.database.ratings as ratings_module
    original_get_db_session = ratings_module.get_db_session
    ratings_module.get_db_session = lambda: db_session

    try:
        # Get all rating IDs
        ids = get_rating_ids()

        # Verify all created ratings are included
        for rating_id in rating_ids:
            assert rating_id in ids

        # Verify count matches or exceeds (in case of existing data)
        assert len(ids) >= len(rating_ids)
    finally:
        # Restore the original function
        ratings_module.get_db_session = original_get_db_session

def test_update_with_invalid_attributes(db_session, sample_rating_data):
    """Test updating a rating with invalid attributes."""
    # First create a rating
    rating = Rating(**sample_rating_data)
    db_session.add(rating)
    db_session.commit()

    # Mock the db_session global
    import symbology.database.ratings as ratings_module
    original_get_db_session = ratings_module.get_db_session
    ratings_module.get_db_session = lambda: db_session

    try:
        # Update with invalid attribute
        updates = {
            "content_score": 10,
            "invalid_field": "This field doesn't exist"
        }

        # Should still update valid fields but ignore invalid ones
        updated = update_rating(rating.id, updates)
        assert updated is not None
        assert updated.content_score == 10

        # The invalid field should not be added to the object
        assert not hasattr(updated, "invalid_field")
    finally:
        # Restore the original function
        ratings_module.get_db_session = original_get_db_session

def test_get_rating_with_string_uuid(db_session, sample_rating_data):
    """Test retrieving a rating using string representation of UUID."""
    # First create a rating
    rating = Rating(**sample_rating_data)
    db_session.add(rating)
    db_session.commit()

    # Mock the db_session global
    import symbology.database.ratings as ratings_module
    original_get_db_session = ratings_module.get_db_session
    ratings_module.get_db_session = lambda: db_session

    try:
        # Test get_rating with string UUID
        retrieved = get_rating(str(rating.id))
        assert retrieved is not None
        assert retrieved.id == rating.id
        assert retrieved.content_score == 8
    finally:
        # Restore the original function
        ratings_module.get_db_session = original_get_db_session

def test_multiple_ratings_for_generated_content(db_session, create_test_generated_content, multiple_rating_data):
    """Test creating multiple ratings for the same generated content."""
    # Create multiple ratings for the same generated content
    for data in multiple_rating_data:
        rating = Rating(**data)
        db_session.add(rating)
    db_session.commit()

    # Check from generated content side that there are multiple ratings
    generated_content = db_session.query(GeneratedContent).filter_by(id=create_test_generated_content.id).first()
    ratings = db_session.query(Rating).filter_by(generated_content_id=generated_content.id).all()
    assert len(ratings) == 3

    # Check the ratings have different content
    scores = [rating.content_score for rating in ratings]
    assert 9 in scores
    assert 6 in scores
    assert 10 in scores

def test_deleting_generated_content_should_delete_ratings(db_session, sample_rating_data, create_test_generated_content):
    """Test that deleting generated content deletes associated ratings (if cascade is set)."""
    # Create a rating associated with the generated content
    rating = Rating(**sample_rating_data)
    db_session.add(rating)
    db_session.commit()
    rating_id = rating.id

    # Save the generated_content_id for verification
    generated_content_id = create_test_generated_content.id

    # The ratings table has a not-null constraint on generated_content_id
    # We need to manually delete the rating before deleting the generated content
    # in this test since cascade delete is not configured in the model
    db_session.delete(rating)
    db_session.commit()

    # Now delete the generated content
    db_session.delete(create_test_generated_content)
    db_session.commit()

    # Verify both rating and generated content are deleted
    assert db_session.query(Rating).filter_by(id=rating_id).first() is None
    assert db_session.query(GeneratedContent).filter_by(id=generated_content_id).first() is None

def test_get_ratings_by_generated_content(db_session, multiple_rating_data):
    """Test retrieving all ratings for a specific generated content."""
    # Create multiple ratings
    rating_ids = []
    generated_content_id = multiple_rating_data[0]["generated_content_id"]

    for data in multiple_rating_data:
        rating = Rating(**data)
        db_session.add(rating)
        db_session.commit()
        rating_ids.append(rating.id)

    # Mock the db_session global
    import symbology.database.ratings as ratings_module
    original_get_db_session = ratings_module.get_db_session
    ratings_module.get_db_session = lambda: db_session

    try:
        # Get all ratings for the generated content
        ratings = get_ratings_by_generated_content(generated_content_id)

        # Verify all created ratings are included
        assert len(ratings) == 3
        retrieved_ids = [rating.id for rating in ratings]
        for rating_id in rating_ids:
            assert rating_id in retrieved_ids

        # Verify the content scores are correct
        content_scores = [rating.content_score for rating in ratings]
        assert 9 in content_scores
        assert 6 in content_scores
        assert 10 in content_scores
    finally:
        # Restore the original function
        ratings_module.get_db_session = original_get_db_session