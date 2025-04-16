from datetime import date
from typing import Any, Dict, List
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from src.database.companies import Company

# Import the Document model and functions
from src.database.documents import create_document, delete_document, Document, get_document, get_document_ids, update_document
from src.database.filings import Filing


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

# Sample document data fixtures
@pytest.fixture
def sample_document_data(create_test_company, create_test_filing) -> Dict[str, Any]:
    """Sample document data for testing."""
    return {
        "company_id": create_test_company.id,
        "filing_id": create_test_filing.id,
        "document_name": "10-K Annual Report",
        "content": "This is the annual report content for fiscal year 2023."
    }

@pytest.fixture
def sample_document_data_minimal(create_test_company) -> Dict[str, Any]:
    """Minimal document data with only required fields."""
    return {
        "company_id": create_test_company.id,
        "document_name": "Press Release",
        "content": "Company announces new product launch."
    }

@pytest.fixture
def multiple_document_data(create_test_company, create_test_filing) -> List[Dict[str, Any]]:
    """Generate data for multiple documents for the same filing."""
    company_id = create_test_company.id
    filing_id = create_test_filing.id
    return [
        {
            "company_id": company_id,
            "filing_id": filing_id,
            "document_name": "10-K",
            "content": "Main 10-K document content."
        },
        {
            "company_id": company_id,
            "filing_id": filing_id,
            "document_name": "EX-101.INS",
            "content": "XBRL Instance Document."
        },
        {
            "company_id": company_id,
            "filing_id": filing_id,
            "document_name": "EX-10.1",
            "content": "Material contract exhibit content."
        }
    ]

# Test cases for Document CRUD operations
def test_create_document(db_session, sample_document_data):
    """Test creating a document."""
    # Create document
    document = Document(**sample_document_data)
    db_session.add(document)
    db_session.commit()

    # Verify it was created
    assert document.id is not None
    assert document.document_name == "10-K Annual Report"
    assert document.content is not None

    # Verify it can be retrieved from the database
    retrieved = db_session.query(Document).filter_by(id=document.id).first()
    assert retrieved is not None
    assert retrieved.document_name == document.document_name
    assert retrieved.content == document.content

def test_create_minimal_document(db_session, sample_document_data_minimal):
    """Test creating a document with only required fields."""
    document = Document(**sample_document_data_minimal)
    db_session.add(document)
    db_session.commit()

    # Verify it was created correctly
    assert document.id is not None
    assert document.document_name == "Press Release"
    assert document.filing_id is None  # Should be None since not provided

def test_document_relationships(db_session, create_test_company, create_test_filing, sample_document_data):
    """Test the relationships between documents, filings, and companies."""
    # Create a document
    document = Document(**sample_document_data)
    db_session.add(document)
    db_session.commit()

    # Verify the company relationship
    assert document.company_id == create_test_company.id
    assert document.company.name == create_test_company.name

    # Verify the filing relationship
    assert document.filing_id == create_test_filing.id
    assert document.filing.filing_type == create_test_filing.filing_type

    # Check from the company side
    company = db_session.query(Company).filter_by(id=create_test_company.id).first()
    assert len(company.documents) > 0
    assert company.documents[0].id == document.id

    # Check from the filing side
    filing = db_session.query(Filing).filter_by(id=create_test_filing.id).first()
    assert len(filing.documents) > 0
    assert filing.documents[0].id == document.id

def test_get_document_by_id(db_session, sample_document_data):
    """Test retrieving a document by ID using the get_document function."""
    # First create a document
    document = Document(**sample_document_data)
    db_session.add(document)
    db_session.commit()

    # Mock the db_session global with our test session
    import src.database.documents as documents_module
    original_get_db_session = documents_module.get_db_session
    documents_module.get_db_session = lambda: db_session

    try:
        # Test the get_document function
        retrieved = get_document(document.id)
        assert retrieved is not None
        assert retrieved.id == document.id
        assert retrieved.document_name == "10-K Annual Report"

        # Test with non-existent ID
        non_existent = get_document(uuid.uuid4())
        assert non_existent is None
    finally:
        # Restore the original function
        documents_module.get_db_session = original_get_db_session

