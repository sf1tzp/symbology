import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from src.ingestion.database import crud_ai_completion, models
from src.ingestion.database.base import Base, engine
from sqlalchemy.exc import IntegrityError
from src.ingestion.database import crud_company, crud_filing


@pytest.fixture
def db(db_session):
    """Alias for db_session to match the parameter names used in tests."""
    return db_session


@pytest.fixture
def db_company(db):
    """Create a test company in the database."""
    company_data = {
        "cik": 1234567,
        "name": "Test Company Inc.",
        "tickers": ["TEST", "TSTC"],
        "exchanges": ["NYSE"],
        "sic": "7370",
        "sic_description": "Services-Computer Programming, Data Processing, Etc.",
        "category": "Technology",
        "fiscal_year_end": "1231",
        "entity_type": "Corporation",
        "phone": "123-456-7890",
        "business_address": "123 Test Street, Test City, TS 12345",
        "mailing_address": "P.O. Box 123, Test City, TS 12345"
    }
    db_company = crud_company.create_company(company_data=company_data, session=db)
    return db_company


@pytest.fixture
def db_filing(db, db_company):
    """Create a test filing in the database."""
    filing_data = {
        "company_id": db_company.id,
        "filing_type": "10-K",
        "accession_number": "0001234567-23-000123",
        "filing_date": datetime.strptime("2023-03-15", "%Y-%m-%d"),
        "report_date": datetime.strptime("2022-12-31", "%Y-%m-%d"),
        "form_name": "Annual Report",
        "file_number": "001-12345",
        "film_number": "23456789",
        "description": "Annual report for fiscal year ending December 31, 2022",
        "url": "https://www.sec.gov/Archives/edgar/data/1234567/000123456723000123/test-10k.htm",
        "data": {"key": "value"}
    }
    # Create filing with proper function signature (filing_data first, session second)
    db_filing = crud_filing.create_filing(filing_data=filing_data, session=db)
    return db_filing


@pytest.fixture
def template_data():
    """Fixture providing sample prompt template data"""
    return {
        "name": "Test Template",
        "description": "A test prompt template",
        "system_prompt": "You are a financial analyst.",
        "user_prompt_template": "Analyze {company_name}'s {document_type}.",
        "assistant_prompt_template": "I'll analyze the financial data.",
        "category": "test_category",
        "default_parameters": {
            "temperature": 0.5,
            "max_tokens": 1000
        },
        "is_active": True
    }


@pytest.fixture
def completion_data():
    """Fixture providing sample AI completion data"""
    return {
        "system_prompt": "You are a financial analyst.",
        "user_prompt": "Analyze Apple Inc.'s Q1 2025 Report.",
        "completion_text": "Apple Inc. reported strong financial results for Q1 2025...",
        "model": "gpt-4",
        "temperature": 0.5,
        "max_tokens": 1000,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "context_texts": ["Apple Inc. reported revenue of $100B"],
        "completion_id": "comp_123456",
        "token_usage": {"prompt_tokens": 150, "completion_tokens": 200, "total_tokens": 350},
        "tags": ["apple", "q1", "2025"],
        "notes": "Test completion"
    }


@pytest.fixture
def rating_data():
    """Fixture providing sample completion rating data"""
    return {
        "rating": 4,
        "accuracy_score": 4,
        "relevance_score": 5,
        "helpfulness_score": 3,
        "comments": "Good analysis but could be more detailed."
    }


@pytest.fixture
def db_prompt_template(db: Session, template_data):
    """Fixture that creates a prompt template in the database"""
    template = crud_ai_completion.create_prompt_template(
        db=db,
        name=template_data["name"],
        description=template_data["description"],
        system_prompt=template_data["system_prompt"],
        user_prompt_template=template_data["user_prompt_template"],
        assistant_prompt_template=template_data["assistant_prompt_template"],
        category=template_data["category"],
        default_parameters=template_data["default_parameters"],
        is_active=template_data["is_active"]
    )
    return template


