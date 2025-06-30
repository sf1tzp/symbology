from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, joinedload
from uuid_extensions import uuid7

from src.database.base import Base, get_db_session
from src.utils.logging import get_logger

# Initialize structlog
logger = get_logger(__name__)

class DocumentType(Enum):
    MDA = "management_discussion"
    RISK_FACTORS = "risk_factors"
    DESCRIPTION = "business_description"


class Document(Base):
    """Document model representing document information associated with filings."""

    __tablename__ = "documents"

    # Primary identifier
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    # Foreign keys
    filing_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("filings.id", ondelete="CASCADE"), index=True)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)

    # Relationships
    filing = relationship("Filing", back_populates="documents")
    company = relationship("Company", back_populates="documents")

    # Document details
    document_name: Mapped[str] = mapped_column(String(255))
    document_type: Mapped[Optional[DocumentType]] = mapped_column(
        SQLEnum(DocumentType, name="document_type_enum"), nullable=True
    )

    content: Mapped[Optional[str]] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, document_name='{self.document_name}')>"


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
            logger.info("retrieved_document", document_id=str(document_id))
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
            document_name=document.document_name,
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
            document_name=document.document_name
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
            Document.document_name == document_name
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
