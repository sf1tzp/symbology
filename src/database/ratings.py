from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, get_db_session
from src.database.completions import Completion
from src.utils.logging import get_logger

# Initialize structlog
logger = get_logger(__name__)

class Rating(Base):
    """Rating model representing user feedback on completions."""

    __tablename__ = "ratings"

    # Primary identifier
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Relationship to Completion
    completion_id: Mapped[UUID] = mapped_column(ForeignKey("completions.id"), index=True)
    completion: Mapped["Completion"] = relationship("Completion", back_populates="ratings")

    # Rating details
    content_score: Mapped[Optional[int]] = mapped_column(Integer)
    format_score: Mapped[Optional[int]] = mapped_column(Integer)
    comment: Mapped[Optional[str]] = mapped_column(String(1000))
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    def __repr__(self) -> str:
        return f"<Rating(id={self.id}, completion_id={self.completion_id})>"


def get_rating_ids() -> List[UUID]:
    """Get a list of all rating IDs in the database.

    Returns:
        List of rating UUIDs
    """
    try:
        session = get_db_session()
        rating_ids = [rating_id for rating_id, in session.query(Rating.id).all()]
        logger.info("retrieved_rating_ids", count=len(rating_ids))
        return rating_ids
    except Exception as e:
        logger.error("get_rating_ids_failed", error=str(e), exc_info=True)
        raise


def get_rating(rating_id: Union[UUID, str]) -> Optional[Rating]:
    """Get a rating by its ID.

    Args:
        rating_id: UUID of the rating to retrieve

    Returns:
        Rating object if found, None otherwise
    """
    try:
        session = get_db_session()
        rating = session.query(Rating).filter(Rating.id == rating_id).first()
        if rating:
            logger.info("retrieved_rating", rating_id=str(rating_id))
        else:
            logger.warning("rating_not_found", rating_id=str(rating_id))
        return rating
    except Exception as e:
        logger.error("get_rating_failed", rating_id=str(rating_id), error=str(e), exc_info=True)
        raise


def create_rating(rating_data: Dict[str, Any]) -> Rating:
    """Create a new rating in the database.

    Args:
        rating_data: Dictionary containing rating attributes

    Returns:
        Newly created Rating object
    """
    try:
        session = get_db_session()

        # Check if completion exists
        completion_id = rating_data.get('completion_id')
        if completion_id:
            completion = session.query(Completion).filter(Completion.id == completion_id).first()
            if not completion:
                logger.error("create_rating_failed", error=f"Completion with ID {completion_id} not found")
                raise ValueError(f"Completion with ID {completion_id} not found")

        # Validate scores
        if 'content_score' in rating_data and rating_data['content_score'] is not None:
            if not 1 <= rating_data['content_score'] <= 10:
                raise ValueError("Content score must be between 1 and 10")

        if 'format_score' in rating_data and rating_data['format_score'] is not None:
            if not 1 <= rating_data['format_score'] <= 10:
                raise ValueError("Format score must be between 1 and 10")

        rating = Rating(**rating_data)
        session.add(rating)
        session.commit()
        logger.info("created_rating", rating_id=str(rating.id), completion_id=str(rating.completion_id))
        return rating
    except Exception as e:
        session.rollback()
        logger.error("create_rating_failed", error=str(e), exc_info=True)
        raise


def update_rating(rating_id: Union[UUID, str], rating_data: Dict[str, Any]) -> Optional[Rating]:
    """Update an existing rating in the database.

    Args:
        rating_id: UUID of the rating to update
        rating_data: Dictionary containing rating attributes to update

    Returns:
        Updated Rating object if found, None otherwise
    """
    try:
        session = get_db_session()
        rating = session.query(Rating).filter(Rating.id == rating_id).first()
        if not rating:
            logger.warning("update_rating_not_found", rating_id=str(rating_id))
            return None

        # If completion_id is being updated, check if new completion exists
        if 'completion_id' in rating_data:
            completion = session.query(Completion).filter(Completion.id == rating_data['completion_id']).first()
            if not completion:
                logger.error("update_rating_failed", error=f"Completion with ID {rating_data['completion_id']} not found")
                raise ValueError(f"Completion with ID {rating_data['completion_id']} not found")

        # Validate scores
        if 'content_score' in rating_data and rating_data['content_score'] is not None:
            if not 1 <= rating_data['content_score'] <= 10:
                raise ValueError("Content score must be between 1 and 10")

        if 'format_score' in rating_data and rating_data['format_score'] is not None:
            if not 1 <= rating_data['format_score'] <= 10:
                raise ValueError("Format score must be between 1 and 10")

        for key, value in rating_data.items():
            if hasattr(rating, key):
                setattr(rating, key, value)
            else:
                logger.warning("update_rating_invalid_attribute", rating_id=str(rating_id), attribute=key)

        session.commit()
        logger.info("updated_rating", rating_id=str(rating.id))
        return rating
    except Exception as e:
        session.rollback()
        logger.error("update_rating_failed", rating_id=str(rating_id), error=str(e), exc_info=True)
        raise


def delete_rating(rating_id: Union[UUID, str]) -> bool:
    """Delete a rating from the database.

    Args:
        rating_id: UUID of the rating to delete

    Returns:
        True if rating was deleted, False if not found
    """
    try:
        session = get_db_session()
        rating = session.query(Rating).filter(Rating.id == rating_id).first()
        if not rating:
            logger.warning("delete_rating_not_found", rating_id=str(rating_id))
            return False

        session.delete(rating)
        session.commit()
        logger.info("deleted_rating", rating_id=str(rating_id))
        return True
    except Exception as e:
        session.rollback()
        logger.error("delete_rating_failed", rating_id=str(rating_id), error=str(e), exc_info=True)
        raise

