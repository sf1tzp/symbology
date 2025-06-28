from typing import Any, Dict, List
import uuid

import pytest

from src.database.aggregates import (
    Aggregate,
    create_aggregate,
    delete_aggregate,
    get_aggregate,
    get_aggregate_ids,
    get_aggregates_by_completion,
    update_aggregate,
)
from src.database.companies import Company
from src.database.completions import Completion
from src.database.prompts import Prompt, PromptRole


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
        "fiscal_year_end": "2023-12-31",
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

# Sample aggregate data fixtures
@pytest.fixture
def sample_aggregate_data() -> Dict[str, Any]:
    """Sample aggregate data for testing."""
    return {
        "model": "gpt-4",
        "temperature": 0.7,
        "top_p": 1.0,
        "num_ctx": 4096,
        "content": "This is a test aggregate content summarizing multiple completions.",
        "total_duration": 45.5
    }

@pytest.fixture
def sample_minimal_aggregate_data() -> Dict[str, Any]:
    """Minimal aggregate data with only required fields."""
    return {
        "model": "gpt-3.5-turbo",
        "content": "Minimal aggregate content."
    }

@pytest.fixture
def sample_system_prompt_data() -> Dict[str, Any]:
    """Sample system prompt data for testing."""
    return {
        "name": "Test Aggregate System Prompt",
        "role": PromptRole.SYSTEM,
        "description": "A test system prompt for aggregate analysis",
        "content": "You are a helpful assistant that summarizes multiple documents."
    }

@pytest.fixture
def create_test_system_prompt(db_session, sample_system_prompt_data):
    """Create and return a test system prompt."""
    prompt = Prompt(**sample_system_prompt_data)
    db_session.add(prompt)
    db_session.commit()
    return prompt

@pytest.fixture
def create_multiple_completions(db_session, create_test_system_prompt):
    """Create and return multiple test completions."""
    completions = []
    for i in range(3):
        completion_data = {
            "model": "gpt-4",
            "system_prompt_id": create_test_system_prompt.id,
            "content": f"Test completion content {i+1}",
            "temperature": 0.7,
            "num_ctx": 4096,
            "total_duration": 10.0 + i
        }
        completion = Completion(**completion_data)
        db_session.add(completion)
        completions.append(completion)

    db_session.commit()
    return completions

@pytest.fixture
def multiple_aggregate_data() -> List[Dict[str, Any]]:
    """Generate data for multiple aggregates."""
    return [
        {
            "model": "gpt-4",
            "content": "First aggregate content",
            "temperature": 0.5,
            "total_duration": 30.0
        },
        {
            "model": "gpt-3.5-turbo",
            "content": "Second aggregate content",
            "temperature": 0.8,
            "total_duration": 25.0
        },
        {
            "model": "claude-3",
            "content": "Third aggregate content",
            "temperature": 0.3,
            "total_duration": 40.0
        }
    ]


# Test cases for Aggregate CRUD operations
def test_create_aggregate(db_session, sample_aggregate_data):
    """Test creating an aggregate."""
    aggregate = Aggregate(**sample_aggregate_data)
    db_session.add(aggregate)
    db_session.commit()

    # Verify it was created
    assert aggregate.id is not None
    assert aggregate.model == "gpt-4"
    assert aggregate.content == "This is a test aggregate content summarizing multiple completions."
    assert aggregate.temperature == 0.7
    assert aggregate.num_ctx == 4096

    # Verify it can be retrieved from the database
    retrieved = db_session.query(Aggregate).filter_by(id=aggregate.id).first()
    assert retrieved is not None
    assert retrieved.model == aggregate.model
    assert retrieved.content == aggregate.content


def test_create_minimal_aggregate(db_session, sample_minimal_aggregate_data):
    """Test creating an aggregate with only required fields."""
    aggregate = Aggregate(**sample_minimal_aggregate_data)
    db_session.add(aggregate)
    db_session.commit()

    assert aggregate.id is not None
    assert aggregate.model == "gpt-3.5-turbo"
    assert aggregate.content == "Minimal aggregate content."


