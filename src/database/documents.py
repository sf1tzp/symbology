from enum import Enum
import hashlib
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import joinedload, Mapped, mapped_column, relationship
from src.database.base import Base, get_db_session

# Import Filing for the new functions
from src.database.filings import Filing
from src.utils.logging import get_logger
from uuid_extensions import uuid7

# Initialize structlog
logger = get_logger(__name__)

class DocumentType(Enum):
    # Core document types that appear in multiple form types
    MDA = "management_discussion"
    RISK_FACTORS = "risk_factors"
    DESCRIPTION = "business_description"

    # Additional document sections from various form types
    CONTROLS_PROCEDURES = "controls_procedures"
    LEGAL_PROCEEDINGS = "legal_proceedings"
    MARKET_RISK = "market_risk"
    EXECUTIVE_COMPENSATION = "executive_compensation"
    DIRECTORS_OFFICERS = "directors_officers"

    def __repr__(self) -> str:
        return f"{ self.value }"


class Document(Base):
    """Document model representing document information associated with filings."""

    __tablename__ = "documents"

    # Primary identifier
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    # Foreign keys
    filing_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("filings.id", ondelete="CASCADE"), index=True)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)

    # Relationships
    filing = relationship("Filing", back_populates="documents", lazy="joined")
    company = relationship("Company", back_populates="documents", lazy="joined")

    # Document details
    title: Mapped[str] = mapped_column(String(255))
    document_type: Mapped[Optional[DocumentType]] = mapped_column(
        SQLEnum(DocumentType, name="document_type_enum"), nullable=True
    )

    content: Mapped[Optional[str]] = mapped_column(Text, deferred=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)

    def __repr__(self) -> str:
        return f"{self.company.ticker} {self.filing.period_of_report.year} {self.filing.filing_type} {self.document_type.value}"

    def generate_content_hash(self) -> str:
        """Generate SHA256 hash of the content for URL identification."""
        if not self.content:
            return ""
        return hashlib.sha256(self.content.encode('utf-8')).hexdigest()

    def get_short_hash(self, length: int = 12) -> str:
        """Get shortened version of content hash for URLs."""
        if not self.content_hash:
            return ""
        return self.content_hash[:length]

    def update_content_hash(self):
        """Update the content hash based on current content."""
        self.content_hash = self.generate_content_hash()


def get_document_ids() -> List[UUID]:
    """Get a list of all document IDs in the database.

    Returns:
        List of document UUIDs
    """
    try:
        session = get_db_session()
        document_ids = [document_id for document_id, in session.query(Document.id).all()]
        logger.info("retrieved_document_ids", count=len(document_ids))
        return document_ids
    except Exception as e:
        logger.error("get_document_ids_failed", error=str(e), exc_info=True)
        raise


def get_document(document_id: Union[UUID, str]) -> Optional[Document]:
    """Get a document by its ID.

    Args:
        document_id: UUID of the document to retrieve

    Returns:
        Document object if found, None otherwise
    """
    try:
        session = get_db_session()
        # Use joinedload to eagerly fetch the filing relationship
        document = session.query(Document).options(joinedload(Document.filing)).filter(Document.id == document_id).first()
        if document:
            logger.info("retrieved_document", document=document.title)
        else:
            logger.warning("document_not_found", document_id=str(document_id))
        return document
    except Exception as e:
        logger.error("get_document_failed", document_id=str(document_id), error=str(e), exc_info=True)
        raise


def create_document(document_data: Dict[str, Any]) -> Document:
    """Create a new document in the database.

    Args:
        document_data: Dictionary containing document attributes

    Returns:
        Newly created Document object
    """
    try:
        session = get_db_session()
        document = Document(**document_data)
        session.add(document)
        session.commit()
        logger.info(
            "created_document",
            document_id=str(document.id),
            document_name=document.title,
            company_id=str(document.company_id)
        )
        return document
    except Exception as e:
        session.rollback()
        logger.error("create_document_failed", error=str(e), exc_info=True)
        raise


def update_document(document_id: Union[UUID, str], document_data: Dict[str, Any]) -> Optional[Document]:
    """Update an existing document in the database.

    Args:
        document_id: UUID of the document to update
        document_data: Dictionary containing document attributes to update

    Returns:
        Updated Document object if found, None otherwise
    """
    try:
        session = get_db_session()
        document = session.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.warning("update_document_not_found", document_id=str(document_id))
            return None

        for key, value in document_data.items():
            if hasattr(document, key):
                setattr(document, key, value)
            else:
                logger.warning("update_document_invalid_attribute", document_id=str(document_id), attribute=key)

        session.commit()
        logger.info(
            "updated_document",
            document_id=str(document.id),
            document_name=document.title
        )
        return document
    except Exception as e:
        session.rollback()
        logger.error("update_document_failed", document_id=str(document_id), error=str(e), exc_info=True)
        raise


def delete_document(document_id: Union[UUID, str]) -> bool:
    """Delete a document from the database.

    Args:
        document_id: UUID of the document to delete

    Returns:
        True if document was deleted, False if not found
    """
    try:
        session = get_db_session()
        document = session.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.warning("delete_document_not_found", document_id=str(document_id))
            return False

        session.delete(document)
        session.commit()
        logger.info("deleted_document", document_id=str(document_id))
        return True
    except Exception as e:
        session.rollback()
        logger.error("delete_document_failed", document_id=str(document_id), error=str(e), exc_info=True)
        raise


