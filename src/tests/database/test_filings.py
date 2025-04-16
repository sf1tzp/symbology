import uuid
import pytest
from datetime import date
from sqlalchemy.exc import IntegrityError
from typing import Dict, Any, List

# Import the Filing model and functions
from src.database.filings import (
    Filing,
    get_filing_ids,
    get_filing,
    create_filing,
    update_filing,
    delete_filing
)
from src.database.companies import Company, create_company
from src.database.documents import Document
from src.database.base import Base

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

# Sample filing data fixtures
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
def sample_filing_data_minimal(create_test_company) -> Dict[str, Any]:
    """Minimal filing data with only required fields."""
    return {
        "company_id": create_test_company.id,
        "accession_number": "0000123456-23-000456",
        "filing_type": "8-K",
        "filing_date": date(2023, 11, 15)
    }

@pytest.fixture
def multiple_filing_data(create_test_company) -> List[Dict[str, Any]]:
    """Generate data for multiple filings for the same company."""
    company_id = create_test_company.id
    return [
        {
            "company_id": company_id,
            "accession_number": "0000123456-23-000789",
            "filing_type": "10-Q",
            "filing_date": date(2023, 9, 30),
            "period_of_report": date(2023, 9, 30)
        },
        {
            "company_id": company_id,
            "accession_number": "0000123456-23-000790",
            "filing_type": "10-Q",
            "filing_date": date(2023, 6, 30),
            "period_of_report": date(2023, 6, 30)
        },
        {
            "company_id": company_id,
            "accession_number": "0000123456-23-000791",
            "filing_type": "10-Q",
            "filing_date": date(2023, 3, 31),
            "period_of_report": date(2023, 3, 31)
        }
    ]

# Test cases for Filing CRUD operations
def test_create_filing(db_session, sample_filing_data):
    """Test creating a filing."""
    # Create filing
    filing = Filing(**sample_filing_data)
    db_session.add(filing)
    db_session.commit()

    # Verify it was created
    assert filing.id is not None
    assert filing.accession_number == "0000123456-23-000123"
    assert filing.filing_type == "10-K"

    # Verify it can be retrieved from the database
    retrieved = db_session.query(Filing).filter_by(id=filing.id).first()
    assert retrieved is not None
    assert retrieved.accession_number == filing.accession_number
    assert retrieved.filing_type == filing.filing_type
    assert retrieved.filing_date == filing.filing_date

def test_create_minimal_filing(db_session, sample_filing_data_minimal):
    """Test creating a filing with only required fields."""
    filing = Filing(**sample_filing_data_minimal)
    db_session.add(filing)
    db_session.commit()

    # Verify it was created with defaults
    assert filing.id is not None
    assert filing.accession_number == "0000123456-23-000456"
    assert filing.filing_type == "8-K"
    assert filing.filing_url is None
    assert filing.period_of_report is None

def test_filing_company_relationship(db_session, create_test_company, sample_filing_data):
    """Test the relationship between filings and companies."""
    # Create a filing
    filing = Filing(**sample_filing_data)
    db_session.add(filing)
    db_session.commit()

    # Verify the company relationship
    assert filing.company_id == create_test_company.id
    assert filing.company.name == create_test_company.name

    # Check from the company side
    company = db_session.query(Company).filter_by(id=create_test_company.id).first()
    assert len(company.filings) > 0
    assert company.filings[0].id == filing.id

def test_get_filing_by_id(db_session, sample_filing_data):
    """Test retrieving a filing by ID using the get_filing function."""
    # First create a filing
    filing = Filing(**sample_filing_data)
    db_session.add(filing)
    db_session.commit()

    # Mock the db_session global with our test session
    import src.database.filings as filings_module
    original_get_db_session = filings_module.get_db_session
    filings_module.get_db_session = lambda: db_session

    try:
        # Test the get_filing function
        retrieved = get_filing(filing.id)
        assert retrieved is not None
        assert retrieved.id == filing.id
        assert retrieved.accession_number == "0000123456-23-000123"

        # Test with non-existent ID
        non_existent = get_filing(uuid.uuid4())
        assert non_existent is None
    finally:
        # Restore the original function
        filings_module.get_db_session = original_get_db_session