def test_create_aggregate_function(db_session, sample_aggregate_data):
    """Test the create_aggregate helper function."""
    # Mock the db_session global
    import src.database.aggregates as aggregates_module
    original_get_db_session = aggregates_module.get_db_session
    aggregates_module.get_db_session = lambda: db_session

    try:
        # Create an aggregate using the helper function
        aggregate = create_aggregate(sample_aggregate_data)

        # Verify it was created correctly
        assert aggregate.id is not None
        assert aggregate.model == "gpt-4"
        assert aggregate.content == "This is a test aggregate content summarizing multiple completions."

        # Verify it exists in the database
        retrieved = db_session.query(Aggregate).filter_by(id=aggregate.id).first()
        assert retrieved is not None
        assert retrieved.model == aggregate.model
    finally:
        # Restore the original function
        aggregates_module.get_db_session = original_get_db_session


def test_create_aggregate_with_completion_ids(db_session, sample_aggregate_data, create_multiple_completions):
    """Test creating an aggregate with multiple completion IDs associated."""
    # Mock the db_session global
    import src.database.aggregates as aggregates_module
    original_get_db_session = aggregates_module.get_db_session
    aggregates_module.get_db_session = lambda: db_session

    try:
        # Add completion IDs to the aggregate data
        completion_ids = [comp.id for comp in create_multiple_completions]
        aggregate_data = sample_aggregate_data.copy()
        aggregate_data['completion_ids'] = completion_ids

        # Create the aggregate
        aggregate = create_aggregate(aggregate_data)

        # Verify the aggregate was created
        assert aggregate.id is not None
        assert aggregate.model == "gpt-4"

        # Verify the completion associations
        assert len(aggregate.source_completions) == 3

        # Check that all completion IDs are associated
        associated_completion_ids = [comp.id for comp in aggregate.source_completions]
        for completion_id in completion_ids:
            assert completion_id in associated_completion_ids

        # Verify from the completion side - each completion should have the aggregate in its aggregates
        for completion in create_multiple_completions:
            db_session.refresh(completion)  # Refresh to get updated relationships
            assert len(completion.aggregates) > 0
            assert aggregate.id in [agg.id for agg in completion.aggregates]

    finally:
        # Restore the original function
        aggregates_module.get_db_session = original_get_db_session


def test_get_aggregate_by_id(db_session, sample_aggregate_data):
    """Test retrieving an aggregate by ID using the get_aggregate function."""
    # First create an aggregate
    aggregate = Aggregate(**sample_aggregate_data)
    db_session.add(aggregate)
    db_session.commit()

    # Mock the db_session global
    import src.database.aggregates as aggregates_module
    original_get_db_session = aggregates_module.get_db_session
    aggregates_module.get_db_session = lambda: db_session

    try:
        # Test the get_aggregate function
        retrieved = get_aggregate(aggregate.id)
        assert retrieved is not None
        assert retrieved.id == aggregate.id
        assert retrieved.model == "gpt-4"

        # Test with non-existent ID
        non_existent = get_aggregate(uuid.uuid4())
        assert non_existent is None

        # Test with string UUID
        retrieved_str = get_aggregate(str(aggregate.id))
        assert retrieved_str is not None
        assert retrieved_str.id == aggregate.id
    finally:
        # Restore the original function
        aggregates_module.get_db_session = original_get_db_session


def test_get_aggregate_ids(db_session, multiple_aggregate_data):
    """Test retrieving all aggregate IDs."""
    # Create multiple aggregates
    aggregate_ids = []
    for data in multiple_aggregate_data:
        aggregate = Aggregate(**data)
        db_session.add(aggregate)
        db_session.commit()
        aggregate_ids.append(aggregate.id)

    # Mock the db_session global
    import src.database.aggregates as aggregates_module
    original_get_db_session = aggregates_module.get_db_session
    aggregates_module.get_db_session = lambda: db_session

    try:
        # Get all aggregate IDs
        ids = get_aggregate_ids()

        # Verify all created aggregates are included
        for aggregate_id in aggregate_ids:
            assert aggregate_id in ids

        # Verify count matches or exceeds (in case of existing data)
        assert len(ids) >= len(aggregate_ids)
    finally:
        # Restore the original function
        aggregates_module.get_db_session = original_get_db_session


def test_update_aggregate(db_session, sample_aggregate_data):
    """Test updating an aggregate using the update_aggregate function."""
    # First create an aggregate
    aggregate = Aggregate(**sample_aggregate_data)
    db_session.add(aggregate)
    db_session.commit()

    # Mock the db_session global
    import src.database.aggregates as aggregates_module
    original_get_db_session = aggregates_module.get_db_session
    aggregates_module.get_db_session = lambda: db_session

    try:
        # Update the aggregate
        updates = {
            "content": "Updated aggregate content",
            "temperature": 0.9,
            "total_duration": 60.0
        }

        updated = update_aggregate(aggregate.id, updates)

        # Verify updates were applied
        assert updated is not None
        assert updated.content == "Updated aggregate content"
        assert updated.temperature == 0.9
        assert updated.total_duration == 60.0

        # Check that model wasn't changed
        assert updated.model == "gpt-4"

        # Test updating non-existent aggregate
        non_existent = update_aggregate(uuid.uuid4(), {"content": "Non-existent aggregate"})
        assert non_existent is None
    finally:
        # Restore the original function
        aggregates_module.get_db_session = original_get_db_session


