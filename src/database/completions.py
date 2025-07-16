from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union
from uuid import UUID

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Table, Text
from sqlalchemy.orm import attributes, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from src.database.base import Base, get_db_session
from src.utils.logging import get_logger
from uuid_extensions import uuid7

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from src.database.documents import Document
    from src.database.prompts import Prompt
    from src.database.ratings import Rating

# Initialize structlog
logger = get_logger(__name__)

# Association table for many-to-many relationship between Completion and Document
completion_document_association = Table(
    "completion_document_association",
    Base.metadata,
    Column("completion_id", ForeignKey("completions.id"), primary_key=True),
    Column("document_id", ForeignKey("documents.id"), primary_key=True)
)

class Completion(Base):
    """Completion model representing AI completions."""

    __tablename__ = "completions"

    # Primary identifier
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    # Timestamp fields
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    total_duration: Mapped[Optional[float]] = mapped_column(Float)

    # The actual content of the completion
    content: Mapped[Optional[str]] = mapped_column(Text)

    source_documents: Mapped[List["Document"]] = relationship(
        "Document",
        secondary=completion_document_association,
        backref="completions"
    )

    system_prompt_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("prompts.id", ondelete="SET NULL"), index=True)
    system_prompt: Mapped[Optional["Prompt"]] = relationship(
        "Prompt",
        foreign_keys=[system_prompt_id],
    )

    # OpenAI parameters
    model: Mapped[str] = mapped_column(String(50))
    temperature: Mapped[Optional[float]] = mapped_column(Float, default=0.7)
    top_p: Mapped[Optional[float]] = mapped_column(Float, default=1.0)
    num_ctx: Mapped[Optional[int]] = mapped_column(Float, default=4096)

    ratings: Mapped[Optional[List["Rating"]]] = relationship("Rating", back_populates="completion")

    def __repr__(self) -> str:
        return f"<Completion(id={self.id}, model='{self.model}')>"


def get_completion_ids() -> List[UUID]:
    """Get a list of all completion IDs in the database.

    Returns:
        List of completion UUIDs
    """
    try:
        session = get_db_session()
        completion_ids = [completion_id for completion_id, in session.query(Completion.id).all()]
        logger.info("retrieved_completion_ids", count=len(completion_ids))
        return completion_ids
    except Exception as e:
        logger.error("get_completion_ids_failed", error=str(e), exc_info=True)
        raise


def get_completions_by_document(document_id: Union[UUID, str]) -> List[Completion]:
    """Get all completions that use a specific document as a source.

    Args:
        document_id: UUID of the document to filter completions by

    Returns:
        List of Completion objects that reference the specified document
    """
    try:
        session = get_db_session()

        # Query completions that have the specified document in source_documents
        completions = (
            session.query(Completion)
            .join(completion_document_association, Completion.id == completion_document_association.c.completion_id)
            .filter(completion_document_association.c.document_id == document_id)
            .all()
        )

        logger.info("retrieved_completions_by_document", document_id=str(document_id), count=len(completions))
        return completions
    except Exception as e:
        logger.error("get_completions_by_document_failed", document_id=str(document_id),
                     error=str(e), exc_info=True)
        raise


def get_completion(completion_id: Union[UUID, str]) -> Optional[Completion]:
    """Get a completion by its ID.

    Args:
        completion_id: UUID of the completion to retrieve

    Returns:
        Completion object if found, None otherwise
    """
    try:
        session = get_db_session()
        completion = session.query(Completion).filter(Completion.id == completion_id).first()
        if completion:
            logger.info("retrieved_completion", completion_id=str(completion_id))
        else:
            logger.warning("completion_not_found", completion_id=str(completion_id))
        return completion
    except Exception as e:
        logger.error("get_completion_failed", completion_id=str(completion_id), error=str(e), exc_info=True)
        raise


def create_completion(completion_data: Dict[str, Any]) -> Completion:
    """Create a new completion in the database.

    Args:
        completion_data: Dictionary containing completion attributes

    Returns:
        Newly created Completion object
    """
    try:
        session = get_db_session()

        # Handle document associations if provided
        document_ids = completion_data.pop('document_ids', None)

        completion = Completion(**completion_data)
        session.add(completion)

        # Add document associations if provided
        if document_ids:
            from src.database.documents import Document
            documents = session.query(Document).filter(Document.id.in_(document_ids)).all()
            completion.source_documents.extend(documents)

        session.commit()
        logger.info("created_completion", completion_id=str(completion.id), model=completion.model)
        return completion
    except Exception as e:
        session.rollback()
        logger.error("create_completion_failed", error=str(e), exc_info=True)
        raise


def update_completion(completion_id: Union[UUID, str], completion_data: Dict[str, Any]) -> Optional[Completion]:
    """Update an existing completion in the database.

    Args:
        completion_id: UUID of the completion to update
        completion_data: Dictionary containing completion attributes to update

    Returns:
        Updated Completion object if found, None otherwise
    """
    try:
        session = get_db_session()
        completion = session.query(Completion).filter(Completion.id == completion_id).first()
        if not completion:
            logger.warning("update_completion_not_found", completion_id=str(completion_id))
            return None

        # Handle document associations if provided
        if 'document_ids' in completion_data:
            from src.database.documents import Document
            document_ids = completion_data.pop('document_ids')

            # Clear existing associations and add new ones
            completion.source_documents.clear()
            documents = session.query(Document).filter(Document.id.in_(document_ids)).all()
            completion.source_documents.extend(documents)


        for key, value in completion_data.items():
            if hasattr(completion, key):
                setattr(completion, key, value)
                # Flag JSON fields as modified to ensure changes are detected
                if key == 'context_text':
                    attributes.flag_modified(completion, key)
            else:
                logger.warning("update_completion_invalid_attribute", completion_id=str(completion_id), attribute=key)

        session.commit()
        logger.info("updated_completion", completion_id=str(completion.id))
        return completion
    except Exception as e:
        session.rollback()
        logger.error("update_completion_failed", completion_id=str(completion_id), error=str(e), exc_info=True)
        raise


def delete_completion(completion_id: Union[UUID, str]) -> bool:
    """Delete a completion from the database.

    Args:
        completion_id: UUID of the completion to delete

    Returns:
        True if completion was deleted, False if not found
    """
    try:
        session = get_db_session()
        completion = session.query(Completion).filter(Completion.id == completion_id).first()
        if not completion:
            logger.warning("delete_completion_not_found", completion_id=str(completion_id))
            return False

        session.delete(completion)
        session.commit()
        logger.info("deleted_completion", completion_id=str(completion_id))
        return True
    except Exception as e:
        session.rollback()
        logger.error("delete_completion_failed", completion_id=str(completion_id), error=str(e), exc_info=True)
        raise

