import datetime
import pytest
from sqlalchemy.orm import Session

from src.python.database import crud_management_discussion
from src.python.database import crud_company
from src.python.database import crud_filing
from src.python.database.models import ManagementDiscussion


@pytest.fixture
def sample_management_discussion_data():
    return {
        "content": "Management's discussion and analysis of financial condition and results of operations for the fiscal year."
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


def test_create_management_discussion(db_session, sample_company, sample_filing, sample_management_discussion_data):
    # Create management discussion
    mgmt_discussion = crud_management_discussion.create_management_discussion(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        content=sample_management_discussion_data["content"],
    )

    # Check that the management discussion was created successfully
    assert mgmt_discussion.id is not None
    assert mgmt_discussion.filing_id == sample_filing.id
    assert mgmt_discussion.company_id == sample_company.id
    assert mgmt_discussion.content == sample_management_discussion_data["content"]


def test_get_management_discussion(db_session, sample_company, sample_filing, sample_management_discussion_data):
    # Create management discussion
    mgmt_discussion = crud_management_discussion.create_management_discussion(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        content=sample_management_discussion_data["content"],
    )

    # Retrieve the management discussion
    retrieved = crud_management_discussion.get_management_discussion(db_session, mgmt_discussion.id)
    
    # Check that we got the right object
    assert retrieved.id == mgmt_discussion.id
    assert retrieved.content == sample_management_discussion_data["content"]


def test_get_management_discussion_by_filing_id(db_session, sample_company, sample_filing, sample_management_discussion_data):
    # Create management discussion
    mgmt_discussion = crud_management_discussion.create_management_discussion(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        content=sample_management_discussion_data["content"],
    )

    # Retrieve the management discussion by filing id
    retrieved = crud_management_discussion.get_management_discussion_by_filing_id(db_session, sample_filing.id)
    
    # Check that we got the right object
    assert retrieved.id == mgmt_discussion.id
    assert retrieved.filing_id == sample_filing.id


def test_get_management_discussions_by_company_id(db_session, sample_company, sample_filing, sample_management_discussion_data):
    # Create management discussion
    mgmt_discussion = crud_management_discussion.create_management_discussion(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        content=sample_management_discussion_data["content"],
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
    
    # Create another management discussion for the second filing
    another_mgmt_discussion = crud_management_discussion.create_management_discussion(
        db=db_session,
        filing_id=another_filing.id,
        company_id=sample_company.id,
        report_date=another_filing.report_date,
        content="Another year's management discussion and analysis.",
    )

    # Retrieve all management discussions for the company
    discussions = crud_management_discussion.get_management_discussions_by_company_id(db_session, sample_company.id)
    
    # Check that we got two management discussions
    assert len(discussions) == 2
    
    # Check that the management discussions are for the correct company
    for disc in discussions:
        assert disc.company_id == sample_company.id


def test_update_management_discussion(db_session, sample_company, sample_filing, sample_management_discussion_data):
    # Create management discussion
    mgmt_discussion = crud_management_discussion.create_management_discussion(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        content=sample_management_discussion_data["content"],
    )

    # Update the content
    updated_content = "This is updated management discussion content."
    updated = crud_management_discussion.update_management_discussion(
        db_session, mgmt_discussion.id, updated_content
    )
    
    # Check that the update was applied
    assert updated.content == updated_content
    
    # Verify in the database directly
    db_mgmt_discussion = db_session.query(ManagementDiscussion).filter(ManagementDiscussion.id == mgmt_discussion.id).first()
    assert db_mgmt_discussion.content == updated_content


def test_delete_management_discussion(db_session, sample_company, sample_filing, sample_management_discussion_data):
    # Create management discussion
    mgmt_discussion = crud_management_discussion.create_management_discussion(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        content=sample_management_discussion_data["content"],
    )

    # Delete the management discussion
    result = crud_management_discussion.delete_management_discussion(db_session, mgmt_discussion.id)
    assert result is True
    
    # Verify it's gone
    assert crud_management_discussion.get_management_discussion(db_session, mgmt_discussion.id) is None


def test_delete_nonexistent_management_discussion(db_session):
    # Try to delete a management discussion that doesn't exist
    result = crud_management_discussion.delete_management_discussion(db_session, 999999)
    assert result is False