def test_create_filing_function(db_session, sample_filing_data):
    """Test the create_filing helper function."""
    # Mock the db_session global
    import src.database.filings as filings_module
    original_get_db_session = filings_module.get_db_session
    filings_module.get_db_session = lambda: db_session

    try:
        # Create a filing using the helper function
        filing = create_filing(sample_filing_data)

        # Verify it was created correctly
        assert filing.id is not None
        assert filing.accession_number == "0000123456-23-000123"
        assert filing.filing_type == "10-K"

        # Verify it exists in the database
        retrieved = db_session.query(Filing).filter_by(id=filing.id).first()
        assert retrieved is not None
        assert retrieved.accession_number == filing.accession_number

        # Test creating a filing with non-existent company
        invalid_data = sample_filing_data.copy()
        invalid_data["company_id"] = uuid.uuid4()  # Non-existent company ID

        # Should raise ValueError due to company not found
        with pytest.raises(ValueError):
            create_filing(invalid_data)
    finally:
        # Restore the original function
        filings_module.get_db_session = original_get_db_session

def test_update_filing(db_session, sample_filing_data):
    """Test updating a filing using the update_filing function."""
    # First create a filing
    filing = Filing(**sample_filing_data)
    db_session.add(filing)
    db_session.commit()

    # Mock the db_session global
    import src.database.filings as filings_module
    original_get_db_session = filings_module.get_db_session
    filings_module.get_db_session = lambda: db_session

    try:
        # Update the filing
        updates = {
            "filing_url": "https://updated-url.com/file.html",
            "period_of_report": date(2023, 12, 15)
        }

        updated = update_filing(filing.id, updates)

        # Verify updates were applied
        assert updated is not None
        assert updated.filing_url == "https://updated-url.com/file.html"
        assert updated.period_of_report == date(2023, 12, 15)

        # Check that other fields weren't changed
        assert updated.accession_number == "0000123456-23-000123"
        assert updated.filing_type == "10-K"

        # Test updating non-existent filing
        non_existent = update_filing(uuid.uuid4(), {"filing_type": "Test"})
        assert non_existent is None
    finally:
        # Restore the original function
        filings_module.get_db_session = original_get_db_session

def test_update_filing_with_invalid_company(db_session, sample_filing_data):
    """Test updating a filing with an invalid company ID."""
    # First create a filing
    filing = Filing(**sample_filing_data)
    db_session.add(filing)
    db_session.commit()

    # Mock the db_session global
    import src.database.filings as filings_module
    original_get_db_session = filings_module.get_db_session
    filings_module.get_db_session = lambda: db_session

    try:
        # Try to update with non-existent company ID
        updates = {
            "company_id": uuid.uuid4()  # Non-existent company ID
        }

        # Should raise ValueError
        with pytest.raises(ValueError):
            update_filing(filing.id, updates)
    finally:
        # Restore the original function
        filings_module.get_db_session = original_get_db_session

def test_delete_filing(db_session, sample_filing_data):
    """Test deleting a filing using the delete_filing function."""
    # First create a filing
    filing = Filing(**sample_filing_data)
    db_session.add(filing)
    db_session.commit()
    filing_id = filing.id

    # Mock the db_session global
    import src.database.filings as filings_module
    original_get_db_session = filings_module.get_db_session
    filings_module.get_db_session = lambda: db_session

    try:
        # Delete the filing
        result = delete_filing(filing_id)
        assert result is True

        # Verify it was deleted
        assert db_session.query(Filing).filter_by(id=filing_id).first() is None

        # Test deleting non-existent filing
        result = delete_filing(uuid.uuid4())
        assert result is False
    finally:
        # Restore the original function
        filings_module.get_db_session = original_get_db_session

