from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.ingestion.database.base import Base, get_db_session
from src.ingestion.utils.logging import get_logger

# Initialize structlog
logger = get_logger(__name__)

class Document(Base):
    """Document model representing document information associated with filings."""

    __tablename__ = "documents"

    # Primary identifier
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Foreign keys
    filing_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("filings.id", ondelete="CASCADE"), index=True)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)

    # Relationships
    filing = relationship("Filing", back_populates="documents")
    company = relationship("Company", back_populates="documents")

    # Document details
    document_name: Mapped[str] = mapped_column(String(255))
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
        document = session.query(Document).filter(Document.id == document_id).first()
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
