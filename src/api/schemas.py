"""API request and response schemas."""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CompanySearchRequest(BaseModel):
    """Request schema for company search."""
    ticker: Optional[str] = Field(None, description="Company ticker symbol")
    cik: Optional[str] = Field(None, description="Company CIK")


class CompanyIdRequest(BaseModel):
    """Request schema for company by ID."""
    company_id: UUID = Field(..., description="UUID of the company")


class FilingIdRequest(BaseModel):
    """Request schema for filing by ID."""
    filing_id: UUID = Field(..., description="UUID of the filing")


class DocumentIdRequest(BaseModel):
    """Request schema for document by ID."""
    document_id: UUID = Field(..., description="UUID of the document")