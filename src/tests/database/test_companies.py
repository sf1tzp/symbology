import uuid
import pytest
from datetime import date
from sqlalchemy.exc import IntegrityError
from typing import Dict, Any

# Import the Company model and functions
from src.ingestion.database.companies import (
    Company,
    get_company_ids,
    get_company,
    create_company,
    update_company,
    delete_company
)
from src.ingestion.database.base import Base

# Sample company data fixtures
@pytest.fixture
def sample_company_data() -> Dict[str, Any]:
    """Sample company data for testing."""
    return {
        "name": "Apple Inc.",
        "cik": "0000320193",
        "display_name": "Apple",
        "is_company": True,
        "tickers": ["AAPL"],
        "exchanges": ["NASDAQ"],
        "sic": "3571",
        "sic_description": "Electronic Computers",
        "fiscal_year_end": date(2023, 9, 30),
        "entity_type": "Corporation",
        "ein": "94-2404110"
    }

@pytest.fixture
def sample_company_data_minimal() -> Dict[str, Any]:
    """Minimal company data with only required fields."""
    return {
        "name": "Minimal Test Company"
    }

@pytest.fixture
def sample_company_with_former_names() -> Dict[str, Any]:
    """Company data with former names included."""
    return {
        "name": "Meta Platforms, Inc.",
        "cik": "0001326801",
        "tickers": ["META"],
        "exchanges": ["NASDAQ"],
        "former_names": [
            {"name": "Facebook, Inc.", "date_changed": "2021-10-28"},
            {"name": "Facebook, LLC", "date_changed": "2004-07-29"}
        ]
    }

@pytest.fixture
def multiple_company_data() -> list:
    """Generate data for multiple companies."""
    return [
        {
            "name": "Microsoft Corporation",
            "cik": "0000789019",
            "tickers": ["MSFT"],
            "exchanges": ["NASDAQ"]
        },
        {
            "name": "Alphabet Inc.",
            "cik": "0001652044",
            "tickers": ["GOOGL", "GOOG"],
            "exchanges": ["NASDAQ"]
        },
        {
            "name": "Tesla, Inc.",
            "cik": "0001318605",
            "tickers": ["TSLA"],
            "exchanges": ["NASDAQ"]
        }
    ]

# Test cases for Company CRUD operations
def test_create_company(db_session, sample_company_data):
    """Test creating a company."""
    # Create company
    company = Company(**sample_company_data)
    db_session.add(company)
    db_session.commit()

    # Verify it was created
    assert company.id is not None
    assert company.name == "Apple Inc."
    assert company.cik == "0000320193"

    # Verify it can be retrieved from the database
    retrieved = db_session.query(Company).filter_by(id=company.id).first()
    assert retrieved is not None
    assert retrieved.name == company.name
    assert retrieved.cik == company.cik

def test_create_minimal_company(db_session, sample_company_data_minimal):
    """Test creating a company with only required fields."""
    company = Company(**sample_company_data_minimal)
    db_session.add(company)
    db_session.commit()

    # Verify it was created with defaults
    assert company.id is not None
    assert company.name == "Minimal Test Company"
    assert company.is_company is True
    assert company.tickers == []
    assert company.exchanges == []
    assert company.former_names == []

def test_create_company_with_former_names(db_session, sample_company_with_former_names):
    """Test creating a company with former names."""
    company = Company(**sample_company_with_former_names)
    db_session.add(company)
    db_session.commit()

    # Verify former names were stored correctly
    assert len(company.former_names) == 2
    assert company.former_names[0]["name"] == "Facebook, Inc."
    assert company.former_names[1]["name"] == "Facebook, LLC"

def test_get_company_by_id(db_session, sample_company_data):
    """Test retrieving a company by ID using the get_company function."""
    # First create a company
    company = Company(**sample_company_data)
    db_session.add(company)
    db_session.commit()

    # Mock the db_session global with our test session
    import src.ingestion.database.companies as companies_module
    original_get_db_session = companies_module.get_db_session
    companies_module.get_db_session = lambda: db_session

    try:
        # Test the get_company function
        retrieved = get_company(company.id)
        assert retrieved is not None
        assert retrieved.id == company.id
        assert retrieved.name == "Apple Inc."

        # Test with non-existent ID
        non_existent = get_company(uuid.uuid4())
        assert non_existent is None
    finally:
        # Restore the original function
        companies_module.get_db_session = original_get_db_session

def test_create_company_function(db_session, sample_company_data):
    """Test the create_company helper function."""
    # Mock the db_session global
    import src.ingestion.database.companies as companies_module
    original_get_db_session = companies_module.get_db_session
    companies_module.get_db_session = lambda: db_session

    try:
        # Create a company using the helper function
        company = create_company(sample_company_data)

        # Verify it was created correctly
        assert company.id is not None
        assert company.name == "Apple Inc."
        assert company.cik == "0000320193"

        # Verify it exists in the database
        retrieved = db_session.query(Company).filter_by(id=company.id).first()
        assert retrieved is not None
        assert retrieved.name == company.name
    finally:
        # Restore the original function
        companies_module.get_db_session = original_get_db_session