def find_or_create_document(company_id: UUID, document_name: str, document_type: DocumentType, content: Optional[str],
                           filing_id: Optional[UUID] = None) -> Document:
    """Find a document by company, filing, and name or create it if it doesn't exist.

    Args:
        company_id: UUID of the company
        document_name: Name of the document
        content: Content of the document
        filing_id: UUID of the filing (optional)

    Returns:
        Found or created Document object
    """
    try:
        session = get_db_session()

        # Build query
        query = session.query(Document).filter(
            Document.company_id == company_id,
            Document.title == document_name
        )

        if filing_id:
            query = query.filter(Document.filing_id == filing_id)
        else:
            query = query.filter(Document.filing_id.is_(None))

        existing_document = query.first()

        if existing_document:
            # Update content if provided
            if content is not None:
                existing_document.content = content
                session.commit()
                logger.info("updated_document_content",
                           document_id=str(existing_document.id),
                           document_name=document_name)
            return existing_document
        else:
            # Create new document
            document_data = {
                'company_id': company_id,
                'document_name': document_name,
                'document_type': document_type,
                'content': content
            }
            if filing_id:
                document_data['filing_id'] = filing_id

            document = Document(**document_data)
            document.update_content_hash()
            session.add(document)
            session.commit()
            logger.info("created_new_document",
                       document_id=str(document.id),
                       document_name=document_name)
            return document
    except Exception as e:
        session.rollback()
        logger.error("find_or_create_document_failed", error=str(e), exc_info=True)
        raise


# FIXME: This function should not return the document contents
def get_documents_by_filing(filing_id: UUID) -> List[Document]:
    """Get all documents associated with a filing.

    Args:
        filing_id: UUID of the filing

    Returns:
        List of Document objects
    """
    try:
        session = get_db_session()
        documents = session.query(Document).filter(Document.filing_id == filing_id).all()
        logger.info("retrieved_documents_by_filing",
                   filing_id=str(filing_id),
                   count=len(documents))
        return documents
    except Exception as e:
        logger.error("get_documents_by_filing_failed",
                    filing_id=str(filing_id),
                    error=str(e),
                    exc_info=True)
        raise


def get_documents_by_ids(document_ids: List[UUID]) -> List[Document]:
    """Get documents by their IDs.

    Args:
        document_ids: List of document UUIDs

    Returns:
        List of Document objects (only basic info, not content)
    """
    try:
        if not document_ids:
            return []

        session = get_db_session()
        # Only select the fields we need, excluding content for performance
        documents = session.query(Document).filter(Document.id.in_(document_ids)).options(
            joinedload(Document.filing)
        ).all()

        logger.info("retrieved_documents_by_ids",
                   document_count=len(documents),
                   requested_count=len(document_ids))
        return documents
    except Exception as e:
        logger.error("get_documents_by_ids_failed",
                    document_ids=[str(doc_id) for doc_id in document_ids],
                    error=str(e),
                    exc_info=True)
        raise


def get_document_by_content_hash(content_hash: str) -> Optional[Document]:
    """Get document by its content hash.

    Args:
        content_hash: Full or partial SHA256 hash of the document content

    Returns:
        Document object if found, None otherwise
    """
    try:
        session = get_db_session()

        # Try exact match first
        document = session.query(Document).filter(Document.content_hash == content_hash).first()

        # If no exact match and hash is short, try prefix match
        if not document and len(content_hash) < 64:
            document = session.query(Document).filter(
                Document.content_hash.like(f"{content_hash}%")
            ).first()

        if document:
            logger.info("retrieved_document_by_content_hash", content_hash=content_hash)
        else:
            logger.warning("document_not_found_by_content_hash", content_hash=content_hash)
        return document
    except Exception as e:
        logger.error("get_document_by_content_hash_failed", content_hash=content_hash, error=str(e), exc_info=True)
        raise


def get_document_by_accession_and_hash(accession_number: str, content_hash: str) -> Optional[Document]:
    """Get document by filing accession number and content hash (for URL routing).

    Args:
        accession_number: SEC filing accession number
        content_hash: Full or partial SHA256 hash of the document content

    Returns:
        Document object if found, None otherwise
    """
    try:
        session = get_db_session()

        # Join with filing to filter by accession number
        query = (
            session.query(Document)
            .join(Filing, Document.filing_id == Filing.id)
            .filter(Filing.accession_number == accession_number)
        )

        # Try exact hash match first
        document = query.filter(Document.content_hash == content_hash).first()

        # If no exact match and hash is short, try prefix match
        if not document and len(content_hash) < 64:
            document = query.filter(Document.content_hash.like(f"{content_hash}%")).first()

        if document:
            logger.info("retrieved_document_by_accession_and_hash",
                       accession_number=accession_number, content_hash=content_hash)
        else:
            logger.warning("document_not_found_by_accession_and_hash",
                          accession_number=accession_number, content_hash=content_hash)
        return document
    except Exception as e:
        logger.error("get_document_by_accession_and_hash_failed",
                    accession_number=accession_number, content_hash=content_hash, error=str(e), exc_info=True)
        raise