def test_update_aggregate_completion_associations(db_session, sample_aggregate_data, create_multiple_completions):
    """Test updating completion associations for an aggregate."""
    # Create an aggregate first
    aggregate = Aggregate(**sample_aggregate_data)
    db_session.add(aggregate)
    db_session.commit()

    # Mock the db_session global
    import src.database.aggregates as aggregates_module
    original_get_db_session = aggregates_module.get_db_session
    aggregates_module.get_db_session = lambda: db_session

    try:
        # Initially associate with first 2 completions
        initial_completion_ids = [comp.id for comp in create_multiple_completions[:2]]
        updates = {"completion_ids": initial_completion_ids}

        updated = update_aggregate(aggregate.id, updates)
        assert len(updated.source_completions) == 2

        # Update to associate with all 3 completions
        all_completion_ids = [comp.id for comp in create_multiple_completions]
        updates = {"completion_ids": all_completion_ids}

        updated = update_aggregate(aggregate.id, updates)
        assert len(updated.source_completions) == 3

        # Verify the completion IDs are correct
        associated_ids = [comp.id for comp in updated.source_completions]
        for comp_id in all_completion_ids:
            assert comp_id in associated_ids

    finally:
        # Restore the original function
        aggregates_module.get_db_session = original_get_db_session


def test_delete_aggregate(db_session, sample_aggregate_data):
    """Test deleting an aggregate using the delete_aggregate function."""
    # First create an aggregate
    aggregate = Aggregate(**sample_aggregate_data)
    db_session.add(aggregate)
    db_session.commit()
    aggregate_id = aggregate.id

    # Mock the db_session global
    import src.database.aggregates as aggregates_module
    original_get_db_session = aggregates_module.get_db_session
    aggregates_module.get_db_session = lambda: db_session

    try:
        # Delete the aggregate
        result = delete_aggregate(aggregate_id)
        assert result is True

        # Verify it was deleted
        assert db_session.query(Aggregate).filter_by(id=aggregate_id).first() is None

        # Test deleting non-existent aggregate
        result = delete_aggregate(uuid.uuid4())
        assert result is False
    finally:
        # Restore the original function
        aggregates_module.get_db_session = original_get_db_session


def test_get_aggregates_by_completion(db_session, sample_aggregate_data, create_multiple_completions):
    """Test retrieving aggregates by completion ID."""
    # Create multiple aggregates with different completion associations
    aggregate1 = Aggregate(**sample_aggregate_data)
    aggregate1.content = "First aggregate"
    aggregate1.source_completions = [create_multiple_completions[0], create_multiple_completions[1]]

    aggregate_data2 = sample_aggregate_data.copy()
    aggregate_data2["content"] = "Second aggregate"
    aggregate2 = Aggregate(**aggregate_data2)
    aggregate2.source_completions = [create_multiple_completions[1], create_multiple_completions[2]]

    db_session.add(aggregate1)
    db_session.add(aggregate2)
    db_session.commit()

    # Mock the db_session global
    import src.database.aggregates as aggregates_module
    original_get_db_session = aggregates_module.get_db_session
    aggregates_module.get_db_session = lambda: db_session

    try:
        # Test getting aggregates by completion ID
        # Completion 0 should be in aggregate1 only
        aggregates_for_comp0 = get_aggregates_by_completion(create_multiple_completions[0].id)
        assert len(aggregates_for_comp0) == 1
        assert aggregates_for_comp0[0].id == aggregate1.id

        # Completion 1 should be in both aggregates
        aggregates_for_comp1 = get_aggregates_by_completion(create_multiple_completions[1].id)
        assert len(aggregates_for_comp1) == 2
        aggregate_ids = [agg.id for agg in aggregates_for_comp1]
        assert aggregate1.id in aggregate_ids
        assert aggregate2.id in aggregate_ids

        # Completion 2 should be in aggregate2 only
        aggregates_for_comp2 = get_aggregates_by_completion(create_multiple_completions[2].id)
        assert len(aggregates_for_comp2) == 1
        assert aggregates_for_comp2[0].id == aggregate2.id

    finally:
        # Restore the original function
        aggregates_module.get_db_session = original_get_db_session