def test_create_document_function(db_session, sample_document_data):
    """Test the create_document helper function."""
    # Mock the db_session global
    import src.database.documents as documents_module
    original_get_db_session = documents_module.get_db_session
    documents_module.get_db_session = lambda: db_session

    try:
        # Create a document using the helper function
        document = create_document(sample_document_data)

        # Verify it was created correctly
        assert document.id is not None
        assert document.document_name == "10-K Annual Report"
        assert document.content is not None

        # Verify it exists in the database
        retrieved = db_session.query(Document).filter_by(id=document.id).first()
        assert retrieved is not None
        assert retrieved.document_name == document.document_name
    finally:
        # Restore the original function
        documents_module.get_db_session = original_get_db_session

def test_update_document(db_session, sample_document_data):
    """Test updating a document using the update_document function."""
    # First create a document
    document = Document(**sample_document_data)
    db_session.add(document)
    db_session.commit()

    # Mock the db_session global
    import src.database.documents as documents_module
    original_get_db_session = documents_module.get_db_session
    documents_module.get_db_session = lambda: db_session

    try:
        # Update the document
        updates = {
            "document_name": "Updated 10-K Report",
            "content": "Updated content for the annual report."
        }

        updated = update_document(document.id, updates)

        # Verify updates were applied
        assert updated is not None
        assert updated.document_name == "Updated 10-K Report"
        assert updated.content == "Updated content for the annual report."

        # Check that other fields weren't changed
        assert updated.company_id == document.company_id
        assert updated.filing_id == document.filing_id

        # Test updating non-existent document
        non_existent = update_document(uuid.uuid4(), {"document_name": "Test"})
        assert non_existent is None
    finally:
        # Restore the original function
        documents_module.get_db_session = original_get_db_session

def test_delete_document(db_session, sample_document_data):
    """Test deleting a document using the delete_document function."""
    # First create a document
    document = Document(**sample_document_data)
    db_session.add(document)
    db_session.commit()
    document_id = document.id

    # Mock the db_session global
    import src.database.documents as documents_module
    original_get_db_session = documents_module.get_db_session
    documents_module.get_db_session = lambda: db_session

    try:
        # Delete the document
        result = delete_document(document_id)
        assert result is True

        # Verify it was deleted
        assert db_session.query(Document).filter_by(id=document_id).first() is None

        # Test deleting non-existent document
        result = delete_document(uuid.uuid4())
        assert result is False
    finally:
        # Restore the original function
        documents_module.get_db_session = original_get_db_session

def test_get_document_ids(db_session, multiple_document_data):
    """Test retrieving all document IDs."""
    # Create multiple documents
    document_ids = []
    for data in multiple_document_data:
        document = Document(**data)
        db_session.add(document)
        db_session.commit()
        document_ids.append(document.id)

    # Mock the db_session global
    import src.database.documents as documents_module
    original_get_db_session = documents_module.get_db_session
    documents_module.get_db_session = lambda: db_session

    try:
        # Get all document IDs
        ids = get_document_ids()

        # Verify all created documents are included
        for document_id in document_ids:
            assert document_id in ids

        # Verify count matches
        assert len(ids) >= len(document_ids)
    finally:
        # Restore the original function
        documents_module.get_db_session = original_get_db_session

