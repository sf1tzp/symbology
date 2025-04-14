from datetime import datetime
from typing import List, Optional, Union

from sqlalchemy.orm import Session

from .models import RiskFactors


def create_risk_factors(
    db: Session,
    filing_id: int,
    company_id: int,
    report_date: Union[datetime, str],
    content: str,
) -> RiskFactors:
    """
    Create a new risk factors entry.

    Args:
        db: Database session
        filing_id: ID of the filing
        company_id: ID of the company
        report_date: Date of the report
        content: Text content of the risk factors

    Returns:
        The created RiskFactors object
    """
    if isinstance(report_date, str):
        report_date = datetime.strptime(report_date, "%Y-%m-%d")

    db_risk_factors = RiskFactors(
        filing_id=filing_id,
        company_id=company_id,
        report_date=report_date,
        content=content,
    )
    db.add(db_risk_factors)
    db.commit()
    db.refresh(db_risk_factors)
    return db_risk_factors


def get_risk_factors(db: Session, risk_factors_id: int) -> Optional[RiskFactors]:
    """
    Get risk factors by ID.

    Args:
        db: Database session
        risk_factors_id: ID of the risk factors

    Returns:
        The RiskFactors object or None if not found
    """
    return db.query(RiskFactors).filter(RiskFactors.id == risk_factors_id).first()


def get_risk_factors_by_filing_id(db: Session, filing_id: int) -> Optional[RiskFactors]:
    """
    Get risk factors by filing ID.

    Args:
        db: Database session
        filing_id: ID of the filing

    Returns:
        The RiskFactors object or None if not found
    """
    return db.query(RiskFactors).filter(RiskFactors.filing_id == filing_id).first()


def get_risk_factors_by_company_id(db: Session, company_id: int) -> List[RiskFactors]:
    """
    Get all risk factors for a company.

    Args:
        db: Database session
        company_id: ID of the company

    Returns:
        List of RiskFactors objects
    """
    return db.query(RiskFactors).filter(RiskFactors.company_id == company_id).all()


def update_risk_factors(
    db: Session, risk_factors_id: int, content: str
) -> Optional[RiskFactors]:
    """
    Update risk factors content.

    Args:
        db: Database session
        risk_factors_id: ID of the risk factors
        content: New text content

    Returns:
        The updated RiskFactors object or None if not found
    """
    db_risk_factors = get_risk_factors(db, risk_factors_id)
    if not db_risk_factors:
        return None

    db_risk_factors.content = content
    db.commit()
    db.refresh(db_risk_factors)
    return db_risk_factors


def delete_risk_factors(db: Session, risk_factors_id: int) -> bool:
    """
    Delete risk factors.

    Args:
        db: Database session
        risk_factors_id: ID of the risk factors to delete

    Returns:
        True if successful, False if not found
    """
    db_risk_factors = get_risk_factors(db, risk_factors_id)
    if not db_risk_factors:
        return False

    db.delete(db_risk_factors)
    db.commit()
    return True