def test_aggregate_prompt_relationship(db_session, sample_aggregate_data, create_test_system_prompt):
    """Test the relationship between aggregates and prompts."""
    # Create an aggregate with a system prompt
    aggregate_data = sample_aggregate_data.copy()
    aggregate_data["system_prompt_id"] = create_test_system_prompt.id

    aggregate = Aggregate(**aggregate_data)
    db_session.add(aggregate)
    db_session.commit()

    # Verify the prompt relationship
    assert aggregate.system_prompt_id == create_test_system_prompt.id
    assert aggregate.system_prompt.name == create_test_system_prompt.name


def test_aggregate_multiple_completion_association_detailed(db_session, sample_aggregate_data, create_multiple_completions):
    """Test detailed verification of multiple completion ID associations."""
    # Create an aggregate and associate it with all completions
    aggregate = Aggregate(**sample_aggregate_data)
    aggregate.source_completions.extend(create_multiple_completions)
    db_session.add(aggregate)
    db_session.commit()

    # Verify the aggregate has all completions
    assert len(aggregate.source_completions) == 3

    # Verify each completion is correctly associated
    completion_ids = [comp.id for comp in create_multiple_completions]
    associated_completion_ids = [comp.id for comp in aggregate.source_completions]

    for comp_id in completion_ids:
        assert comp_id in associated_completion_ids

    # Verify bidirectional relationship - each completion should reference the aggregate
    for completion in create_multiple_completions:
        db_session.refresh(completion)  # Refresh to get the backref relationship
        assert len(completion.aggregates) > 0
        assert aggregate.id in [agg.id for agg in completion.aggregates]

    # Verify association table records exist
    from src.database.aggregates import aggregate_completion_association
    association_records = db_session.execute(
        aggregate_completion_association.select().where(
            aggregate_completion_association.c.aggregate_id == aggregate.id
        )
    ).fetchall()

    assert len(association_records) == 3

    # Verify all completion IDs are in the association table
    associated_comp_ids_from_table = [record.completion_id for record in association_records]
    for comp_id in completion_ids:
        assert comp_id in associated_comp_ids_from_table


def test_aggregate_with_invalid_attributes(db_session, sample_aggregate_data):
    """Test updating an aggregate with invalid attributes."""
    # Create an aggregate first
    aggregate = Aggregate(**sample_aggregate_data)
    db_session.add(aggregate)
    db_session.commit()

    # Mock the db_session global
    import src.database.aggregates as aggregates_module
    original_get_db_session = aggregates_module.get_db_session
    aggregates_module.get_db_session = lambda: db_session

    try:
        # Update with invalid attribute
        updates = {
            "content": "Still valid content",
            "invalid_field": "This field doesn't exist"
        }

        # Should still update valid fields but ignore invalid ones
        updated = update_aggregate(aggregate.id, updates)
        assert updated is not None
        assert updated.content == "Still valid content"

        # The invalid field should not be added to the object
        assert not hasattr(updated, "invalid_field")
    finally:
        # Restore the original function
        aggregates_module.get_db_session = original_get_db_session


