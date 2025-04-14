from datetime import datetime
import pytest
from sqlalchemy.exc import IntegrityError

# Use absolute imports for test files
from src.ingestion.database.crud_company import create_company
from src.ingestion.database.crud_filing import (
    create_filing,
    delete_filing,
    get_all_filings,
    get_filing_by_accession_number,
    get_filing_by_id,
    get_filings_by_company_id,
    get_filings_by_date_range,
    get_filings_by_type,
    update_filing,
    upsert_filing,
)
from src.ingestion.database.models import Company


class TestFiling:
    """Test cases for Filing model and CRUD operations."""

    @pytest.fixture
    def test_company(self, db_session, sample_company_data):
        """Create a test company for filing tests."""
        company = create_company(sample_company_data, session=db_session)
        return company

    @pytest.fixture
    def test_filing_data(self, test_company, sample_filing_data):
        """Create filing data with valid company_id."""
        data = sample_filing_data.copy()
        data["company_id"] = test_company.id
        return data

    def test_create_filing(self, db_session, test_company, test_filing_data):
        """Test creating a new filing."""
        # Create filing
        filing = create_filing(test_filing_data, session=db_session)

        # Verify filing was created
        assert filing.id is not None
        assert filing.filing_type == test_filing_data["filing_type"]
        assert filing.accession_number == test_filing_data["accession_number"]
        assert filing.company_id == test_company.id

    def test_create_filing_unique_accession(self, db_session, test_company, test_filing_data):
        """Test that accession number must be unique."""
        # Create a filing
        filing1 = create_filing(test_filing_data, session=db_session)

        # Try to create another filing with the same accession number
        duplicate_data = test_filing_data.copy()
        duplicate_data["filing_type"] = "8-K"  # Change something but keep accession number

        # This should raise an IntegrityError due to unique constraint
        with pytest.raises(IntegrityError):
            filing2 = create_filing(duplicate_data, session=db_session)

    def test_get_filing_by_id(self, db_session, test_company, test_filing_data):
        """Test retrieving a filing by ID."""
        # Create a filing
        filing = create_filing(test_filing_data, session=db_session)

        # Get filing by ID
        retrieved_filing = get_filing_by_id(filing.id, session=db_session)

        # Verify it's the same filing
        assert retrieved_filing.id == filing.id
        assert retrieved_filing.filing_type == filing.filing_type
        assert retrieved_filing.accession_number == filing.accession_number

    def test_get_filing_by_accession_number(self, db_session, test_company, test_filing_data):
        """Test retrieving a filing by accession number."""
        # Create a filing
        filing = create_filing(test_filing_data, session=db_session)

        # Get filing by accession number
        retrieved_filing = get_filing_by_accession_number(
            test_filing_data["accession_number"], session=db_session
        )

        # Verify it's the same filing
        assert retrieved_filing.id == filing.id
        assert retrieved_filing.filing_type == filing.filing_type

    def test_get_filings_by_company_id(self, db_session, test_company, test_filing_data):
        """Test retrieving filings by company ID."""
        # Create a filing
        filing = create_filing(test_filing_data, session=db_session)

        # Create a second filing for the same company
        data2 = test_filing_data.copy()
        data2["accession_number"] = "0001234567-23-000456"
        filing2 = create_filing(data2, session=db_session)

        # Get filings by company ID
        filings = get_filings_by_company_id(test_company.id, session=db_session)

        # Verify we got both filings
        assert len(filings) == 2
        assert {f.accession_number for f in filings} == {
            test_filing_data["accession_number"],
            data2["accession_number"]
        }

    def test_get_filings_by_type(self, db_session, test_company, test_filing_data):
        """Test retrieving filings by filing type."""
        # Create a 10-K filing
        filing_10k = create_filing(test_filing_data, session=db_session)  # 10-K by default

        # Create an 8-K filing
        data_8k = test_filing_data.copy()
        data_8k["accession_number"] = "0001234567-23-000456"
        data_8k["filing_type"] = "8-K"
        filing_8k = create_filing(data_8k, session=db_session)

        # Get 10-K filings
        filings_10k = get_filings_by_type("10-K", session=db_session)

        # Verify we got only the 10-K filing
        assert len(filings_10k) == 1
        assert filings_10k[0].id == filing_10k.id
        assert filings_10k[0].filing_type == "10-K"

    def test_get_filings_by_date_range(self, db_session, test_company, test_filing_data):
        """Test retrieving filings by date range."""
        # Create filings with different dates
        filing1 = create_filing(test_filing_data, session=db_session)  # 2023-03-15

        # Create an earlier filing
        data2 = test_filing_data.copy()
        data2["accession_number"] = "0001234567-23-000456"
        data2["filing_date"] = datetime.strptime("2023-01-15", "%Y-%m-%d")
        filing2 = create_filing(data2, session=db_session)

        # Create a later filing
        data3 = test_filing_data.copy()
        data3["accession_number"] = "0001234567-23-000789"
        data3["filing_date"] = datetime.strptime("2023-05-15", "%Y-%m-%d")
        filing3 = create_filing(data3, session=db_session)

        # Get filings within a specific date range
        start_date = datetime.strptime("2023-02-01", "%Y-%m-%d")
        end_date = datetime.strptime("2023-04-30", "%Y-%m-%d")
        filings = get_filings_by_date_range(start_date, end_date, session=db_session)

        # Verify we got only the middle filing
        assert len(filings) == 1
        assert filings[0].id == filing1.id

    def test_update_filing(self, db_session, test_company, test_filing_data):
        """Test updating a filing."""
        # Create a filing
        filing = create_filing(test_filing_data, session=db_session)

        # Update filing
        updated_data = {
            "description": "Updated filing description",
            "data": {"new_key": "new_value"}
        }
        updated_filing = update_filing(filing.id, updated_data, session=db_session)

        # Verify filing was updated
        assert updated_filing.description == updated_data["description"]
        assert updated_filing.data == updated_data["data"]
        assert updated_filing.filing_type == test_filing_data["filing_type"]  # Unchanged field

    def test_delete_filing(self, db_session, test_company, test_filing_data):
        """Test deleting a filing."""
        # Create a filing
        filing = create_filing(test_filing_data, session=db_session)

        # Delete filing
        result = delete_filing(filing.id, session=db_session)

        # Verify filing was deleted
        assert result is True
        assert get_filing_by_id(filing.id, session=db_session) is None

    def test_get_all_filings(self, db_session, test_company, test_filing_data):
        """Test retrieving all filings."""
        # Create multiple filings
        filing1 = create_filing(test_filing_data, session=db_session)

        # Create a second filing
        data2 = test_filing_data.copy()
        data2["accession_number"] = "0001234567-23-000456"
        filing2 = create_filing(data2, session=db_session)

        # Get all filings
        filings = get_all_filings(session=db_session)

        # Verify we got both filings
        assert len(filings) == 2
        assert {f.accession_number for f in filings} == {
            test_filing_data["accession_number"],
            data2["accession_number"]
        }

    def test_upsert_filing_insert(self, db_session, test_company, test_filing_data):
        """Test upserting a new filing (insert case)."""
        # Upsert new filing
        filing = upsert_filing(
            test_filing_data["accession_number"],
            test_filing_data,
            session=db_session
        )

        # Verify filing was inserted
        assert filing.id is not None
        assert filing.filing_type == test_filing_data["filing_type"]
        assert filing.accession_number == test_filing_data["accession_number"]

    def test_upsert_filing_update(self, db_session, test_company, test_filing_data):
        """Test upserting an existing filing (update case)."""
        # Create a filing
        filing = create_filing(test_filing_data, session=db_session)

        # Upsert with updated data
        updated_data = {
            "description": "Updated via upsert",
            "data": {"updated": True}
        }
        updated_filing = upsert_filing(
            test_filing_data["accession_number"],
            updated_data,
            session=db_session
        )

        # Verify filing was updated
        assert updated_filing.id == filing.id
        assert updated_filing.description == updated_data["description"]
        assert updated_filing.data == updated_data["data"]

    def test_filing_to_dict(self, db_session, test_company, test_filing_data):
        """Test converting a filing to dictionary."""
        # Create a filing
        filing = create_filing(test_filing_data, session=db_session)

        # Convert to dict
        filing_dict = filing.to_dict()

        # Verify dictionary has expected fields
        assert isinstance(filing_dict, dict)
        assert filing_dict["filing_type"] == test_filing_data["filing_type"]
        assert filing_dict["accession_number"] == test_filing_data["accession_number"]
        assert filing_dict["company_id"] == test_company.id

    def test_company_filing_relationship(self, db_session, test_company, test_filing_data):
        """Test the relationship between Company and Filing."""
        # Create a filing
        filing = create_filing(test_filing_data, session=db_session)

        # Get company from filing
        assert filing.company is not None
        assert filing.company.id == test_company.id
        assert filing.company.name == test_company.name

        # Get filings from company
        company = db_session.get(Company, test_company.id)
        assert company.filings is not None
        assert len(company.filings) == 1
        assert company.filings[0].id == filing.id
        assert company.filings[0].filing_type == filing.filing_type