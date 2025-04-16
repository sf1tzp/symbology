import uuid
import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from typing import Dict, Any, List

# Import the FinancialValue model and functions
from src.ingestion.database.financial_values import (
    FinancialValue,
    get_financial_value_ids,
    get_financial_value,
    create_financial_value,
    update_financial_value,
    delete_financial_value
)
from src.ingestion.database.companies import Company, create_company
from src.ingestion.database.financial_concepts import FinancialConcept, create_financial_concept
from src.ingestion.database.filings import Filing, create_filing
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

# Sample financial concept fixture
@pytest.fixture
def sample_concept_data() -> Dict[str, Any]:
    """Sample financial concept data for testing."""
    return {
        "name": "Revenue",
        "description": "The income generated from sale of goods or services.",
        "labels": ["Revenue", "Sales", "Net Sales"]
    }

@pytest.fixture
def create_test_concept(db_session, sample_concept_data):
    """Create and return a test financial concept."""
    concept = FinancialConcept(**sample_concept_data)
    db_session.add(concept)
    db_session.commit()
    return concept

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

# Sample financial value data fixtures
@pytest.fixture
def sample_financial_value_data(create_test_company, create_test_concept, create_test_filing) -> Dict[str, Any]:
    """Sample financial value data for testing."""
    return {
        "company_id": create_test_company.id,
        "concept_id": create_test_concept.id,
        "filing_id": create_test_filing.id,
        "value_date": date(2023, 12, 31),
        "value": Decimal("1000000.50")
    }

@pytest.fixture
def sample_financial_value_data_no_filing(create_test_company, create_test_concept) -> Dict[str, Any]:
    """Sample financial value data without filing reference."""
    return {
        "company_id": create_test_company.id,
        "concept_id": create_test_concept.id,
        "value_date": date(2023, 12, 31),
        "value": Decimal("850000.25")
    }

@pytest.fixture
def multiple_financial_value_data(create_test_company, create_test_concept) -> List[Dict[str, Any]]:
    """Generate data for multiple financial values for the same company and concept."""
    company_id = create_test_company.id
    concept_id = create_test_concept.id
    return [
        {
            "company_id": company_id,
            "concept_id": concept_id,
            "value_date": date(2023, 12, 31),
            "value": Decimal("1000000.00")
        },
        {
            "company_id": company_id,
            "concept_id": concept_id,
            "value_date": date(2023, 9, 30),
            "value": Decimal("750000.00")
        },
        {
            "company_id": company_id,
            "concept_id": concept_id,
            "value_date": date(2023, 6, 30),
            "value": Decimal("600000.00")
        }
    ]

# Test cases for FinancialValue CRUD operations
def test_create_financial_value(db_session, sample_financial_value_data):
    """Test creating a financial value."""
    # Create financial value
    financial_value = FinancialValue(**sample_financial_value_data)
    db_session.add(financial_value)
    db_session.commit()

    # Verify it was created
    assert financial_value.id is not None
    assert financial_value.value == Decimal("1000000.50")
    assert financial_value.value_date == date(2023, 12, 31)

    # Verify it can be retrieved from the database
    retrieved = db_session.query(FinancialValue).filter_by(id=financial_value.id).first()
    assert retrieved is not None
    assert retrieved.value == financial_value.value
    assert retrieved.company_id == financial_value.company_id
    assert retrieved.concept_id == financial_value.concept_id

def test_create_financial_value_without_filing(db_session, sample_financial_value_data_no_filing):
    """Test creating a financial value without a filing reference."""
    financial_value = FinancialValue(**sample_financial_value_data_no_filing)
    db_session.add(financial_value)
    db_session.commit()

    # Verify it was created with filing_id as None
    assert financial_value.id is not None
    assert financial_value.value == Decimal("850000.25")
    assert financial_value.filing_id is None

def test_financial_value_relationships(db_session, create_test_company, create_test_concept, create_test_filing, sample_financial_value_data):
    """Test the relationships between financial values and other entities."""
    # Create a financial value
    financial_value = FinancialValue(**sample_financial_value_data)
    db_session.add(financial_value)
    db_session.commit()

    # Verify the company relationship
    assert financial_value.company_id == create_test_company.id
    assert financial_value.company.name == create_test_company.name

    # Verify the concept relationship
    assert financial_value.concept_id == create_test_concept.id
    assert financial_value.concept.name == create_test_concept.name

    # Verify the filing relationship
    assert financial_value.filing_id == create_test_filing.id
    assert financial_value.filing.accession_number == create_test_filing.accession_number

    # Check from the company side
    company = db_session.query(Company).filter_by(id=create_test_company.id).first()
    assert len(company.financial_values) > 0
    assert company.financial_values[0].id == financial_value.id

    # Check from the concept side
    concept = db_session.query(FinancialConcept).filter_by(id=create_test_concept.id).first()
    assert len(concept.financial_values) > 0
    assert concept.financial_values[0].id == financial_value.id

    # Check from the filing side
    filing = db_session.query(Filing).filter_by(id=create_test_filing.id).first()
    assert len(filing.financial_values) > 0
    assert filing.financial_values[0].id == financial_value.id