def test_update_company(db_session, sample_company_data):
    """Test updating a company using the update_company function."""
    # First create a company
    company = Company(**sample_company_data)
    db_session.add(company)
    db_session.commit()

    # Mock the db_session global
    import src.ingestion.database.companies as companies_module
    original_get_db_session = companies_module.get_db_session
    companies_module.get_db_session = lambda: db_session

    try:
        # Update the company
        updates = {
            "name": "Apple Corporation",
            "display_name": "Apple Corp",
            "tickers": ["AAPL", "APPL"]
        }

        updated = update_company(company.id, updates)

        # Verify updates were applied
        assert updated is not None
        assert updated.name == "Apple Corporation"
        assert updated.display_name == "Apple Corp"
        assert len(updated.tickers) == 2
        assert "APPL" in updated.tickers

        # Check that other fields weren't changed
        assert updated.cik == "0000320193"
        assert updated.sic == "3571"

        # Test updating non-existent company
        non_existent = update_company(uuid.uuid4(), {"name": "Test"})
        assert non_existent is None
    finally:
        # Restore the original function
        companies_module.get_db_session = original_get_db_session

def test_delete_company(db_session, sample_company_data):
    """Test deleting a company using the delete_company function."""
    # First create a company
    company = Company(**sample_company_data)
    db_session.add(company)
    db_session.commit()
    company_id = company.id

    # Mock the db_session global
    import src.ingestion.database.companies as companies_module
    original_get_db_session = companies_module.get_db_session
    companies_module.get_db_session = lambda: db_session

    try:
        # Delete the company
        result = delete_company(company_id)
        assert result is True

        # Verify it was deleted
        assert db_session.query(Company).filter_by(id=company_id).first() is None

        # Test deleting non-existent company
        result = delete_company(uuid.uuid4())
        assert result is False
    finally:
        # Restore the original function
        companies_module.get_db_session = original_get_db_session

def test_get_company_ids(db_session, multiple_company_data):
    """Test retrieving all company IDs."""
    # Create multiple companies
    company_ids = []
    for data in multiple_company_data:
        company = Company(**data)
        db_session.add(company)
        db_session.commit()
        company_ids.append(company.id)

    # Mock the db_session global
    import src.ingestion.database.companies as companies_module
    original_get_db_session = companies_module.get_db_session
    companies_module.get_db_session = lambda: db_session

    try:
        # Get all company IDs
        ids = get_company_ids()

        # Verify all created companies are included
        for company_id in company_ids:
            assert company_id in ids

        # Verify count matches
        assert len(ids) >= len(company_ids)
    finally:
        # Restore the original function
        companies_module.get_db_session = original_get_db_session

def test_duplicate_cik(db_session, sample_company_data):
    """Test that creating companies with duplicate CIK fails."""
    # Create first company
    company1 = Company(**sample_company_data)
    db_session.add(company1)
    db_session.commit()

    # Try to create second company with same CIK
    company2_data = sample_company_data.copy()
    company2_data["name"] = "Duplicate CIK Company"
    company2 = Company(**company2_data)
    db_session.add(company2)

    # Should raise IntegrityError due to unique constraint
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_duplicate_ein(db_session, sample_company_data):
    """Test that creating companies with duplicate EIN fails."""
    # Create first company
    company1 = Company(**sample_company_data)
    db_session.add(company1)
    db_session.commit()

    # Try to create second company with same EIN but different CIK
    company2_data = sample_company_data.copy()
    company2_data["name"] = "Duplicate EIN Company"
    company2_data["cik"] = "0000999999"  # Different CIK
    company2 = Company(**company2_data)
    db_session.add(company2)

    # Should raise IntegrityError due to unique constraint on EIN
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_update_with_invalid_attributes(db_session, sample_company_data):
    """Test updating a company with invalid attributes."""
    # First create a company
    company = Company(**sample_company_data)
    db_session.add(company)
    db_session.commit()

    # Mock the db_session global
    import src.ingestion.database.companies as companies_module
    original_get_db_session = companies_module.get_db_session
    companies_module.get_db_session = lambda: db_session

    try:
        # Update with invalid attribute
        updates = {
            "name": "Valid Update",
            "invalid_field": "This field doesn't exist"
        }

        # Should still update valid fields but ignore invalid ones
        updated = update_company(company.id, updates)
        assert updated is not None
        assert updated.name == "Valid Update"

        # The invalid field should not be added to the object
        assert not hasattr(updated, "invalid_field")
    finally:
        # Restore the original function
        companies_module.get_db_session = original_get_db_session

def test_get_company_with_string_uuid(db_session, sample_company_data):
    """Test retrieving a company using string representation of UUID."""
    # First create a company
    company = Company(**sample_company_data)
    db_session.add(company)
    db_session.commit()

    # Mock the db_session global
    import src.ingestion.database.companies as companies_module
    original_get_db_session = companies_module.get_db_session
    companies_module.get_db_session = lambda: db_session

    try:
        # Test get_company with string UUID
        retrieved = get_company(str(company.id))
        assert retrieved is not None
        assert retrieved.id == company.id
    finally:
        # Restore the original function
        companies_module.get_db_session = original_get_db_session