def test_get_filing_ids(db_session, multiple_filing_data):
    """Test retrieving all filing IDs."""
    # Create multiple filings
    filing_ids = []
    for data in multiple_filing_data:
        filing = Filing(**data)
        db_session.add(filing)
        db_session.commit()
        filing_ids.append(filing.id)

    # Mock the db_session global
    import src.database.filings as filings_module
    original_get_db_session = filings_module.get_db_session
    filings_module.get_db_session = lambda: db_session

    try:
        # Get all filing IDs
        ids = get_filing_ids()

        # Verify all created filings are included
        for filing_id in filing_ids:
            assert filing_id in ids

        # Verify count matches
        assert len(ids) >= len(filing_ids)
    finally:
        # Restore the original function
        filings_module.get_db_session = original_get_db_session

def test_duplicate_accession_number(db_session, sample_filing_data, create_test_company):
    """Test that creating filings with duplicate accession numbers fails."""
    # Create first filing
    filing1 = Filing(**sample_filing_data)
    db_session.add(filing1)
    db_session.commit()

    # Try to create second filing with same accession number
    filing2_data = sample_filing_data.copy()
    filing2_data["filing_type"] = "8-K"  # Different filing type
    filing2 = Filing(**filing2_data)
    db_session.add(filing2)

    # Should raise IntegrityError due to unique constraint on accession_number
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_get_filing_with_string_uuid(db_session, sample_filing_data):
    """Test retrieving a filing using string representation of UUID."""
    # First create a filing
    filing = Filing(**sample_filing_data)
    db_session.add(filing)
    db_session.commit()

    # Mock the db_session global
    import src.database.filings as filings_module
    original_get_db_session = filings_module.get_db_session
    filings_module.get_db_session = lambda: db_session

    try:
        # Test get_filing with string UUID
        retrieved = get_filing(str(filing.id))
        assert retrieved is not None
        assert retrieved.id == filing.id
    finally:
        # Restore the original function
        filings_module.get_db_session = original_get_db_session

def test_update_with_invalid_attributes(db_session, sample_filing_data):
    """Test updating a filing with invalid attributes."""
    # First create a filing
    filing = Filing(**sample_filing_data)
    db_session.add(filing)
    db_session.commit()

    # Mock the db_session global
    import src.database.filings as filings_module
    original_get_db_session = filings_module.get_db_session
    filings_module.get_db_session = lambda: db_session

    try:
        # Update with invalid attribute
        updates = {
            "filing_type": "10-Q",
            "invalid_field": "This field doesn't exist"
        }

        # Should still update valid fields but ignore invalid ones
        updated = update_filing(filing.id, updates)
        assert updated is not None
        assert updated.filing_type == "10-Q"

        # The invalid field should not be added to the object
        assert not hasattr(updated, "invalid_field")
    finally:
        # Restore the original function
        filings_module.get_db_session = original_get_db_session

def test_cascade_delete_company(db_session, create_test_company, sample_filing_data):
    """Test that deleting a company also deletes its associated filings."""
    # Create a filing for the company
    filing = Filing(**sample_filing_data)
    db_session.add(filing)
    db_session.commit()
    filing_id = filing.id

    # Now delete the company
    db_session.delete(create_test_company)
    db_session.commit()

    # Verify that the filing was also deleted
    assert db_session.query(Filing).filter_by(id=filing_id).first() is None

def test_upsert_filing_by_accession_number(db_session, create_test_company, sample_filing_data):
    """Test the upsert_filing_by_accession_number helper function for creating and updating filings."""
    # Mock the db_session global
    import src.database.filings as filings_module
    original_get_db_session = filings_module.get_db_session
    filings_module.get_db_session = lambda: db_session

    try:
        # Create a new filing using upsert
        result = filings_module.upsert_filing_by_accession_number(sample_filing_data)
        assert result is not None
        assert result.accession_number == "0000123456-23-000123"
        assert result.filing_type == "10-K"

        # Now test updating the existing filing via upsert
        updated_data = {
            "accession_number": "0000123456-23-000123",  # Same accession number
            "filing_type": "10-K/A",  # Amended filing
            "filing_url": "https://updated-url.com/filing.html"
        }

        updated_result = filings_module.upsert_filing_by_accession_number(updated_data)

        # Verify the filing was updated, not created new
        assert updated_result.id == result.id  # Same ID as before
        assert updated_result.filing_type == "10-K/A"
        assert updated_result.filing_url == "https://updated-url.com/filing.html"

        # Original fields not in update remain unchanged
        assert updated_result.accession_number == "0000123456-23-000123"
        assert updated_result.filing_date == date(2023, 12, 31)
    finally:
        # Restore the original function
        filings_module.get_db_session = original_get_db_session