def test_get_recent_aggregates_by_company(db_session, create_test_company):
    """Test getting the most recent aggregates for each document type by company."""
    from datetime import datetime, timedelta

    # Mock the db_session global
    import src.database.aggregates as aggregates_module
    from src.database.aggregates import get_recent_aggregates_by_company
    from src.database.documents import DocumentType
    original_get_db_session = aggregates_module.get_db_session
    aggregates_module.get_db_session = lambda: db_session

    try:
        company_id = create_test_company.id
        base_time = datetime.now()

        # Create multiple aggregates for different document types with different timestamps
        # MDA aggregates - older and newer
        mda_old = Aggregate(
            company_id=company_id,
            document_type=DocumentType.MDA,
            model="gpt-4",
            content="Old MDA aggregate",
            created_at=base_time - timedelta(days=5)
        )
        mda_new = Aggregate(
            company_id=company_id,
            document_type=DocumentType.MDA,
            model="gpt-4",
            content="New MDA aggregate",
            created_at=base_time - timedelta(days=1)
        )

        # RISK_FACTORS aggregates - older and newer
        risk_old = Aggregate(
            company_id=company_id,
            document_type=DocumentType.RISK_FACTORS,
            model="gpt-4",
            content="Old risk factors aggregate",
            created_at=base_time - timedelta(days=3)
        )
        risk_new = Aggregate(
            company_id=company_id,
            document_type=DocumentType.RISK_FACTORS,
            model="gpt-4",
            content="New risk factors aggregate",
            created_at=base_time
        )

        # DESCRIPTION aggregate - only one
        description = Aggregate(
            company_id=company_id,
            document_type=DocumentType.DESCRIPTION,
            model="gpt-4",
            content="Business description aggregate",
            created_at=base_time - timedelta(days=2)
        )

        # Add all aggregates
        db_session.add_all([mda_old, mda_new, risk_old, risk_new, description])
        db_session.commit()

        # Get recent aggregates
        recent_aggregates = get_recent_aggregates_by_company(company_id)

        # Should return exactly 3 aggregates (one for each document type)
        assert len(recent_aggregates) == 3

        # Create a map for easier verification
        aggregates_by_type = {agg.document_type: agg for agg in recent_aggregates}

        # Verify we got the most recent for each type
        assert DocumentType.MDA in aggregates_by_type
        assert aggregates_by_type[DocumentType.MDA].content == "New MDA aggregate"
        assert aggregates_by_type[DocumentType.MDA].id == mda_new.id

        assert DocumentType.RISK_FACTORS in aggregates_by_type
        assert aggregates_by_type[DocumentType.RISK_FACTORS].content == "New risk factors aggregate"
        assert aggregates_by_type[DocumentType.RISK_FACTORS].id == risk_new.id

        assert DocumentType.DESCRIPTION in aggregates_by_type
        assert aggregates_by_type[DocumentType.DESCRIPTION].content == "Business description aggregate"
        assert aggregates_by_type[DocumentType.DESCRIPTION].id == description.id

        # Verify old aggregates are not included
        returned_ids = [agg.id for agg in recent_aggregates]
        assert mda_old.id not in returned_ids
        assert risk_old.id not in returned_ids

    finally:
        # Restore the original function
        aggregates_module.get_db_session = original_get_db_session


def test_get_recent_aggregates_by_company_no_aggregates(db_session, create_test_company):
    """Test getting recent aggregates for a company with no aggregates."""
    # Mock the db_session global
    import src.database.aggregates as aggregates_module
    from src.database.aggregates import get_recent_aggregates_by_company
    original_get_db_session = aggregates_module.get_db_session
    aggregates_module.get_db_session = lambda: db_session

    try:
        # Get aggregates for company with no aggregates
        recent_aggregates = get_recent_aggregates_by_company(create_test_company.id)

        # Should return empty list
        assert len(recent_aggregates) == 0

    finally:
        # Restore the original function
        aggregates_module.get_db_session = original_get_db_session


def test_get_recent_aggregates_by_company_with_null_document_type(db_session, create_test_company):
    """Test that aggregates with null document_type are excluded."""
    from datetime import datetime

    # Mock the db_session global
    import src.database.aggregates as aggregates_module
    from src.database.aggregates import get_recent_aggregates_by_company
    from src.database.documents import DocumentType
    original_get_db_session = aggregates_module.get_db_session
    aggregates_module.get_db_session = lambda: db_session

    try:
        company_id = create_test_company.id

        # Create aggregates with and without document_type
        valid_aggregate = Aggregate(
            company_id=company_id,
            document_type=DocumentType.MDA,
            model="gpt-4",
            content="Valid MDA aggregate",
            created_at=datetime.now()
        )

        null_type_aggregate = Aggregate(
            company_id=company_id,
            document_type=None,  # This should be excluded
            model="gpt-4",
            content="Aggregate without document type",
            created_at=datetime.now()
        )

        db_session.add_all([valid_aggregate, null_type_aggregate])
        db_session.commit()

        # Get recent aggregates
        recent_aggregates = get_recent_aggregates_by_company(company_id)

        # Should only return the aggregate with a valid document_type
        assert len(recent_aggregates) == 1
        assert recent_aggregates[0].id == valid_aggregate.id
        assert recent_aggregates[0].document_type == DocumentType.MDA

        # Verify null type aggregate is not included
        returned_ids = [agg.id for agg in recent_aggregates]
        assert null_type_aggregate.id not in returned_ids

    finally:
        # Restore the original function
        aggregates_module.get_db_session = original_get_db_session


