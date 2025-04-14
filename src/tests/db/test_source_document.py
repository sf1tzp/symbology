import datetime
import pytest
from sqlalchemy.orm import Session

from src.ingestion.database import crud_source_document
from src.ingestion.database import crud_company
from src.ingestion.database import crud_filing
from src.ingestion.database.models import SourceDocument


@pytest.fixture
def sample_source_document_data():
    return {
        "document_type": "exhibit",
        "document_name": "Exhibit 10.1 - Credit Agreement",
        "content": "This is the content of a sample source document that would be part of a filing.",
        "url": "https://www.sec.gov/Archives/edgar/data/123456/000123456789012345/ex10-1.htm"
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


def test_create_source_document(db_session, sample_company, sample_filing, sample_source_document_data):
    # Create source document
    source_doc = crud_source_document.create_source_document(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        document_type=sample_source_document_data["document_type"],
        document_name=sample_source_document_data["document_name"],
        content=sample_source_document_data["content"],
        url=sample_source_document_data["url"],
    )

    # Check that the source document was created successfully
    assert source_doc.id is not None
    assert source_doc.filing_id == sample_filing.id
    assert source_doc.company_id == sample_company.id
    assert source_doc.document_type == sample_source_document_data["document_type"]
    assert source_doc.document_name == sample_source_document_data["document_name"]
    assert source_doc.content == sample_source_document_data["content"]
    assert source_doc.url == sample_source_document_data["url"]


def test_get_source_document(db_session, sample_company, sample_filing, sample_source_document_data):
    # Create source document
    source_doc = crud_source_document.create_source_document(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        document_type=sample_source_document_data["document_type"],
        document_name=sample_source_document_data["document_name"],
        content=sample_source_document_data["content"],
        url=sample_source_document_data["url"],
    )

    # Retrieve the source document
    retrieved = crud_source_document.get_source_document(db_session, source_doc.id)

    # Check that we got the right object
    assert retrieved.id == source_doc.id
    assert retrieved.content == sample_source_document_data["content"]
    assert retrieved.document_type == sample_source_document_data["document_type"]
    assert retrieved.document_name == sample_source_document_data["document_name"]


def test_get_source_documents_by_filing_id(db_session, sample_company, sample_filing, sample_source_document_data):
    # Create multiple source documents for the same filing
    source_doc1 = crud_source_document.create_source_document(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        document_type=sample_source_document_data["document_type"],
        document_name=sample_source_document_data["document_name"],
        content=sample_source_document_data["content"],
        url=sample_source_document_data["url"],
    )

    source_doc2 = crud_source_document.create_source_document(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        document_type="attachment",
        document_name="Attachment 1 - Supplementary Material",
        content="This is additional content for a different source document.",
        url="https://www.sec.gov/Archives/edgar/data/123456/000123456789012345/attachment1.htm",
    )

    # Retrieve the source documents by filing id
    retrieved = crud_source_document.get_source_documents_by_filing_id(db_session, sample_filing.id)

    # Check that we got both documents
    assert len(retrieved) == 2
    assert {doc.id for doc in retrieved} == {source_doc1.id, source_doc2.id}
    assert all(doc.filing_id == sample_filing.id for doc in retrieved)


def test_get_source_documents_by_company_id(db_session, sample_company, sample_filing, sample_source_document_data):
    # Create source document
    source_doc = crud_source_document.create_source_document(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        document_type=sample_source_document_data["document_type"],
        document_name=sample_source_document_data["document_name"],
        content=sample_source_document_data["content"],
        url=sample_source_document_data["url"],
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

    # Create another source document for the second filing
    another_source_doc = crud_source_document.create_source_document(
        db=db_session,
        filing_id=another_filing.id,
        company_id=sample_company.id,
        report_date=another_filing.report_date,
        document_type="supplementary",
        document_name="Supplementary Data",
        content="This is a source document for another filing.",
        url="https://www.sec.gov/Archives/edgar/data/123456/000123456789012346/supp.htm",
    )

    # Retrieve all source documents for the company
    documents = crud_source_document.get_source_documents_by_company_id(db_session, sample_company.id)

    # Check that we got both source documents
    assert len(documents) == 2

    # Check that the source documents are for the correct company
    for doc in documents:
        assert doc.company_id == sample_company.id


def test_get_source_documents_by_type(db_session, sample_company, sample_filing, sample_source_document_data):
    # Create source documents of different types
    exhibit_doc = crud_source_document.create_source_document(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        document_type="exhibit",
        document_name="Exhibit 10.1",
        content="This is an exhibit document.",
        url="https://www.sec.gov/Archives/edgar/data/123456/000123456789012345/ex10-1.htm",
    )

    attachment_doc = crud_source_document.create_source_document(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        document_type="attachment",
        document_name="Attachment 1",
        content="This is an attachment document.",
        url="https://www.sec.gov/Archives/edgar/data/123456/000123456789012345/att1.htm",
    )

    supplementary_doc = crud_source_document.create_source_document(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        document_type="supplementary",
        document_name="Supplementary Data",
        content="This is a supplementary document.",
        url="https://www.sec.gov/Archives/edgar/data/123456/000123456789012345/supp.htm",
    )

    # Retrieve by document type
    exhibit_docs = crud_source_document.get_source_documents_by_type(db_session, "exhibit")
    attachment_docs = crud_source_document.get_source_documents_by_type(db_session, "attachment")
    supplementary_docs = crud_source_document.get_source_documents_by_type(db_session, "supplementary")

    # Check that we got the right documents for each type
    assert len(exhibit_docs) == 1
    assert exhibit_docs[0].id == exhibit_doc.id
    assert exhibit_docs[0].document_type == "exhibit"

    assert len(attachment_docs) == 1
    assert attachment_docs[0].id == attachment_doc.id
    assert attachment_docs[0].document_type == "attachment"

    assert len(supplementary_docs) == 1
    assert supplementary_docs[0].id == supplementary_doc.id
    assert supplementary_docs[0].document_type == "supplementary"


def test_update_source_document(db_session, sample_company, sample_filing, sample_source_document_data):
    # Create source document
    source_doc = crud_source_document.create_source_document(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        document_type=sample_source_document_data["document_type"],
        document_name=sample_source_document_data["document_name"],
        content=sample_source_document_data["content"],
        url=sample_source_document_data["url"],
    )

    # Update content and document type
    updated_content = "This is updated content for the source document."
    updated_document_type = "updated_exhibit"
    updated_document_name = "Updated Exhibit Name"
    updated_url = "https://updated-url.example.com"

    updated = crud_source_document.update_source_document(
        db_session,
        source_doc.id,
        content=updated_content,
        document_type=updated_document_type,
        document_name=updated_document_name,
        url=updated_url
    )

    # Check that the update was applied
    assert updated.content == updated_content
    assert updated.document_type == updated_document_type
    assert updated.document_name == updated_document_name
    assert updated.url == updated_url

    # Verify in the database directly
    db_source_doc = db_session.query(SourceDocument).filter(SourceDocument.id == source_doc.id).first()
    assert db_source_doc.content == updated_content
    assert db_source_doc.document_type == updated_document_type
    assert db_source_doc.document_name == updated_document_name
    assert db_source_doc.url == updated_url


def test_partial_update_source_document(db_session, sample_company, sample_filing, sample_source_document_data):
    # Create source document
    source_doc = crud_source_document.create_source_document(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        document_type=sample_source_document_data["document_type"],
        document_name=sample_source_document_data["document_name"],
        content=sample_source_document_data["content"],
        url=sample_source_document_data["url"],
    )

    # Update only content, leaving other fields unchanged
    updated_content = "This is updated content only."

    updated = crud_source_document.update_source_document(
        db_session,
        source_doc.id,
        content=updated_content
    )

    # Check that only content was updated and other fields remain unchanged
    assert updated.content == updated_content
    assert updated.document_type == sample_source_document_data["document_type"]
    assert updated.document_name == sample_source_document_data["document_name"]
    assert updated.url == sample_source_document_data["url"]


def test_delete_source_document(db_session, sample_company, sample_filing, sample_source_document_data):
    # Create source document
    source_doc = crud_source_document.create_source_document(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        document_type=sample_source_document_data["document_type"],
        document_name=sample_source_document_data["document_name"],
        content=sample_source_document_data["content"],
        url=sample_source_document_data["url"],
    )

    # Delete the source document
    result = crud_source_document.delete_source_document(db_session, source_doc.id)
    assert result is True

    # Verify it's gone
    assert crud_source_document.get_source_document(db_session, source_doc.id) is None


def test_delete_nonexistent_source_document(db_session):
    # Try to delete a source document that doesn't exist
    result = crud_source_document.delete_source_document(db_session, 999999)
    assert result is False


def test_filing_source_document_relationship(db_session, sample_company, sample_filing, sample_source_document_data):
    # Create source document
    source_doc = crud_source_document.create_source_document(
        db=db_session,
        filing_id=sample_filing.id,
        company_id=sample_company.id,
        report_date=sample_filing.report_date,
        document_type=sample_source_document_data["document_type"],
        document_name=sample_source_document_data["document_name"],
        content=sample_source_document_data["content"],
        url=sample_source_document_data["url"],
    )

    # Get the filing from the database with relationship loaded
    filing = db_session.query(crud_filing.Filing).filter(crud_filing.Filing.id == sample_filing.id).first()

    # Check that the source document is accessible through the filing relationship
    assert len(filing.source_documents) == 1
    assert filing.source_documents[0].id == source_doc.id
    assert filing.source_documents[0].document_type == sample_source_document_data["document_type"]
    assert filing.source_documents[0].document_name == sample_source_document_data["document_name"]