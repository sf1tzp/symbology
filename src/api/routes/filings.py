"""Filing-related API routes."""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.ingestion.database.base import get_db
from src.ingestion.database.crud_filing import (
    get_filing_by_id,
    get_all_filings,
    get_filings_by_company_id,
    get_filings_by_type,
    create_filing,
    update_filing,
    delete_filing
)
from src.api.schemas import Filing, FilingCreate, FilingUpdate
from src.ingestion.utils.logging import get_logger, log_exception

# Create logger for this module
logger = get_logger(__name__)

# Create filings router
router = APIRouter()


@router.get("/", response_model=List[Filing])
async def read_filings(
    skip: int = 0,
    limit: int = 100,
    company_id: Optional[int] = None,
    filing_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Retrieve a list of filings.

    Parameters:
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return
    - company_id: Filter by company ID (optional)
    - filing_type: Filter by filing type (optional)
    """
    logger.info("read_filings_requested",
               skip=skip,
               limit=limit,
               company_id=company_id,
               filing_type=filing_type)

    if company_id and filing_type:
        # Filter by both company and type
        # Since there's no direct method for this, we'll get by company and filter in memory
        filings = [f for f in get_filings_by_company_id(company_id, skip, limit, session=db)
                 if f.filing_type == filing_type]
    elif company_id:
        filings = get_filings_by_company_id(company_id, skip, limit, session=db)
    elif filing_type:
        filings = get_filings_by_type(filing_type, skip, limit, session=db)
    else:
        filings = get_all_filings(skip, limit, session=db)

    logger.info("filings_retrieved", count=len(filings))
    return filings


@router.post("/", response_model=Filing, status_code=201)
async def create_new_filing(
    filing: FilingCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new filing.

    Parameters:
    - filing: Filing data
    """
    logger.info("create_filing_requested",
               company_id=filing.company_id,
               filing_type=filing.filing_type)

    try:
        db_filing = create_filing(filing.model_dump(), session=db)
        logger.info("filing_created",
                   id=db_filing.id,
                   company_id=getattr(db_filing, "company_id", None),
                   filing_type=getattr(db_filing, "filing_type", None))
        return db_filing
    except Exception as e:
        error_msg = log_exception(e, logger, "Failed to create filing: ")
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/{filing_id}", response_model=Filing)
async def read_filing(
    filing_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve a specific filing by ID.

    Parameters:
    - filing_id: Filing ID
    """
    logger.info("read_filing_requested", filing_id=filing_id)

    db_filing = get_filing_by_id(filing_id, session=db)
    if db_filing is None:
        logger.warning("filing_not_found", filing_id=filing_id)
        raise HTTPException(status_code=404, detail="Filing not found")

    logger.info("filing_retrieved",
               filing_id=filing_id,
               company_id=getattr(db_filing, "company_id", None),
               filing_type=getattr(db_filing, "filing_type", None))
    return db_filing


@router.put("/{filing_id}", response_model=Filing)
async def update_filing_data(
    filing_id: int,
    filing: FilingUpdate,
    db: Session = Depends(get_db),
):
    """
    Update a filing.

    Parameters:
    - filing_id: Filing ID
    - filing: Updated filing data
    """
    logger.info("update_filing_requested", filing_id=filing_id)

    db_filing = get_filing_by_id(filing_id, session=db)
    if db_filing is None:
        logger.warning("filing_not_found", filing_id=filing_id)
        raise HTTPException(status_code=404, detail="Filing not found")

    try:
        # Filter out None values to keep existing values for those fields
        update_data = {k: v for k, v in filing.model_dump().items() if v is not None}
        updated_filing = update_filing(filing_id, update_data, session=db)
        logger.info("filing_updated", filing_id=filing_id)
        return updated_filing
    except Exception as e:
        error_msg = log_exception(e, logger, "Failed to update filing: ")
        raise HTTPException(status_code=500, detail=error_msg)


@router.delete("/{filing_id}", status_code=204)
async def delete_filing_data(
    filing_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete a filing.

    Parameters:
    - filing_id: Filing ID
    """
    logger.info("delete_filing_requested", filing_id=filing_id)

    db_filing = get_filing_by_id(filing_id, session=db)
    if db_filing is None:
        logger.warning("filing_not_found", filing_id=filing_id)
        raise HTTPException(status_code=404, detail="Filing not found")

    try:
        delete_filing(filing_id, session=db)
        logger.info("filing_deleted", filing_id=filing_id)
        return None
    except Exception as e:
        error_msg = log_exception(e, logger, "Failed to delete filing: ")
        raise HTTPException(status_code=500, detail=error_msg)