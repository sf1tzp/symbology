"""
Module for financial concept CRUD operations.
This module handles operations related to financial concepts across different statement types.
"""
import logging
from typing import Any, Dict, List

from .base import get_db_session
from .models import FinancialConcept

# Configure logging
logger = logging.getLogger(__name__)


def get_or_create_financial_concept(
    concept_id: str, label: str = None, session=None
) -> FinancialConcept:
    """Get an existing financial concept or create a new one.

    Args:
        concept_id: The standard concept identifier (e.g., us-gaap_CashAndCashEquivalentsAtCarryingValue)
        label: Human-readable label for the concept
        session: Database session (optional)

    Returns:
        FinancialConcept object
    """
    session = session or get_db_session()

    # Try to find the concept
    concept = session.query(FinancialConcept).filter(
        FinancialConcept.concept_id == concept_id
    ).first()

    if concept:
        # Concept exists, check if we need to add this label
        if label and label not in concept.labels:
            # Create a completely new list to ensure SQLAlchemy detects the change
            current_labels = concept.labels if concept.labels else []
            new_labels = current_labels + [label]
            # Assign the new list to force SQLAlchemy to detect the change
            concept.labels = new_labels
            session.commit()
            session.refresh(concept)
    else:
        # Create new concept with this label
        concept = FinancialConcept(
            concept_id=concept_id,
            labels=[label] if label else []
        )
        session.add(concept)
        session.commit()
        session.refresh(concept)

    return concept


def get_all_concepts(session=None) -> List[Dict[str, Any]]:
    """Get all financial concepts.

    Args:
        session: Database session (optional)

    Returns:
        List of all financial concepts
    """
    session = session or get_db_session()

    concepts = session.query(FinancialConcept).all()

    return [
        {
            "id": concept.id,
            "concept_id": concept.concept_id,
            "description": concept.description,
            "labels": concept.labels
        }
        for concept in concepts
    ]