def test_get_financial_value_by_id(db_session, sample_financial_value_data):
    """Test retrieving a financial value by ID using the get_financial_value function."""
    # First create a financial value
    financial_value = FinancialValue(**sample_financial_value_data)
    db_session.add(financial_value)
    db_session.commit()

    # Mock the db_session global with our test session
    import src.ingestion.database.financial_values as values_module
    original_get_db_session = values_module.get_db_session
    values_module.get_db_session = lambda: db_session

    try:
        # Test the get_financial_value function
        retrieved = get_financial_value(financial_value.id)
        assert retrieved is not None
        assert retrieved.id == financial_value.id
        assert retrieved.value == Decimal("1000000.50")

        # Test with non-existent ID
        non_existent = get_financial_value(uuid.uuid4())
        assert non_existent is None
    finally:
        # Restore the original function
        values_module.get_db_session = original_get_db_session

def test_create_financial_value_function(db_session, sample_financial_value_data):
    """Test the create_financial_value helper function."""
    # Mock the db_session global
    import src.ingestion.database.financial_values as values_module
    original_get_db_session = values_module.get_db_session
    values_module.get_db_session = lambda: db_session

    try:
        # Create a financial value using the helper function
        financial_value = create_financial_value(sample_financial_value_data)

        # Verify it was created correctly
        assert financial_value.id is not None
        assert financial_value.value == Decimal("1000000.50")
        assert financial_value.value_date == date(2023, 12, 31)

        # Verify it exists in the database
        retrieved = db_session.query(FinancialValue).filter_by(id=financial_value.id).first()
        assert retrieved is not None
        assert retrieved.value == financial_value.value
    finally:
        # Restore the original function
        values_module.get_db_session = original_get_db_session

def test_update_financial_value(db_session, sample_financial_value_data):
    """Test updating a financial value using the update_financial_value function."""
    # First create a financial value
    financial_value = FinancialValue(**sample_financial_value_data)
    db_session.add(financial_value)
    db_session.commit()

    # Mock the db_session global
    import src.ingestion.database.financial_values as values_module
    original_get_db_session = values_module.get_db_session
    values_module.get_db_session = lambda: db_session

    try:
        # Update the financial value
        updates = {
            "value": Decimal("1200000.75"),
            "value_date": date(2023, 12, 30)
        }

        updated = update_financial_value(financial_value.id, updates)

        # Verify updates were applied
        assert updated is not None
        assert updated.value == Decimal("1200000.75")
        assert updated.value_date == date(2023, 12, 30)

        # Check that other fields weren't changed
        assert updated.company_id == financial_value.company_id
        assert updated.concept_id == financial_value.concept_id

        # Test updating non-existent financial value
        non_existent = update_financial_value(uuid.uuid4(), {"value": Decimal("100.00")})
        assert non_existent is None
    finally:
        # Restore the original function
        values_module.get_db_session = original_get_db_session

def test_delete_financial_value(db_session, sample_financial_value_data):
    """Test deleting a financial value using the delete_financial_value function."""
    # First create a financial value
    financial_value = FinancialValue(**sample_financial_value_data)
    db_session.add(financial_value)
    db_session.commit()
    value_id = financial_value.id

    # Mock the db_session global
    import src.ingestion.database.financial_values as values_module
    original_get_db_session = values_module.get_db_session
    values_module.get_db_session = lambda: db_session

    try:
        # Delete the financial value
        result = delete_financial_value(value_id)
        assert result is True

        # Verify it was deleted
        assert db_session.query(FinancialValue).filter_by(id=value_id).first() is None

        # Test deleting non-existent financial value
        result = delete_financial_value(uuid.uuid4())
        assert result is False
    finally:
        # Restore the original function
        values_module.get_db_session = original_get_db_session

def test_get_financial_value_ids(db_session, multiple_financial_value_data):
    """Test retrieving all financial value IDs."""
    # Create multiple financial values
    value_ids = []
    for data in multiple_financial_value_data:
        financial_value = FinancialValue(**data)
        db_session.add(financial_value)
        db_session.commit()
        value_ids.append(financial_value.id)

    # Mock the db_session global
    import src.ingestion.database.financial_values as values_module
    original_get_db_session = values_module.get_db_session
    values_module.get_db_session = lambda: db_session

    try:
        # Get all financial value IDs
        ids = get_financial_value_ids()

        # Verify all created values are included
        for value_id in value_ids:
            assert value_id in ids

        # Verify count matches or exceeds (in case of existing data)
        assert len(ids) >= len(value_ids)
    finally:
        # Restore the original function
        values_module.get_db_session = original_get_db_session