@pytest.fixture
def db_completion(db: Session, db_prompt_template, completion_data, db_company, db_filing):
    """Fixture that creates an AI completion in the database"""
    completion = crud_ai_completion.create_ai_completion(
        db=db,
        prompt_template_id=db_prompt_template.id,
        system_prompt=completion_data["system_prompt"],
        user_prompt=completion_data["user_prompt"],
        completion_text=completion_data["completion_text"],
        model=completion_data["model"],
        temperature=completion_data["temperature"],
        max_tokens=completion_data["max_tokens"],
        company_id=db_company.id,
        filing_id=db_filing.id,
        context_texts=completion_data["context_texts"],
        top_p=completion_data["top_p"],
        frequency_penalty=completion_data["frequency_penalty"],
        presence_penalty=completion_data["presence_penalty"],
        completion_id=completion_data["completion_id"],
        token_usage=completion_data["token_usage"],
        tags=completion_data["tags"],
        notes=completion_data["notes"]
    )
    return completion


@pytest.fixture
def db_source_document(db: Session, db_company, db_filing):
    """Fixture that creates a source document in the database"""
    document = models.SourceDocument(
        filing_id=db_filing.id,
        company_id=db_company.id,
        report_date=datetime.now(),
        document_type="10-K",
        document_name="Test Document",
        content="This is a test document content for Apple Inc.",
        url="https://example.com/test-document"
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@pytest.fixture
def db_completion_with_relations(db: Session, db_prompt_template, completion_data,
                               db_company, db_filing, db_source_document):
    """Fixture that creates an AI completion with source document relationships"""
    completion = crud_ai_completion.create_ai_completion(
        db=db,
        prompt_template_id=db_prompt_template.id,
        system_prompt=completion_data["system_prompt"],
        user_prompt=completion_data["user_prompt"],
        completion_text=completion_data["completion_text"],
        model=completion_data["model"],
        temperature=completion_data["temperature"],
        max_tokens=completion_data["max_tokens"],
        company_id=db_company.id,
        filing_id=db_filing.id,
        source_document_ids=[db_source_document.id],
        context_texts=completion_data["context_texts"],
        tags=completion_data["tags"]
    )
    return completion


@pytest.fixture
def db_completion_chain(db: Session, db_prompt_template, db_completion, completion_data):
    """Fixture that creates an AI completion that uses another as context"""
    follow_up = crud_ai_completion.create_ai_completion(
        db=db,
        prompt_template_id=db_prompt_template.id,
        system_prompt="You are a follow-up analyst.",
        user_prompt="Provide more detail on the previous analysis.",
        completion_text="Building on the previous analysis, Apple's Q1 2025 performance shows...",
        model=completion_data["model"],
        temperature=0.3,
        max_tokens=1500,
        context_completion_ids=[db_completion.id],
        tags=["follow-up", "detailed"]
    )
    return follow_up


def test_create_prompt_template(db: Session, template_data):
    """Test creating a prompt template"""
    template = crud_ai_completion.create_prompt_template(
        db=db,
        name=template_data["name"],
        description=template_data["description"],
        system_prompt=template_data["system_prompt"],
        user_prompt_template=template_data["user_prompt_template"],
        assistant_prompt_template=template_data["assistant_prompt_template"],
        category=template_data["category"],
        default_parameters=template_data["default_parameters"],
        is_active=template_data["is_active"]
    )

    assert template is not None
    assert template.id is not None
    assert template.name == template_data["name"]
    assert template.description == template_data["description"]
    assert template.system_prompt == template_data["system_prompt"]
    assert template.user_prompt_template == template_data["user_prompt_template"]
    assert template.assistant_prompt_template == template_data["assistant_prompt_template"]
    assert template.category == template_data["category"]
    assert template.default_parameters == template_data["default_parameters"]
    assert template.is_active == template_data["is_active"]
    assert template.created_at is not None
    assert template.updated_at is not None


def test_get_prompt_template(db: Session, db_prompt_template):
    """Test retrieving a prompt template by ID"""
    retrieved = crud_ai_completion.get_prompt_template(db, db_prompt_template.id)

    assert retrieved is not None
    assert retrieved.id == db_prompt_template.id
    assert retrieved.name == db_prompt_template.name
    assert retrieved.system_prompt == db_prompt_template.system_prompt


def test_get_prompt_templates(db: Session, db_prompt_template, template_data):
    """Test retrieving prompt templates with filtering"""
    # Create a second template with different category
    second_template = crud_ai_completion.create_prompt_template(
        db=db,
        name="Second Template",
        description="Another test template",
        system_prompt="You are a risk analyst.",
        user_prompt_template="Analyze the risks for {company_name}.",
        category="risk_analysis",
        default_parameters={"temperature": 0.3},
        is_active=True
    )

    # Test filtering by category
    test_category_templates = crud_ai_completion.get_prompt_templates(
        db,
        category=template_data["category"]
    )
    assert len(test_category_templates) == 1
    assert test_category_templates[0].id == db_prompt_template.id

    # Test filtering by active status
    active_templates = crud_ai_completion.get_prompt_templates(
        db,
        is_active=True
    )
    assert len(active_templates) == 2

    # Create an inactive template
    inactive_template = crud_ai_completion.create_prompt_template(
        db=db,
        name="Inactive Template",
        description="An inactive template",
        system_prompt="You are a deprecated analyst.",
        user_prompt_template="Analyze {company_name}.",
        is_active=False
    )

    # Test filtering by inactive status
    inactive_templates = crud_ai_completion.get_prompt_templates(
        db,
        is_active=False
    )
    assert len(inactive_templates) == 1
    assert inactive_templates[0].id == inactive_template.id


def test_update_prompt_template(db: Session, db_prompt_template):
    """Test updating a prompt template"""
    # Store the original updated_at timestamp
    original_timestamp = db_prompt_template.updated_at

    # Add a small delay to ensure timestamps will be different
    import time
    time.sleep(0.01)

    updated = crud_ai_completion.update_prompt_template(
        db,
        db_prompt_template.id,
        name="Updated Template Name",
        description="Updated description",
        default_parameters={"temperature": 0.8, "max_tokens": 2000}
    )

    assert updated is not None
    assert updated.id == db_prompt_template.id
    assert updated.name == "Updated Template Name"
    assert updated.description == "Updated description"
    assert updated.default_parameters == {"temperature": 0.8, "max_tokens": 2000}
    # These fields should not have changed
    assert updated.system_prompt == db_prompt_template.system_prompt
    assert updated.user_prompt_template == db_prompt_template.user_prompt_template

    # Verify that update_at was updated
    assert updated.updated_at > original_timestamp


def test_delete_prompt_template(db: Session, db_prompt_template):
    """Test deleting a prompt template"""
    result = crud_ai_completion.delete_prompt_template(db, db_prompt_template.id)
    assert result is True

    # Verify template was deleted
    retrieved = crud_ai_completion.get_prompt_template(db, db_prompt_template.id)
    assert retrieved is None

    # Test deleting non-existent template
    result = crud_ai_completion.delete_prompt_template(db, 9999)
    assert result is False


def test_create_ai_completion(db: Session, db_prompt_template, completion_data, db_company, db_filing):
    """Test creating an AI completion"""
    completion = crud_ai_completion.create_ai_completion(
        db=db,
        prompt_template_id=db_prompt_template.id,
        system_prompt=completion_data["system_prompt"],
        user_prompt=completion_data["user_prompt"],
        completion_text=completion_data["completion_text"],
        model=completion_data["model"],
        temperature=completion_data["temperature"],
        max_tokens=completion_data["max_tokens"],
        company_id=db_company.id,
        filing_id=db_filing.id
    )

    assert completion is not None
    assert completion.id is not None
    assert completion.prompt_template_id == db_prompt_template.id
    assert completion.system_prompt == completion_data["system_prompt"]
    assert completion.user_prompt == completion_data["user_prompt"]
    assert completion.completion_text == completion_data["completion_text"]
    assert completion.model == completion_data["model"]
    assert completion.temperature == completion_data["temperature"]
    assert completion.max_tokens == completion_data["max_tokens"]
    assert completion.company_id == db_company.id
    assert completion.filing_id == db_filing.id
    assert completion.created_at is not None


def test_get_ai_completion(db: Session, db_completion):
    """Test retrieving an AI completion by ID"""
    retrieved = crud_ai_completion.get_ai_completion(db, db_completion.id)

    assert retrieved is not None
    assert retrieved.id == db_completion.id
    assert retrieved.prompt_template_id == db_completion.prompt_template_id
    assert retrieved.system_prompt == db_completion.system_prompt
    assert retrieved.completion_text == db_completion.completion_text


def test_get_ai_completions_with_filtering(db: Session, db_completion, db_completion_with_relations,
                                          db_company, db_source_document):
    """Test retrieving AI completions with filtering"""
    # Test filtering by company ID
    company_completions = crud_ai_completion.get_ai_completions(
        db,
        company_id=db_company.id
    )
    assert len(company_completions) == 2

    # Test filtering by source document ID
    doc_completions = crud_ai_completion.get_ai_completions(
        db,
        source_document_id=db_source_document.id
    )
    assert len(doc_completions) == 1
    assert doc_completions[0].id == db_completion_with_relations.id

    # Test filtering by tags
    tag_completions = crud_ai_completion.get_ai_completions(
        db,
        tags=["apple"]
    )
    assert len(tag_completions) == 2

    # Test filtering by model
    model_completions = crud_ai_completion.get_ai_completions(
        db,
        model=db_completion.model
    )
    assert len(model_completions) == 2


def test_create_completion_with_source_documents(db: Session, db_prompt_template, completion_data,
                                               db_company, db_filing, db_source_document):
    """Test creating a completion with source document relationships"""
    completion = crud_ai_completion.create_ai_completion(
        db=db,
        prompt_template_id=db_prompt_template.id,
        system_prompt=completion_data["system_prompt"],
        user_prompt=completion_data["user_prompt"],
        completion_text=completion_data["completion_text"],
        model=completion_data["model"],
        temperature=completion_data["temperature"],
        max_tokens=completion_data["max_tokens"],
        source_document_ids=[db_source_document.id]
    )

    assert completion is not None
    assert len(completion.source_documents) == 1
    assert completion.source_documents[0].id == db_source_document.id


def test_completion_self_referential_relationship(db: Session, db_completion_chain):
    """Test self-referential relationship between completions"""
    # Get the parent completion
    parent = crud_ai_completion.get_ai_completion(db, db_completion_chain.context_completions[0].id)

    # Verify bidirectional relationship
    assert len(parent.used_as_context_by) == 1
    assert parent.used_as_context_by[0].id == db_completion_chain.id

    # Test querying by context completion
    context_filtered = crud_ai_completion.get_ai_completions(
        db,
        context_completion_id=parent.id
    )
    assert len(context_filtered) == 1
    assert context_filtered[0].id == db_completion_chain.id

    # Test querying by "used as context by"
    used_as_context_filtered = crud_ai_completion.get_ai_completions(
        db,
        used_as_context_by_completion_id=db_completion_chain.id
    )
    assert len(used_as_context_filtered) == 1
    assert used_as_context_filtered[0].id == parent.id


def test_create_completion_rating(db: Session, db_completion, rating_data):
    """Test creating a completion rating"""
    rating = crud_ai_completion.create_completion_rating(
        db=db,
        completion_id=db_completion.id,
        rating=rating_data["rating"],
        accuracy_score=rating_data["accuracy_score"],
        relevance_score=rating_data["relevance_score"],
        helpfulness_score=rating_data["helpfulness_score"],
        comments=rating_data["comments"]
    )

    assert rating is not None
    assert rating.id is not None
    assert rating.completion_id == db_completion.id
    assert rating.rating == rating_data["rating"]
    assert rating.accuracy_score == rating_data["accuracy_score"]
    assert rating.relevance_score == rating_data["relevance_score"]
    assert rating.helpfulness_score == rating_data["helpfulness_score"]
    assert rating.comments == rating_data["comments"]
    assert rating.created_at is not None
    assert rating.updated_at is not None


def test_get_completion_rating(db: Session, db_completion, rating_data):
    """Test retrieving a completion rating"""
    # Create a rating
    rating = crud_ai_completion.create_completion_rating(
        db=db,
        completion_id=db_completion.id,
        **rating_data
    )

    # Retrieve the rating
    retrieved = crud_ai_completion.get_completion_rating(db, rating.id)

    assert retrieved is not None
    assert retrieved.id == rating.id
    assert retrieved.completion_id == db_completion.id
    assert retrieved.rating == rating_data["rating"]
    assert retrieved.comments == rating_data["comments"]


def test_get_completion_ratings_with_filtering(db: Session, db_completion, rating_data):
    """Test retrieving completion ratings with filtering"""
    # Create two ratings for the same completion
    rating1 = crud_ai_completion.create_completion_rating(
        db=db,
        completion_id=db_completion.id,
        rating=5,
        accuracy_score=5,
        relevance_score=5,
        helpfulness_score=5,
        comments="Excellent analysis"
    )

    rating2 = crud_ai_completion.create_completion_rating(
        db=db,
        completion_id=db_completion.id,
        rating=3,
        accuracy_score=3,
        relevance_score=4,
        helpfulness_score=2,
        comments="Average analysis"
    )

    # Test filtering by completion ID
    completion_ratings = crud_ai_completion.get_completion_ratings(
        db,
        completion_id=db_completion.id
    )
    assert len(completion_ratings) == 2

    # Test filtering by minimum rating
    high_ratings = crud_ai_completion.get_completion_ratings(
        db,
        completion_id=db_completion.id,
        min_rating=4
    )
    assert len(high_ratings) == 1
    assert high_ratings[0].id == rating1.id


def test_update_completion_rating(db: Session, db_completion, rating_data):
    """Test updating a completion rating"""
    # Create a rating
    rating = crud_ai_completion.create_completion_rating(
        db=db,
        completion_id=db_completion.id,
        **rating_data
    )

    # Store the original timestamp
    original_timestamp = rating.updated_at

    # Add a small delay to ensure timestamps will be different
    import time
    time.sleep(0.01)

    # Update the rating
    updated = crud_ai_completion.update_completion_rating(
        db,
        rating.id,
        rating=2,
        accuracy_score=2,
        comments="Updated comments after review"
    )

    assert updated is not None
    assert updated.id == rating.id
    assert updated.rating == 2
    assert updated.accuracy_score == 2
    # This should not have changed
    assert updated.relevance_score == rating_data["relevance_score"]
    assert updated.comments == "Updated comments after review"
    # Verify updated_at was updated
    assert updated.updated_at > original_timestamp


def test_relationship_cascade_delete(db: Session, db_completion, rating_data):
    """Test that ratings are deleted when a completion is deleted"""
    # Create a rating for the completion
    rating = crud_ai_completion.create_completion_rating(
        db=db,
        completion_id=db_completion.id,
        **rating_data
    )

    # Delete the completion
    db.delete(db_completion)
    db.commit()

    # Verify rating was also deleted
    retrieved_rating = crud_ai_completion.get_completion_rating(db, rating.id)
    assert retrieved_rating is None