def test_update_with_invalid_attributes(db_session, sample_document_data):
    """Test updating a document with invalid attributes."""
    # First create a document
    document = Document(**sample_document_data)
    db_session.add(document)
    db_session.commit()

    # Mock the db_session global
    import src.database.documents as documents_module
    original_get_db_session = documents_module.get_db_session
    documents_module.get_db_session = lambda: db_session

    try:
        # Update with invalid attribute
        updates = {
            "document_name": "Valid Update",
            "invalid_field": "This field doesn't exist"
        }

        # Should still update valid fields but ignore invalid ones
        updated = update_document(document.id, updates)
        assert updated is not None
        assert updated.document_name == "Valid Update"

        # The invalid field should not be added to the object
        assert not hasattr(updated, "invalid_field")
    finally:
        # Restore the original function
        documents_module.get_db_session = original_get_db_session

def test_get_document_with_string_uuid(db_session, sample_document_data):
    """Test retrieving a document using string representation of UUID."""
    # First create a document
    document = Document(**sample_document_data)
    db_session.add(document)
    db_session.commit()

    # Mock the db_session global
    import src.database.documents as documents_module
    original_get_db_session = documents_module.get_db_session
    documents_module.get_db_session = lambda: db_session

    try:
        # Test get_document with string UUID
        retrieved = get_document(str(document.id))
        assert retrieved is not None
        assert retrieved.id == document.id
    finally:
        # Restore the original function
        documents_module.get_db_session = original_get_db_session

def test_cascade_delete_company(db_session, create_test_company, sample_document_data):
    """Test that deleting a company also deletes its associated documents."""
    # Create a document for the company
    document = Document(**sample_document_data)
    db_session.add(document)
    db_session.commit()
    document_id = document.id

    # Now delete the company
    db_session.delete(create_test_company)
    db_session.commit()

    # Verify that the document was also deleted
    assert db_session.query(Document).filter_by(id=document_id).first() is None

def test_cascade_delete_filing(db_session, create_test_filing, sample_document_data):
    """Test that deleting a filing also deletes its associated documents."""
    # Create a document for the filing
    document = Document(**sample_document_data)
    db_session.add(document)
    db_session.commit()
    document_id = document.id

    # Now delete the filing
    db_session.delete(create_test_filing)
    db_session.commit()

    # Verify that the document was also deleted
    assert db_session.query(Document).filter_by(id=document_id).first() is None

def test_document_without_filing(db_session, create_test_company):
    """Test creating a document without a filing association."""
    # Create document data without filing_id
    document_data = {
        "company_id": create_test_company.id,
        "document_name": "Standalone Document",
        "content": "This document is not associated with any filing."
    }

    # Create document
    document = Document(**document_data)
    db_session.add(document)
    db_session.commit()

    # Verify it was created correctly
    assert document.id is not None
    assert document.document_name == "Standalone Document"
    assert document.filing_id is None
    assert document.filing is None
    assert document.company_id == create_test_company.id
    assert document.company is not None

def test_create_document_with_invalid_company(db_session, sample_document_data):
    """Test creating a document with an invalid company ID."""
    # Modify the document data to have an invalid company ID
    invalid_data = sample_document_data.copy()
    invalid_data["company_id"] = uuid.uuid4()  # Non-existent company ID

    # Create document
    document = Document(**invalid_data)
    db_session.add(document)

    # Should raise IntegrityError due to foreign key constraint
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_create_document_with_invalid_filing(db_session, create_test_company, sample_document_data):
    """Test creating a document with an invalid filing ID."""
    # Modify the document data to have an invalid filing ID
    invalid_data = sample_document_data.copy()
    invalid_data["filing_id"] = uuid.uuid4()  # Non-existent filing ID

    # Create document
    document = Document(**invalid_data)
    db_session.add(document)

    # Should raise IntegrityError due to foreign key constraint
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_create_multiple_documents_for_filing(db_session, create_test_filing, multiple_document_data):
    """Test creating multiple documents for a single filing."""
    # Create multiple documents
    created_documents = []
    for data in multiple_document_data:
        document = Document(**data)
        db_session.add(document)
        db_session.commit()
        created_documents.append(document)

    # Verify all documents were created
    assert len(created_documents) == len(multiple_document_data)

    # Check that they all refer to the same filing
    for document in created_documents:
        assert document.filing_id == create_test_filing.id

    # Check from the filing side
    filing = db_session.query(Filing).filter_by(id=create_test_filing.id).first()
    assert len(filing.documents) == len(multiple_document_data)

