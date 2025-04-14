from datetime import datetime
from typing import List, Optional, Union

from sqlalchemy.orm import Session

from .models import BusinessDescription


def create_business_description(
    db: Session,
    filing_id: int,
    company_id: int,
    report_date: Union[datetime, str],
    content: str,
) -> BusinessDescription:
    """
    Create a new business description entry.

    Args:
        db: Database session
        filing_id: ID of the filing
        company_id: ID of the company
        report_date: Date of the report
        content: Text content of the business description

    Returns:
        The created BusinessDescription object
    """
    if isinstance(report_date, str):
        report_date = datetime.strptime(report_date, "%Y-%m-%d")

    db_business_desc = BusinessDescription(
        filing_id=filing_id,
        company_id=company_id,
        report_date=report_date,
        content=content,
    )
    db.add(db_business_desc)
    db.commit()
    db.refresh(db_business_desc)
    return db_business_desc


def get_business_description(db: Session, business_description_id: int) -> Optional[BusinessDescription]:
    """
    Get a business description by ID.

    Args:
        db: Database session
        business_description_id: ID of the business description

    Returns:
        The BusinessDescription object or None if not found
    """
    return db.query(BusinessDescription).filter(BusinessDescription.id == business_description_id).first()


def get_business_description_by_filing_id(db: Session, filing_id: int) -> Optional[BusinessDescription]:
    """
    Get a business description by filing ID.

    Args:
        db: Database session
        filing_id: ID of the filing

    Returns:
        The BusinessDescription object or None if not found
    """
    return db.query(BusinessDescription).filter(BusinessDescription.filing_id == filing_id).first()


def get_business_descriptions_by_company_id(db: Session, company_id: int) -> List[BusinessDescription]:
    """
    Get all business descriptions for a company.

    Args:
        db: Database session
        company_id: ID of the company

    Returns:
        List of BusinessDescription objects
    """
    return db.query(BusinessDescription).filter(BusinessDescription.company_id == company_id).all()


def update_business_description(
    db: Session, business_description_id: int, content: str
) -> Optional[BusinessDescription]:
    """
    Update a business description content.

    Args:
        db: Database session
        business_description_id: ID of the business description
        content: New text content

    Returns:
        The updated BusinessDescription object or None if not found
    """
    db_business_desc = get_business_description(db, business_description_id)
    if not db_business_desc:
        return None

    db_business_desc.content = content
    db.commit()
    db.refresh(db_business_desc)
    return db_business_desc


def delete_business_description(db: Session, business_description_id: int) -> bool:
    """
    Delete a business description.

    Args:
        db: Database session
        business_description_id: ID of the business description to delete

    Returns:
        True if successful, False if not found
    """
    db_business_desc = get_business_description(db, business_description_id)
    if not db_business_desc:
        return False

    db.delete(db_business_desc)
    db.commit()
    return True