def test_cascade_delete_company(db_session, create_test_company, create_test_concept, sample_financial_value_data_no_filing):
    """Test that deleting a company also deletes its associated financial values."""
    # Create a financial value for the company
    data = sample_financial_value_data_no_filing
    financial_value = FinancialValue(**data)
    db_session.add(financial_value)
    db_session.commit()
    value_id = financial_value.id

    # Now delete the company
    db_session.delete(create_test_company)
    db_session.commit()

    # Verify that the financial value was also deleted due to cascade
    assert db_session.query(FinancialValue).filter_by(id=value_id).first() is None

def test_cascade_delete_concept(db_session, create_test_company, create_test_concept, sample_financial_value_data_no_filing):
    """Test that deleting a financial concept also deletes its associated financial values."""
    # Create a financial value for the concept
    data = sample_financial_value_data_no_filing
    financial_value = FinancialValue(**data)
    db_session.add(financial_value)
    db_session.commit()
    value_id = financial_value.id

    # Now delete the concept
    db_session.delete(create_test_concept)
    db_session.commit()

    # Verify that the financial value was also deleted due to cascade
    assert db_session.query(FinancialValue).filter_by(id=value_id).first() is None

def test_cascade_delete_filing(db_session, create_test_filing, sample_financial_value_data):
    """Test that deleting a filing also deletes its associated financial values."""
    # Create a financial value for the filing
    financial_value = FinancialValue(**sample_financial_value_data)
    db_session.add(financial_value)
    db_session.commit()
    value_id = financial_value.id

    # Now delete the filing
    db_session.delete(create_test_filing)
    db_session.commit()

    # Verify that the financial value was also deleted due to cascade
    assert db_session.query(FinancialValue).filter_by(id=value_id).first() is None

def test_update_with_invalid_attributes(db_session, sample_financial_value_data):
    """Test updating a financial value with invalid attributes."""
    # First create a financial value
    financial_value = FinancialValue(**sample_financial_value_data)
    db_session.add(financial_value)
    db_session.commit()

    # Mock the db_session global
    import src.ingestion.database.financial_values as values_module
    original_get_db_session = values_module.get_db_session
    values_module.get_db_session = lambda: db_session

    try:
        # Update with invalid attribute
        updates = {
            "value": Decimal("999999.99"),
            "invalid_field": "This field doesn't exist"
        }

        # Should still update valid fields but ignore invalid ones
        updated = update_financial_value(financial_value.id, updates)
        assert updated is not None
        assert updated.value == Decimal("999999.99")

        # The invalid field should not be added to the object
        assert not hasattr(updated, "invalid_field")
    finally:
        # Restore the original function
        values_module.get_db_session = original_get_db_session

def test_get_financial_value_with_string_uuid(db_session, sample_financial_value_data):
    """Test retrieving a financial value using string representation of UUID."""
    # First create a financial value
    financial_value = FinancialValue(**sample_financial_value_data)
    db_session.add(financial_value)
    db_session.commit()

    # Mock the db_session global
    import src.ingestion.database.financial_values as values_module
    original_get_db_session = values_module.get_db_session
    values_module.get_db_session = lambda: db_session

    try:
        # Test get_financial_value with string UUID
        retrieved = get_financial_value(str(financial_value.id))
        assert retrieved is not None
        assert retrieved.id == financial_value.id
        assert retrieved.value == Decimal("1000000.50")
    finally:
        # Restore the original function
        values_module.get_db_session = original_get_db_session

def test_upsert_financial_value(db_session, create_test_company, create_test_concept, create_test_filing):
    """Test the upsert_financial_value helper function."""
    # Mock the db_session global
    import src.ingestion.database.financial_values as values_module
    original_get_db_session = values_module.get_db_session
    values_module.get_db_session = lambda: db_session

    try:
        # Create a new financial value using upsert
        value_date = date(2023, 12, 31)
        result = values_module.upsert_financial_value(
            company_id=create_test_company.id,
            concept_id=create_test_concept.id,
            value_date=value_date,
            value=Decimal("1000000.50"),
            filing_id=create_test_filing.id
        )

        assert result is not None
        assert result.value == Decimal("1000000.50")
        assert result.value_date == value_date
        value_id = result.id

        # Call upsert again with the same identifiers but different value - should update existing
        updated_result = values_module.upsert_financial_value(
            company_id=create_test_company.id,
            concept_id=create_test_concept.id,
            value_date=value_date,
            value=Decimal("1200000.75"),
            filing_id=create_test_filing.id
        )

        # Should be same financial value but with updated value
        assert updated_result.id == value_id
        assert updated_result.value == Decimal("1200000.75")
        assert updated_result.value_date == value_date

        # Test without filing_id
        standalone_value = values_module.upsert_financial_value(
            company_id=create_test_company.id,
            concept_id=create_test_concept.id,
            value_date=date(2023, 9, 30),
            value=Decimal("900000.25")
        )

        assert standalone_value is not None
        assert standalone_value.value == Decimal("900000.25")
        assert standalone_value.filing_id is None
    finally:
        # Restore the original function
        values_module.get_db_session = original_get_db_session