def test_upsert_filing_without_accession_number(db_session, create_test_company):
    """Test that upsert_filing_by_accession_number function raises ValueError when accession number is missing."""
    # Mock the db_session global
    import src.database.filings as filings_module
    original_get_db_session = filings_module.get_db_session
    filings_module.get_db_session = lambda: db_session

    try:
        # Try to upsert without accession number
        invalid_data = {
            "company_id": create_test_company.id,
            "filing_type": "10-K",
            "filing_date": date(2023, 12, 31)
        }

        # Should raise ValueError
        with pytest.raises(ValueError, match="Accession number is required"):
            filings_module.upsert_filing_by_accession_number(invalid_data)
    finally:
        # Restore the original function
        filings_module.get_db_session = original_get_db_session

def test_upsert_filing_invalid_company(db_session):
    """Test that upsert_filing_by_accession_number raises ValueError with non-existent company ID."""
    # Mock the db_session global
    import src.database.filings as filings_module
    original_get_db_session = filings_module.get_db_session
    filings_module.get_db_session = lambda: db_session

    try:
        # Try to upsert with non-existent company ID
        invalid_data = {
            "company_id": uuid.uuid4(),  # Random non-existent company ID
            "accession_number": "0000123456-23-000999",
            "filing_type": "10-K",
            "filing_date": date(2023, 12, 31)
        }

        # Should raise ValueError about company not found
        with pytest.raises(ValueError, match="Company with ID"):
            filings_module.upsert_filing_by_accession_number(invalid_data)
    finally:
        # Restore the original function
        filings_module.get_db_session = original_get_db_session

def test_get_filing_by_accession_number(db_session, sample_filing_data):
    """Test the get_filing_by_accession_number helper function."""
    # First create a filing
    filing = Filing(**sample_filing_data)
    db_session.add(filing)
    db_session.commit()

    # Mock the db_session global
    import src.database.filings as filings_module
    original_get_db_session = filings_module.get_db_session
    filings_module.get_db_session = lambda: db_session

    try:
        # Test retrieving by accession number
        retrieved = filings_module.get_filing_by_accession_number("0000123456-23-000123")
        assert retrieved is not None
        assert retrieved.id == filing.id
        assert retrieved.filing_type == "10-K"

        # Test with non-existent accession number
        non_existent = filings_module.get_filing_by_accession_number("9999999999-99-999999")
        assert non_existent is None
    finally:
        # Restore the original function
        filings_module.get_db_session = original_get_db_session

def test_get_filings_by_company(db_session, create_test_company, multiple_filing_data):
    """Test retrieving all filings for a specific company."""
    # Create multiple filings for the same company
    filing_ids = []
    for data in multiple_filing_data:
        filing = Filing(**data)
        db_session.add(filing)
        db_session.commit()
        filing_ids.append(filing.id)

    # Mock the db_session global
    import src.database.filings as filings_module
    original_get_db_session = filings_module.get_db_session
    filings_module.get_db_session = lambda: db_session

    try:
        # Get all filings for the company
        company_id = create_test_company.id
        filings = filings_module.get_filings_by_company(company_id)

        # Verify we got back all the filings we created
        assert len(filings) == len(filing_ids)

        # Check that all filing IDs are in our list of created filing IDs
        retrieved_ids = [filing.id for filing in filings]
        for filing_id in filing_ids:
            assert filing_id in retrieved_ids

        # Test with string UUID
        filings_str = filings_module.get_filings_by_company(str(company_id))
        assert len(filings_str) == len(filing_ids)

        # Test with non-existent company ID
        non_existent_filings = filings_module.get_filings_by_company(uuid.uuid4())
        assert len(non_existent_filings) == 0
    finally:
        # Restore the original function
        filings_module.get_db_session = original_get_db_session