def test_find_or_create_document(db_session, create_test_company, create_test_filing):
    """Test the find_or_create_document helper function."""
    # Mock the db_session global
    import src.database.documents as documents_module
    original_get_db_session = documents_module.get_db_session
    documents_module.get_db_session = lambda: db_session

    try:
        # Create a new document using find_or_create
        document = documents_module.find_or_create_document(
            company_id=create_test_company.id,
            filing_id=create_test_filing.id,
            document_name="Risk Factors",
            content="This is the risk factors content."
        )

        assert document is not None
        assert document.document_name == "Risk Factors"
        assert document.content == "This is the risk factors content."
        document_id = document.id

        # Call find_or_create again with the same parameters - should return existing document
        document2 = documents_module.find_or_create_document(
            company_id=create_test_company.id,
            filing_id=create_test_filing.id,
            document_name="Risk Factors",
            content="This is updated risk factors content."
        )

        # Should be same document but with updated content
        assert document2.id == document_id
        assert document2.document_name == "Risk Factors"
        assert document2.content == "This is updated risk factors content."

        # Now test creating a document without a filing ID
        standalone_doc = documents_module.find_or_create_document(
            company_id=create_test_company.id,
            document_name="Standalone Document",
            content="This is a document not associated with a filing.",
            filing_id=None
        )

        assert standalone_doc is not None
        assert standalone_doc.document_name == "Standalone Document"
        assert standalone_doc.filing_id is None
    finally:
        # Restore the original function
        documents_module.get_db_session = original_get_db_session

def test_find_or_create_document_update_existing(db_session, create_test_company, create_test_filing):
    """Test the find_or_create_document helper function when updating an existing document."""
    # First create a document directly
    document_data = {
        "company_id": create_test_company.id,
        "filing_id": create_test_filing.id,
        "document_name": "MD&A",
        "content": "Original management discussion content."
    }
    document = Document(**document_data)
    db_session.add(document)
    db_session.commit()
    document_id = document.id

    # Mock the db_session global
    import src.database.documents as documents_module
    original_get_db_session = documents_module.get_db_session
    documents_module.get_db_session = lambda: db_session

    try:
        # Now try to find or create a document with the same identifiers
        updated_doc = documents_module.find_or_create_document(
            company_id=create_test_company.id,
            filing_id=create_test_filing.id,
            document_name="MD&A",
            content="Updated management discussion content."
        )

        # Should be the same document but with updated content
        assert updated_doc.id == document_id
        assert updated_doc.content == "Updated management discussion content."
    finally:
        # Restore the original function
        documents_module.get_db_session = original_get_db_session

def test_get_documents_by_filing(db_session, create_test_company, create_test_filing, multiple_document_data):
    """Test the get_documents_by_filing helper function."""
    # Create multiple documents for the same filing
    for data in multiple_document_data:
        document = Document(**data)
        db_session.add(document)
    db_session.commit()

    # Mock the db_session global
    import src.database.documents as documents_module
    original_get_db_session = documents_module.get_db_session
    documents_module.get_db_session = lambda: db_session

    try:
        # Get documents for the filing
        documents = documents_module.get_documents_by_filing(create_test_filing.id)

        # Should have the same number of documents as we created
        assert len(documents) == len(multiple_document_data)

        # Check that the document names match what we created
        doc_names = [doc.document_name for doc in documents]
        for data in multiple_document_data:
            assert data["document_name"] in doc_names

        # Test with a filing ID that has no documents
        no_docs = documents_module.get_documents_by_filing(uuid.uuid4())
        assert len(no_docs) == 0
    finally:
        # Restore the original function
        documents_module.get_db_session = original_get_db_session