from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from symbology.database.base import Base, get_db_session
from symbology.utils.logging import get_logger
from uuid_extensions import uuid7

if TYPE_CHECKING:
    from symbology.database.generated_content import GeneratedContent

# Initialize structlog
logger = get_logger(__name__)

class Rating(Base):
    """Rating model representing user feedback on completions and aggregates."""

    __tablename__ = "ratings"

    # Primary identifier
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)

    generated_content_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("generated_content.id"), index=True, nullable=True)
    generated_content: Mapped[Optional["GeneratedContent"]] = relationship("GeneratedContent", back_populates="ratings")

    # Rating details
    content_score: Mapped[Optional[int]] = mapped_column(Integer)
    format_score: Mapped[Optional[int]] = mapped_column(Integer)
    comment: Mapped[Optional[str]] = mapped_column(String(1000))
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    def __repr__(self) -> str:
        if self.generated_content_id:
            return f"<Rating(id={self.id}, generated_content_id={self.generated_content_id})>"
        else:
            return f"<Rating(id={self.id})>"


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

        # Check if generated_content exists
        generated_content_id = rating_data.get('generated_content_id')

        if not generated_content_id:
            raise ValueError("Rating must be associated with generated content")

        # Verify the generated content exists
        from symbology.database.generated_content import GeneratedContent
        generated_content = session.query(GeneratedContent).filter(GeneratedContent.id == generated_content_id).first()
        if not generated_content:
            logger.error("create_rating_failed", error=f"Generated content with ID {generated_content_id} not found")
            raise ValueError(f"Generated content with ID {generated_content_id} not found")

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

        logger.info("created_rating", rating_id=str(rating.id), generated_content_id=str(generated_content_id))
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

        # If generated_content_id is being updated, check if new generated content exists
        if 'generated_content_id' in rating_data and rating_data['generated_content_id']:
            from symbology.database.generated_content import GeneratedContent
            generated_content = session.query(GeneratedContent).filter(GeneratedContent.id == rating_data['generated_content_id']).first()
            if not generated_content:
                logger.error("update_rating_failed", error=f"Generated content with ID {rating_data['generated_content_id']} not found")
                raise ValueError(f"Generated content with ID {rating_data['generated_content_id']} not found")

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


def get_ratings_by_generated_content(generated_content_id: Union[UUID, str]) -> List[Rating]:
    """Get all ratings for a specific generated content.

    Args:
        generated_content_id: UUID of the generated content

    Returns:
        List of Rating objects for the specified generated content
    """
    try:
        session = get_db_session()
        ratings = session.query(Rating).filter(Rating.generated_content_id == generated_content_id).all()
        logger.info("retrieved_ratings_by_generated_content",
                   generated_content_id=str(generated_content_id), count=len(ratings))
        return ratings
    except Exception as e:
        logger.error("get_ratings_by_generated_content_failed",
                    generated_content_id=str(generated_content_id), error=str(e), exc_info=True)
        raise
