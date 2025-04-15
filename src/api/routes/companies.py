"""Company-related API routes."""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.ingestion.database.base import get_db
from src.ingestion.database.crud_company import (
    get_company_by_id,
    get_all_companies,
    create_company,
    update_company,
    delete_company,
    get_companies_by_ticker
)
from src.api.schemas import Company, CompanyCreate, CompanyUpdate
from src.ingestion.utils.logging import get_logger, log_exception

# Create logger for this module
logger = get_logger(__name__)

# Create companies router
router = APIRouter()


@router.get("/", response_model=List[Company])
async def read_companies(
    skip: int = 0,
    limit: int = 100,
    ticker: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Retrieve a list of companies.

    Parameters:
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return
    - ticker: Filter by company ticker (optional)
    """
    logger.info("read_companies_requested", skip=skip, limit=limit, ticker=ticker)

    if ticker:
        companies = get_companies_by_ticker(ticker, session=db)
    else:
        companies = get_all_companies(skip=skip, limit=limit, session=db)

    logger.info("companies_retrieved", count=len(companies))
    return companies


@router.post("/", response_model=Company, status_code=201)
async def create_new_company(
    company: CompanyCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new company.

    Parameters:
    - company: Company data
    """
    logger.info("create_company_requested", data=company.model_dump())

    try:
        db_company = create_company(company.model_dump(), session=db)
        logger.info("company_created", id=db_company.id, cik=getattr(db_company, "cik", None))
        return db_company
    except Exception as e:
        error_msg = log_exception(e, logger, "Failed to create company: ")
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/{company_id}", response_model=Company)
async def read_company(
    company_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve a specific company by ID.

    Parameters:
    - company_id: Company ID
    """
    logger.info("read_company_requested", company_id=company_id)

    db_company = get_company_by_id(company_id, session=db)
    if db_company is None:
        logger.warning("company_not_found", company_id=company_id)
        raise HTTPException(status_code=404, detail="Company not found")

    logger.info("company_retrieved", company_id=company_id, cik=getattr(db_company, "cik", None))
    return db_company


@router.put("/{company_id}", response_model=Company)
async def update_company_data(
    company_id: int,
    company: CompanyUpdate,
    db: Session = Depends(get_db),
):
    """
    Update a company.

    Parameters:
    - company_id: Company ID
    - company: Updated company data
    """
    logger.info("update_company_requested", company_id=company_id)

    db_company = get_company_by_id(company_id, session=db)
    if db_company is None:
        logger.warning("company_not_found", company_id=company_id)
        raise HTTPException(status_code=404, detail="Company not found")

    try:
        # Filter out None values to keep existing values for those fields
        update_data = {k: v for k, v in company.model_dump().items() if v is not None}
        updated_company = update_company(company_id, update_data, session=db)
        logger.info("company_updated", company_id=company_id)
        return updated_company
    except Exception as e:
        error_msg = log_exception(e, logger, "Failed to update company: ")
        raise HTTPException(status_code=500, detail=error_msg)


@router.delete("/{company_id}", status_code=204)
async def delete_company_data(
    company_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a company.

    Parameters:
    - company_id: Company ID
    """
    logger.info("delete_company_requested", company_id=company_id)

    db_company = get_company_by_id(company_id, session=db)
    if db_company is None:
        logger.warning("company_not_found", company_id=company_id)
        raise HTTPException(status_code=404, detail="Company not found")

    try:
        delete_company(company_id, session=db)
        logger.info("company_deleted", company_id=company_id)
        return None
    except Exception as e:
        error_msg = log_exception(e, logger, "Failed to delete company: ")
        raise HTTPException(status_code=500, detail=error_msg)