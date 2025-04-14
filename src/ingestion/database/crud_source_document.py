from datetime import datetime
from typing import List, Optional, Union

from sqlalchemy.orm import Session

from .models import SourceDocument


def create_source_document(
    db: Session,
    filing_id: int,
    company_id: int,
    report_date: Union[datetime, str],
    document_type: str,
    document_name: str,
    content: str,
    url: Optional[str] = None,
) -> SourceDocument:
    """
    Create a new source document entry.

    Args:
        db: Database session
        filing_id: ID of the filing
        company_id: ID of the company
        report_date: Date of the report
        document_type: Type of the document
        document_name: Name of the document
        content: Text content of the document
        url: Optional URL to the original document

    Returns:
        The created SourceDocument object
    """
    if isinstance(report_date, str):
        report_date = datetime.strptime(report_date, "%Y-%m-%d")

    db_source_document = SourceDocument(
        filing_id=filing_id,
        company_id=company_id,
        report_date=report_date,
        document_type=document_type,
        document_name=document_name,
        content=content,
        url=url,
    )
    db.add(db_source_document)
    db.commit()
    db.refresh(db_source_document)
    return db_source_document


def get_source_document(db: Session, source_document_id: int) -> Optional[SourceDocument]:
    """
    Get a source document by ID.

    Args:
        db: Database session
        source_document_id: ID of the source document

    Returns:
        The SourceDocument object or None if not found
    """
    return db.query(SourceDocument).filter(SourceDocument.id == source_document_id).first()


def get_source_documents_by_filing_id(db: Session, filing_id: int) -> List[SourceDocument]:
    """
    Get all source documents for a specific filing.

    Args:
        db: Database session
        filing_id: ID of the filing

    Returns:
        List of SourceDocument objects
    """
    return db.query(SourceDocument).filter(SourceDocument.filing_id == filing_id).all()


def get_source_documents_by_company_id(db: Session, company_id: int) -> List[SourceDocument]:
    """
    Get all source documents for a company.

    Args:
        db: Database session
        company_id: ID of the company

    Returns:
        List of SourceDocument objects
    """
    return db.query(SourceDocument).filter(SourceDocument.company_id == company_id).all()


def get_source_documents_by_type(db: Session, document_type: str) -> List[SourceDocument]:
    """
    Get all source documents of a specific type.

    Args:
        db: Database session
        document_type: Type of document to search for

    Returns:
        List of SourceDocument objects
    """
    return db.query(SourceDocument).filter(SourceDocument.document_type == document_type).all()


def update_source_document(
    db: Session,
    source_document_id: int,
    content: Optional[str] = None,
    document_type: Optional[str] = None,
    document_name: Optional[str] = None,
    url: Optional[str] = None
) -> Optional[SourceDocument]:
    """
    Update a source document.

    Args:
        db: Database session
        source_document_id: ID of the source document
        content: New text content
        document_type: New document type
        document_name: New document name
        url: New URL

    Returns:
        The updated SourceDocument object or None if not found
    """
    db_source_document = get_source_document(db, source_document_id)
    if not db_source_document:
        return None

    if content is not None:
        db_source_document.content = content
    if document_type is not None:
        db_source_document.document_type = document_type
    if document_name is not None:
        db_source_document.document_name = document_name
    if url is not None:
        db_source_document.url = url

    db.commit()
    db.refresh(db_source_document)
    return db_source_document


def delete_source_document(db: Session, source_document_id: int) -> bool:
    """
    Delete a source document.

    Args:
        db: Database session
        source_document_id: ID of the source document to delete

    Returns:
        True if successful, False if not found
    """
    db_source_document = get_source_document(db, source_document_id)
    if not db_source_document:
        return False

    db.delete(db_source_document)
    db.commit()
    return True