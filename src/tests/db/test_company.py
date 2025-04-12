import pytest
from sqlalchemy.exc import IntegrityError

from src.python.database.crud_company import (
    create_company,
    delete_company,
    get_all_companies,
    get_companies_by_ticker,
    get_company_by_cik,
    get_company_by_id,
    update_company,
    upsert_company,
)


class TestCompany:
    """Test cases for Company model and CRUD operations."""

    def test_create_company(self, db_session, sample_company_data):
        """Test creating a new company."""
        # Create a company
        company = create_company(sample_company_data, session=db_session)

        # Verify company was created
        assert company.id is not None
        assert company.name == sample_company_data["name"]
        assert company.cik == sample_company_data["cik"]
        assert company.tickers == sample_company_data["tickers"]

    def test_create_company_unique_cik(self, db_session, sample_company_data):
        """Test that CIK must be unique."""
        # Create a company
        company1 = create_company(sample_company_data, session=db_session)

        # Try to create another company with the same CIK
        duplicate_data = sample_company_data.copy()
        duplicate_data["name"] = "Another Company"

        # This should raise an IntegrityError due to unique constraint on CIK
        with pytest.raises(IntegrityError):
            company2 = create_company(duplicate_data, session=db_session)

    def test_get_company_by_id(self, db_session, sample_company_data):
        """Test retrieving a company by ID."""
        # Create a company
        company = create_company(sample_company_data, session=db_session)

        # Get company by ID
        retrieved_company = get_company_by_id(company.id, session=db_session)

        # Verify it's the same company
        assert retrieved_company.id == company.id
        assert retrieved_company.name == company.name
        assert retrieved_company.cik == company.cik

    def test_get_company_by_cik(self, db_session, sample_company_data):
        """Test retrieving a company by CIK."""
        # Create a company
        company = create_company(sample_company_data, session=db_session)

        # Get company by CIK
        retrieved_company = get_company_by_cik(sample_company_data["cik"], session=db_session)

        # Verify it's the same company
        assert retrieved_company.id == company.id
        assert retrieved_company.name == company.name

    def test_get_companies_by_ticker(self, db_session, sample_company_data):
        """Test retrieving companies by ticker."""
        # Create a company
        company = create_company(sample_company_data, session=db_session)

        # Get companies by ticker
        companies = get_companies_by_ticker(sample_company_data["tickers"][0], session=db_session)

        # Verify we got our company
        assert len(companies) == 1
        assert companies[0].id == company.id
        assert companies[0].name == company.name

    def test_update_company(self, db_session, sample_company_data):
        """Test updating a company."""
        # Create a company
        company = create_company(sample_company_data, session=db_session)

        # Update company
        updated_data = {"name": "Updated Company Name", "phone": "999-888-7777"}
        updated_company = update_company(company.id, updated_data, session=db_session)

        # Verify company was updated
        assert updated_company.name == updated_data["name"]
        assert updated_company.phone == updated_data["phone"]
        assert updated_company.cik == sample_company_data["cik"]  # Unchanged field

    def test_delete_company(self, db_session, sample_company_data):
        """Test deleting a company."""
        # Create a company
        company = create_company(sample_company_data, session=db_session)

        # Delete company
        result = delete_company(company.id, session=db_session)

        # Verify company was deleted
        assert result is True
        assert get_company_by_id(company.id, session=db_session) is None

    def test_get_all_companies(self, db_session, sample_company_data):
        """Test retrieving all companies."""
        # Create multiple companies
        company1 = create_company(sample_company_data, session=db_session)

        # Create a second company with different CIK
        data2 = sample_company_data.copy()
        data2["cik"] = 7654321
        data2["name"] = "Second Test Company"
        company2 = create_company(data2, session=db_session)

        # Get all companies
        companies = get_all_companies(session=db_session)

        # Verify we got both companies
        assert len(companies) == 2
        assert {c.name for c in companies} == {company1.name, company2.name}

    def test_upsert_company_insert(self, db_session, sample_company_data):
        """Test upserting a new company (insert case)."""
        # Upsert new company
        company = upsert_company(sample_company_data["cik"], sample_company_data, session=db_session)

        # Verify company was inserted
        assert company.id is not None
        assert company.name == sample_company_data["name"]
        assert company.cik == sample_company_data["cik"]

    def test_upsert_company_update(self, db_session, sample_company_data):
        """Test upserting an existing company (update case)."""
        # Create a company
        company = create_company(sample_company_data, session=db_session)

        # Upsert with updated data
        updated_data = {"name": "Updated Via Upsert", "phone": "111-222-3333"}
        updated_company = upsert_company(sample_company_data["cik"], updated_data, session=db_session)

        # Verify company was updated
        assert updated_company.id == company.id
        assert updated_company.name == updated_data["name"]
        assert updated_company.phone == updated_data["phone"]

    def test_company_to_dict(self, db_session, sample_company_data):
        """Test converting a company to dictionary."""
        # Create a company
        company = create_company(sample_company_data, session=db_session)

        # Convert to dict
        company_dict = company.to_dict()

        # Verify dictionary has expected fields
        assert isinstance(company_dict, dict)
        assert company_dict["name"] == sample_company_data["name"]
        assert company_dict["cik"] == sample_company_data["cik"]
        assert company_dict["tickers"] == sample_company_data["tickers"]