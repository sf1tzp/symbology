import datetime
import pytest
from sqlalchemy.orm import Session

from src.python.database import crud_risk_factors
from src.python.database import crud_company
from src.python.database import crud_filing
from src.python.database.models import RiskFactors


@pytest.fixture
def sample_risk_factors_data():
    return {
        "content": "This section details the various risk factors that could affect our business operations, financial condition, and results."
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


def test_create_risk_factors(db_session, sample_company, sample_filing, sample_risk_factors_data):
    # Create risk factors
    risk_factors = crud_risk_factors.create_risk_factors(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        content=sample_risk_factors_data["content"],
    )

    # Check that the risk factors were created successfully
    assert risk_factors.id is not None
    assert risk_factors.filing_id == sample_filing.id
    assert risk_factors.company_id == sample_company.id
    assert risk_factors.content == sample_risk_factors_data["content"]


def test_get_risk_factors(db_session, sample_company, sample_filing, sample_risk_factors_data):
    # Create risk factors
    risk_factors = crud_risk_factors.create_risk_factors(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        content=sample_risk_factors_data["content"],
    )

    # Retrieve the risk factors
    retrieved = crud_risk_factors.get_risk_factors(db_session, risk_factors.id)

    # Check that we got the right object
    assert retrieved.id == risk_factors.id
    assert retrieved.content == sample_risk_factors_data["content"]


def test_get_risk_factors_by_filing_id(db_session, sample_company, sample_filing, sample_risk_factors_data):
    # Create risk factors
    risk_factors = crud_risk_factors.create_risk_factors(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        content=sample_risk_factors_data["content"],
    )

    # Retrieve the risk factors by filing id
    retrieved = crud_risk_factors.get_risk_factors_by_filing_id(db_session, sample_filing.id)

    # Check that we got the right object
    assert retrieved.id == risk_factors.id
    assert retrieved.filing_id == sample_filing.id


def test_get_risk_factors_by_company_id(db_session, sample_company, sample_filing, sample_risk_factors_data):
    # Create risk factors
    risk_factors = crud_risk_factors.create_risk_factors(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        content=sample_risk_factors_data["content"],
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

    # Create another risk factors for the second filing
    another_risk_factors = crud_risk_factors.create_risk_factors(
        db=db_session,
        filing_id=another_filing.id,
        company_id=sample_company.id,
        report_date=another_filing.report_date,
        content="Another year's risk factors description.",
    )

    # Retrieve all risk factors for the company
    risk_factors_list = crud_risk_factors.get_risk_factors_by_company_id(db_session, sample_company.id)

    # Check that we got two risk factors
    assert len(risk_factors_list) == 2

    # Check that the risk factors are for the correct company
    for rf in risk_factors_list:
        assert rf.company_id == sample_company.id


def test_update_risk_factors(db_session, sample_company, sample_filing, sample_risk_factors_data):
    # Create risk factors
    risk_factors = crud_risk_factors.create_risk_factors(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        content=sample_risk_factors_data["content"],
    )

    # Update the content
    updated_content = "This is updated risk factors content."
    updated = crud_risk_factors.update_risk_factors(
        db_session, risk_factors.id, updated_content
    )

    # Check that the update was applied
    assert updated.content == updated_content

    # Verify in the database directly
    db_risk_factors = db_session.query(RiskFactors).filter(RiskFactors.id == risk_factors.id).first()
    assert db_risk_factors.content == updated_content


def test_delete_risk_factors(db_session, sample_company, sample_filing, sample_risk_factors_data):
    # Create risk factors
    risk_factors = crud_risk_factors.create_risk_factors(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        content=sample_risk_factors_data["content"],
    )

    # Delete the risk factors
    result = crud_risk_factors.delete_risk_factors(db_session, risk_factors.id)
    assert result is True

    # Verify it's gone
    assert crud_risk_factors.get_risk_factors(db_session, risk_factors.id) is None


def test_delete_nonexistent_risk_factors(db_session):
    # Try to delete risk factors that don't exist
    result = crud_risk_factors.delete_risk_factors(db_session, 999999)
    assert result is False