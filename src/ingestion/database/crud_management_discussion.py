from datetime import datetime
from typing import List, Optional, Union

from sqlalchemy.orm import Session

from .models import ManagementDiscussion


def create_management_discussion(
    db: Session,
    filing_id: int,
    company_id: int,
    report_date: Union[datetime, str],
    content: str,
) -> ManagementDiscussion:
    """
    Create a new management discussion entry.

    Args:
        db: Database session
        filing_id: ID of the filing
        company_id: ID of the company
        report_date: Date of the report
        content: Text content of the management discussion

    Returns:
        The created ManagementDiscussion object
    """
    if isinstance(report_date, str):
        report_date = datetime.strptime(report_date, "%Y-%m-%d")

    db_mgmt_discussion = ManagementDiscussion(
        filing_id=filing_id,
        company_id=company_id,
        report_date=report_date,
        content=content,
    )
    db.add(db_mgmt_discussion)
    db.commit()
    db.refresh(db_mgmt_discussion)
    return db_mgmt_discussion


def get_management_discussion(db: Session, management_discussion_id: int) -> Optional[ManagementDiscussion]:
    """
    Get a management discussion by ID.

    Args:
        db: Database session
        management_discussion_id: ID of the management discussion

    Returns:
        The ManagementDiscussion object or None if not found
    """
    return db.query(ManagementDiscussion).filter(ManagementDiscussion.id == management_discussion_id).first()


def get_management_discussion_by_filing_id(db: Session, filing_id: int) -> Optional[ManagementDiscussion]:
    """
    Get a management discussion by filing ID.

    Args:
        db: Database session
        filing_id: ID of the filing

    Returns:
        The ManagementDiscussion object or None if not found
    """
    return db.query(ManagementDiscussion).filter(ManagementDiscussion.filing_id == filing_id).first()


def get_management_discussions_by_company_id(db: Session, company_id: int) -> List[ManagementDiscussion]:
    """
    Get all management discussions for a company.

    Args:
        db: Database session
        company_id: ID of the company

    Returns:
        List of ManagementDiscussion objects
    """
    return db.query(ManagementDiscussion).filter(ManagementDiscussion.company_id == company_id).all()


def update_management_discussion(
    db: Session, management_discussion_id: int, content: str
) -> Optional[ManagementDiscussion]:
    """
    Update a management discussion content.

    Args:
        db: Database session
        management_discussion_id: ID of the management discussion
        content: New text content

    Returns:
        The updated ManagementDiscussion object or None if not found
    """
    db_mgmt_discussion = get_management_discussion(db, management_discussion_id)
    if not db_mgmt_discussion:
        return None

    db_mgmt_discussion.content = content
    db.commit()
    db.refresh(db_mgmt_discussion)
    return db_mgmt_discussion


def delete_management_discussion(db: Session, management_discussion_id: int) -> bool:
    """
    Delete a management discussion.

    Args:
        db: Database session
        management_discussion_id: ID of the management discussion to delete

    Returns:
        True if successful, False if not found
    """
    db_mgmt_discussion = get_management_discussion(db, management_discussion_id)
    if not db_mgmt_discussion:
        return False

    db.delete(db_mgmt_discussion)
    db.commit()
    return True