def test_upsert_financial_value_with_different_filing(db_session, create_test_company, create_test_concept, create_test_filing, sample_filing_data):
    """Test that upsert_financial_value creates a new value for the same identifiers but different filing."""
    # Create a second filing
    filing2_data = sample_filing_data.copy()
    filing2_data["accession_number"] = "0000123456-23-000124"
    filing2 = Filing(**filing2_data)
    db_session.add(filing2)
    db_session.commit()

    # Mock the db_session global
    import src.ingestion.database.financial_values as values_module
    original_get_db_session = values_module.get_db_session
    values_module.get_db_session = lambda: db_session

    try:
        # Create financial value for first filing
        value_date = date(2023, 12, 31)
        value1 = values_module.upsert_financial_value(
            company_id=create_test_company.id,
            concept_id=create_test_concept.id,
            value_date=value_date,
            value=Decimal("1000000.00"),
            filing_id=create_test_filing.id
        )

        # Create financial value for second filing (same date, company, concept)
        value2 = values_module.upsert_financial_value(
            company_id=create_test_company.id,
            concept_id=create_test_concept.id,
            value_date=value_date,
            value=Decimal("1100000.00"),
            filing_id=filing2.id
        )

        # Should be different financial values
        assert value1.id != value2.id
        assert value1.value == Decimal("1000000.00")
        assert value2.value == Decimal("1100000.00")
        assert value1.filing_id != value2.filing_id
    finally:
        # Restore the original function
        values_module.get_db_session = original_get_db_session

def test_get_financial_values_by_filing(db_session, create_test_company, create_test_concept, create_test_filing, multiple_financial_value_data):
    """Test the get_financial_values_by_filing helper function."""
    # Create multiple financial values for the same filing
    for data in multiple_financial_value_data:
        # Add filing_id to all values
        data_with_filing = data.copy()
        data_with_filing["filing_id"] = create_test_filing.id
        value = FinancialValue(**data_with_filing)
        db_session.add(value)
    db_session.commit()

    # Mock the db_session global
    import src.ingestion.database.financial_values as values_module
    original_get_db_session = values_module.get_db_session
    values_module.get_db_session = lambda: db_session

    try:
        # Get values for the filing
        values = values_module.get_financial_values_by_filing(create_test_filing.id)

        # Should have the same number of values as we created
        assert len(values) == len(multiple_financial_value_data)

        # Test with a filing ID that has no values
        no_values = values_module.get_financial_values_by_filing(uuid.uuid4())
        assert len(no_values) == 0
    finally:
        # Restore the original function
        values_module.get_db_session = original_get_db_session

def test_get_financial_values_by_company_and_date(db_session, create_test_company, create_test_concept, multiple_financial_value_data):
    """Test the get_financial_values_by_company_and_date helper function."""
    # Create multiple financial values for the company
    for data in multiple_financial_value_data:
        value = FinancialValue(**data)
        db_session.add(value)
    db_session.commit()

    # We'll test with the first date in our test data
    test_date = multiple_financial_value_data[0]["value_date"]

    # Mock the db_session global
    import src.ingestion.database.financial_values as values_module
    original_get_db_session = values_module.get_db_session
    values_module.get_db_session = lambda: db_session

    try:
        # Get values for the company and date
        values = values_module.get_financial_values_by_company_and_date(
            create_test_company.id, test_date
        )

        # Should be 1 value for this specific date
        assert len(values) == 1
        assert values[0].value_date == test_date

        # Test with a date that has no values
        no_values = values_module.get_financial_values_by_company_and_date(
            create_test_company.id, date(2020, 1, 1)
        )
        assert len(no_values) == 0

        # Test with a non-existent company
        no_company_values = values_module.get_financial_values_by_company_and_date(
            uuid.uuid4(), test_date
        )
        assert len(no_company_values) == 0
    finally:
        # Restore the original function
        values_module.get_db_session = original_get_db_session