def test_get_recent_aggregates_by_ticker(db_session, create_test_company):
    """Test getting recent aggregates by company ticker."""
    from datetime import datetime

    # Mock the db_session global in both modules
    import src.database.aggregates as aggregates_module
    from src.database.aggregates import get_recent_aggregates_by_ticker
    import src.database.companies as companies_module
    from src.database.documents import DocumentType
    original_get_db_session_agg = aggregates_module.get_db_session
    original_get_db_session_comp = companies_module.get_db_session
    aggregates_module.get_db_session = lambda: db_session
    companies_module.get_db_session = lambda: db_session

    try:
        company_id = create_test_company.id

        # Create an aggregate for the test company
        aggregate = Aggregate(
            company_id=company_id,
            document_type=DocumentType.MDA,
            model="gpt-4",
            content="MDA aggregate for ticker test",
            created_at=datetime.now()
        )
        db_session.add(aggregate)
        db_session.commit()

        # Use the test company's ticker from the fixture
        ticker = "TEST"  # This matches our fixture's ticker

        # Get aggregates by ticker
        recent_aggregates = get_recent_aggregates_by_ticker(ticker)

        # Should return the aggregate we created
        assert len(recent_aggregates) == 1
        assert recent_aggregates[0].id == aggregate.id
        assert recent_aggregates[0].content == "MDA aggregate for ticker test"

    finally:
        # Restore the original functions
        aggregates_module.get_db_session = original_get_db_session_agg
        companies_module.get_db_session = original_get_db_session_comp


def test_get_recent_aggregates_by_ticker_company_not_found(db_session):
    """Test getting recent aggregates by ticker when company doesn't exist."""
    # Mock the db_session global in both modules
    import src.database.aggregates as aggregates_module
    from src.database.aggregates import get_recent_aggregates_by_ticker
    import src.database.companies as companies_module
    original_get_db_session_agg = aggregates_module.get_db_session
    original_get_db_session_comp = companies_module.get_db_session
    aggregates_module.get_db_session = lambda: db_session
    companies_module.get_db_session = lambda: db_session

    try:
        # Try to get aggregates for non-existent ticker
        recent_aggregates = get_recent_aggregates_by_ticker("NONEXISTENT")

        # Should return empty list
        assert len(recent_aggregates) == 0

    finally:
        # Restore the original functions
        aggregates_module.get_db_session = original_get_db_session_agg
        companies_module.get_db_session = original_get_db_session_comp


def test_get_recent_aggregates_by_company_multiple_companies(db_session, create_test_company):
    """Test that aggregates from other companies are not included."""
    from datetime import datetime

    # Mock the db_session global
    import src.database.aggregates as aggregates_module
    from src.database.aggregates import get_recent_aggregates_by_company
    from src.database.companies import Company
    from src.database.documents import DocumentType
    original_get_db_session = aggregates_module.get_db_session
    aggregates_module.get_db_session = lambda: db_session

    try:
        company1_id = create_test_company.id

        # Create a second company
        company2 = Company(
            name="Test Company 2",
            display_name="TESTCO2",
            is_company=True,
            tickers=["TEST2"]
        )
        db_session.add(company2)
        db_session.commit()
        company2_id = company2.id

        # Create aggregates for both companies
        company1_aggregate = Aggregate(
            company_id=company1_id,
            document_type=DocumentType.MDA,
            model="gpt-4",
            content="Company 1 MDA",
            created_at=datetime.now()
        )

        company2_aggregate = Aggregate(
            company_id=company2_id,
            document_type=DocumentType.MDA,
            model="gpt-4",
            content="Company 2 MDA",
            created_at=datetime.now()
        )

        db_session.add_all([company1_aggregate, company2_aggregate])
        db_session.commit()

        # Get aggregates for company 1
        company1_aggregates = get_recent_aggregates_by_company(company1_id)

        # Should only return company 1's aggregate
        assert len(company1_aggregates) == 1
        assert company1_aggregates[0].id == company1_aggregate.id
        assert company1_aggregates[0].content == "Company 1 MDA"

        # Verify company 2's aggregate is not included
        returned_ids = [agg.id for agg in company1_aggregates]
        assert company2_aggregate.id not in returned_ids

        # Get aggregates for company 2
        company2_aggregates = get_recent_aggregates_by_company(company2_id)

        # Should only return company 2's aggregate
        assert len(company2_aggregates) == 1
        assert company2_aggregates[0].id == company2_aggregate.id
        assert company2_aggregates[0].content == "Company 2 MDA"

    finally:
        # Restore the original function
        aggregates_module.get_db_session = original_get_db_session