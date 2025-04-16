from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union
from uuid import UUID, uuid4

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.ingestion.database.base import Base, get_db_session
from src.ingestion.utils.logging import get_logger

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from src.ingestion.database.financial_values import FinancialValue

# Initialize structlog
logger = get_logger(__name__)

class FinancialConcept(Base):
    """FinancialConcept model representing financial reporting concepts."""

    __tablename__ = "financial_concepts"

    # Primary identifier
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Financial concept details
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    labels: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)

    # Relationships
    financial_values: Mapped[List["FinancialValue"]] = relationship("FinancialValue", back_populates="concept", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<FinancialConcept(id={self.id}, name='{self.name}')>"


def get_financial_concept_ids() -> List[UUID]:
    """Get a list of all financial concept IDs in the database.

    Returns:
        List of financial concept UUIDs
    """
    try:
        session = get_db_session()
        concept_ids = [concept_id for concept_id, in session.query(FinancialConcept.id).all()]
        logger.info("retrieved_financial_concept_ids", count=len(concept_ids))
        return concept_ids
    except Exception as e:
        logger.error("get_financial_concept_ids_failed", error=str(e), exc_info=True)
        raise


def get_financial_concept(concept_id: Union[UUID, str]) -> Optional[FinancialConcept]:
    """Get a financial concept by its ID.

    Args:
        concept_id: UUID of the financial concept to retrieve

    Returns:
        FinancialConcept object if found, None otherwise
    """
    try:
        session = get_db_session()
        concept = session.query(FinancialConcept).filter(FinancialConcept.id == concept_id).first()
        if concept:
            logger.info("retrieved_financial_concept", concept_id=str(concept_id))
        else:
            logger.warning("financial_concept_not_found", concept_id=str(concept_id))
        return concept
    except Exception as e:
        logger.error("get_financial_concept_failed", concept_id=str(concept_id), error=str(e), exc_info=True)
        raise


def create_financial_concept(concept_data: Dict[str, Any]) -> FinancialConcept:
    """Create a new financial concept in the database.

    Args:
        concept_data: Dictionary containing financial concept attributes

    Returns:
        Newly created FinancialConcept object
    """
    try:
        session = get_db_session()

        # Check if a concept with the same name already exists
        name = concept_data.get('name')
        if name and session.query(FinancialConcept).filter(FinancialConcept.name == name).first():
            logger.error("create_financial_concept_failed", error=f"Financial concept with name '{name}' already exists")
            raise ValueError(f"Financial concept with name '{name}' already exists")

        concept = FinancialConcept(**concept_data)
        session.add(concept)
        session.commit()
        logger.info("created_financial_concept", concept_id=str(concept.id), name=concept.name)
        return concept
    except Exception as e:
        session.rollback()
        logger.error("create_financial_concept_failed", error=str(e), exc_info=True)
        raise


def update_financial_concept(concept_id: Union[UUID, str], concept_data: Dict[str, Any]) -> Optional[FinancialConcept]:
    """Update an existing financial concept in the database.

    Args:
        concept_id: UUID of the financial concept to update
        concept_data: Dictionary containing financial concept attributes to update

    Returns:
        Updated FinancialConcept object if found, None otherwise
    """
    try:
        session = get_db_session()
        concept = session.query(FinancialConcept).filter(FinancialConcept.id == concept_id).first()
        if not concept:
            logger.warning("update_financial_concept_not_found", concept_id=str(concept_id))
            return None

        # If name is being updated, check if it already exists for another concept
        if 'name' in concept_data and concept_data['name'] != concept.name:
            existing = session.query(FinancialConcept).filter(
                FinancialConcept.name == concept_data['name'],
                FinancialConcept.id != concept_id
            ).first()
            if existing:
                logger.error(
                    "update_financial_concept_failed",
                    error=f"Financial concept with name '{concept_data['name']}' already exists"
                )
                raise ValueError(f"Financial concept with name '{concept_data['name']}' already exists")

        for key, value in concept_data.items():
            if hasattr(concept, key):
                setattr(concept, key, value)
            else:
                logger.warning("update_financial_concept_invalid_attribute", concept_id=str(concept_id), attribute=key)

        session.commit()
        logger.info("updated_financial_concept", concept_id=str(concept.id), name=concept.name)
        return concept
    except Exception as e:
        session.rollback()
        logger.error("update_financial_concept_failed", concept_id=str(concept_id), error=str(e), exc_info=True)
        raise


def delete_financial_concept(concept_id: Union[UUID, str]) -> bool:
    """Delete a financial concept from the database.

    Args:
        concept_id: UUID of the financial concept to delete

    Returns:
        True if financial concept was deleted, False if not found
    """
    try:
        session = get_db_session()
        concept = session.query(FinancialConcept).filter(FinancialConcept.id == concept_id).first()
        if not concept:
            logger.warning("delete_financial_concept_not_found", concept_id=str(concept_id))
            return False

        session.delete(concept)
        session.commit()
        logger.info("deleted_financial_concept", concept_id=str(concept_id))
        return True
    except Exception as e:
        session.rollback()
        logger.error("delete_financial_concept_failed", concept_id=str(concept_id), error=str(e), exc_info=True)
        raise
