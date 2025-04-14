import datetime
import pytest
from sqlalchemy.orm import Session

from src.python.database import crud_business_description
from src.python.database import crud_company
from src.python.database import crud_filing
from src.python.database.models import BusinessDescription


@pytest.fixture
def sample_business_description_data():
    return {
        "content": "This is a sample business description with details about operations, products, and markets."
    }


@pytest.fixture
def sample_company(db_session, sample_company_data):
    # Create a test company record using the sample data fixture
    company = crud_company.create_company(company_data=sample_company_data, session=db_session)
    return company


@pytest.fixture
def sample_filing(db_session, sample_filing_data, sample_company):
    # Create a test filing record using the sample data fixture, linked to the sample company
    filing_data = sample_filing_data.copy()
    filing_data["company_id"] = sample_company.id
    filing = crud_filing.create_filing(filing_data=filing_data, session=db_session)
    return filing


def test_create_business_description(db_session, sample_company, sample_filing, sample_business_description_data):
    # Create business description
    business_desc = crud_business_description.create_business_description(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        content=sample_business_description_data["content"],
    )

    # Check that the business description was created successfully
    assert business_desc.id is not None
    assert business_desc.filing_id == sample_filing.id
    assert business_desc.company_id == sample_company.id
    assert business_desc.content == sample_business_description_data["content"]


def test_get_business_description(db_session, sample_company, sample_filing, sample_business_description_data):
    # Create business description
    business_desc = crud_business_description.create_business_description(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        content=sample_business_description_data["content"],
    )

    # Retrieve the business description
    retrieved = crud_business_description.get_business_description(db_session, business_desc.id)

    # Check that we got the right object
    assert retrieved.id == business_desc.id
    assert retrieved.content == sample_business_description_data["content"]


def test_get_business_description_by_filing_id(db_session, sample_company, sample_filing, sample_business_description_data):
    # Create business description
    business_desc = crud_business_description.create_business_description(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        content=sample_business_description_data["content"],
    )

    # Retrieve the business description by filing id
    retrieved = crud_business_description.get_business_description_by_filing_id(db_session, sample_filing.id)

    # Check that we got the right object
    assert retrieved.id == business_desc.id
    assert retrieved.filing_id == sample_filing.id


def test_get_business_descriptions_by_company_id(db_session, sample_company, sample_filing, sample_business_description_data):
    # Create business description
    business_desc = crud_business_description.create_business_description(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        content=sample_business_description_data["content"],
    )

    # Create another filing for the same company
    another_filing = crud_filing.create_filing(
        filing_data={
            "company_id": sample_company.id,
            "filing_type": "10-K",
            "accession_number": "0001234567-23-000002",
            "filing_date": datetime.datetime(2023, 3, 1),
            "report_date": datetime.datetime(2022, 12, 31)
        },
        session=db_session
    )

    # Create another business description for the second filing
    another_business_desc = crud_business_description.create_business_description(
        db=db_session,
        filing_id=another_filing.id,
        company_id=sample_company.id,
        report_date=another_filing.report_date,
        content="Another year's business description.",
    )

    # Retrieve all business descriptions for the company
    descriptions = crud_business_description.get_business_descriptions_by_company_id(db_session, sample_company.id)

    # Check that we got two business descriptions
    assert len(descriptions) == 2

    # Check that the business descriptions are for the correct company
    for desc in descriptions:
        assert desc.company_id == sample_company.id


def test_update_business_description(db_session, sample_company, sample_filing, sample_business_description_data):
    # Create business description
    business_desc = crud_business_description.create_business_description(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        content=sample_business_description_data["content"],
    )

    # Update the content
    updated_content = "This is an updated business description."
    updated = crud_business_description.update_business_description(
        db_session, business_desc.id, updated_content
    )

    # Check that the update was applied
    assert updated.content == updated_content

    # Verify in the database directly
    db_business_desc = db_session.query(BusinessDescription).filter(BusinessDescription.id == business_desc.id).first()
    assert db_business_desc.content == updated_content


def test_delete_business_description(db_session, sample_company, sample_filing, sample_business_description_data):
    # Create business description
    business_desc = crud_business_description.create_business_description(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        content=sample_business_description_data["content"],
    )

    # Delete the business description
    result = crud_business_description.delete_business_description(db_session, business_desc.id)
    assert result is True

    # Verify it's gone
    assert crud_business_description.get_business_description(db_session, business_desc.id) is None


def test_delete_nonexistent_business_description(db_session):
    # Try to delete a business description that doesn't exist
    result = crud_business_description.delete_business_description(db_session, 999999)
    assert result is False